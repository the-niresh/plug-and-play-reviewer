"""The release API image must serve the control-plane health endpoint."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.request
import uuid

import pytest
from repo_paths import REPO_ROOT

REPO = REPO_ROOT
IMAGE = "pr-reviewer-api-runtime-test"
WAIT_SECONDS = 90


def _docker() -> str:
    binary = shutil.which("docker")
    if binary is None:
        pytest.skip("docker is required for the release API image proof")
    return binary


def _run(*args: str, timeout: int = WAIT_SECONDS) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_docker(), *args],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=timeout,
    )


def _published_port(container: str) -> int:
    result = _run("port", container, "8000/tcp")
    assert result.returncode == 0, result.stderr + result.stdout
    host, port = result.stdout.strip().rsplit(":", 1)
    assert host == "127.0.0.1"
    return int(port)


def test_api_image_starts_and_serves_health_over_loopback() -> None:
    built = _run("build", "--target", "api", "--tag", IMAGE, ".", timeout=600)
    assert built.returncode == 0, built.stderr + built.stdout

    container = f"pr-reviewer-api-health-{uuid.uuid4().hex}"
    started = _run(
        "run",
        "--detach",
        "--name",
        container,
        "--publish",
        "127.0.0.1::8000",
        IMAGE,
        # Serve only. The image's own command migrates first and would need a database
        # this test does not have; the migrate-first path is covered below.
        "/app/.venv/bin/pr-reviewer-api",
    )
    assert started.returncode == 0, started.stderr + started.stdout
    try:
        port = _published_port(container)
        deadline = time.monotonic() + WAIT_SECONDS
        error: BaseException | None = None
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=2
                ) as response:
                    assert response.status == 200
                    assert json.loads(response.read()) == {"status": "ok"}
                    return
            except (OSError, TimeoutError, ValueError) as caught:
                error = caught
                time.sleep(0.5)
        logs = _run("logs", container)
        raise AssertionError(
            "API image did not serve GET /health over loopback; "
            f"last error={error!r}\n{logs.stderr}{logs.stdout}"
        )
    finally:
        _run("rm", "--force", container)


def test_the_default_command_refuses_to_serve_without_a_database() -> None:
    """The failure mode this guards against looks exactly like success.

    /health does not touch a table, so a control plane started against an unmigrated or
    unreachable database answers 200 and silently reviews nothing. The image's default
    command migrates first, so it has to die here instead.
    """
    built = _run("build", "--target", "api", "--tag", IMAGE, ".", timeout=600)
    assert built.returncode == 0, built.stderr + built.stdout

    result = _run(
        "run",
        "--rm",
        "--env",
        "DATABASE_URL=postgresql://nobody@127.0.0.1:1/nothing",
        IMAGE,
        timeout=120,
    )
    assert result.returncode != 0, result.stdout + result.stderr
    assert "Uvicorn running" not in result.stdout + result.stderr
