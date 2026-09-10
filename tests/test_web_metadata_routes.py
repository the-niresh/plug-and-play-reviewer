"""Metadata routes must return 200 from a production next start."""

from __future__ import annotations

import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WEB = REPO / "apps" / "web"
NEXT_DIR = WEB / ".next"


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
    assert "<loc>https://reviewer.niresh.tech/</loc>" in text
    assert "/dashboard" not in text


def test_metadata_routes_return_200(next_origin: str) -> None:
    for path in ("/sitemap.xml", "/robots.txt", "/opengraph-image"):
        with urllib.request.urlopen(f"{next_origin}{path}", timeout=5) as response:
            assert response.status == 200, path


def test_sitemap_xml_lists_public_routes(next_origin: str) -> None:
    with urllib.request.urlopen(f"{next_origin}/sitemap.xml", timeout=5) as response:
        body = response.read().decode("utf-8")
    for route in ("/", "/docs", "/docs/agents", "/scorecard"):
        assert f"https://reviewer.niresh.tech{route if route != '/' else '/'}" in body
