"""Metadata routes must return 200 from a production next start."""

from __future__ import annotations

import re
import socket
import subprocess
import time
import urllib.error
import urllib.request

import pytest
from repo_paths import REPO_ROOT

REPO = REPO_ROOT
WEB = REPO / "apps" / "web"
NEXT_DIR = WEB / ".next"
SITE_TS = WEB / "src" / "lib" / "site.ts"


def _default_site_origin() -> str:
    """Read the origin out of site.ts instead of repeating it here.

    A hardcoded copy of the hostname turns every domain move into a red test that says
    nothing about the site being wrong, which is how the last rename went.
    """
    match = re.search(
        r'DEFAULT_SITE_ORIGIN = "([^"]+)"', SITE_TS.read_text(encoding="utf-8")
    )
    assert match, "site.ts no longer declares DEFAULT_SITE_ORIGIN"
    return match.group(1)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def production_build() -> None:
    result = subprocess.run(
        ["bun", "run", "build"],
        cwd=WEB,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, f"next build failed:\n{result.stdout}\n{result.stderr}"


@pytest.fixture(scope="module")
def next_origin(production_build: None) -> str:
    port = _free_port()
    proc = subprocess.Popen(
        [
            str(WEB / "node_modules" / ".bin" / "next"),
            "start",
            "--hostname",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=WEB,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    origin = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 30
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{origin}/robots.txt", timeout=2) as response:
                if response.status == 200:
                    break
        except (OSError, TimeoutError, urllib.error.URLError, ValueError) as caught:
            last_error = caught
            time.sleep(0.3)
    else:
        stdout, stderr = proc.communicate(timeout=5)
        proc.kill()
        raise AssertionError(
            f"next start did not serve robots.txt on {origin}; last error={last_error!r}\n"
            f"{stdout}\n{stderr}"
        )
    try:
        yield origin
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def test_build_prerenders_sitemap_body(production_build: None) -> None:
    body = NEXT_DIR / "server" / "app" / "sitemap.xml.body"
    assert body.is_file(), "next build must prerender /sitemap.xml"
    text = body.read_text(encoding="utf-8")
    assert text.startswith("<?xml")
    assert f"<loc>{_default_site_origin()}/</loc>" in text
    assert "/dashboard" not in text


def test_metadata_routes_return_200(next_origin: str) -> None:
    for path in ("/sitemap.xml", "/robots.txt", "/opengraph-image"):
        with urllib.request.urlopen(f"{next_origin}{path}", timeout=5) as response:
            assert response.status == 200, path


def test_sitemap_xml_lists_public_routes(next_origin: str) -> None:
    with urllib.request.urlopen(f"{next_origin}/sitemap.xml", timeout=5) as response:
        body = response.read().decode("utf-8")
    for route in ("/", "/docs", "/docs/agents", "/scorecard"):
        assert f"{_default_site_origin()}{route if route != '/' else '/'}" in body
