"""Hosted Traefik overlay is present and valid. The runbook says what is live."""

from __future__ import annotations

import shutil
import subprocess

import pytest
from repo_paths import REPO_ROOT

REPO = REPO_ROOT


def _live_hosted_origin() -> str:
    """The origin the shipped runner points at, read from the constant that declares it."""
    from pr_reviewer.tui.github_connect import DEFAULT_HOSTED_ORIGIN

    return DEFAULT_HOSTED_ORIGIN

SECRET_MARKERS = (
    "DATABASE_URL",
    "NEON",
    "WEBHOOK_SECRET",
    "GITHUB_APP_PRIVATE_KEY",
    "BEGIN ",
    "PRIVATE KEY",
)


def test_runbook_separates_live_host_from_owner_setup() -> None:
    text = (REPO / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
    origin = _live_hosted_origin()
    assert "Nothing in this file is applied." not in text
    assert origin in text
    assert "GET /health" in text
    assert "GET /ready" in text
    assert f"{origin}/api/auth/github/callback" in text
    assert f"{origin}/api/github/webhook" in text
    assert "Point the GitHub App homepage, callback, and webhook" in text
    assert "Render or Railway" in text


def test_traefik_file_defines_reviewer_router_and_service() -> None:
    text = (REPO / "deploy" / "traefik" / "reviewer.yml").read_text(encoding="utf-8")
    assert "Host(`reviewer.niresh.tech`)" in text
    assert "websecure" in text
    assert "http://api:8000" in text
    assert not any(marker in text for marker in SECRET_MARKERS)


def test_hosted_compose_labels_match_the_traefik_file() -> None:
    text = (REPO / "docker-compose.hosted.yml").read_text(encoding="utf-8")
    assert "Host(`reviewer.niresh.tech`)" in text
    assert "n8n-mkvx_proxy" in text
    assert 'traefik.http.services.reviewer-api.loadbalancer.server.port: "8000"' in text
    assert 'traefik.http.services.reviewer-ui.loadbalancer.server.port: "3000"' in text
    # Two routers share the host, so the split must be pinned by explicit priority.
    # Traefik's default orders by rule length, which silently reorders when a rule
    # is edited and would hand /api to the UI.
    assert 'traefik.http.routers.reviewer-api.priority: "100"' in text
    assert 'traefik.http.routers.reviewer-ui.priority: "1"' in text
    # The api route must be withdrawn when the database is unreachable, not left
    # serving requests the application cannot answer.
    assert "traefik.http.services.reviewer-api.loadbalancer.healthcheck.path: /ready" in text
    assert not any(marker in text for marker in SECRET_MARKERS)


def test_hosted_compose_config_renders_offline() -> None:
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("docker is required to render compose config")
    result = subprocess.run(
        [
            docker,
            "compose",
            "-f",
            str(REPO / "compose.release.yml"),
            "-f",
            str(REPO / "docker-compose.hosted.yml"),
            "config",
            "--no-interpolate",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "reviewer.niresh.tech" in result.stdout
    assert "n8n-mkvx_proxy" in result.stdout
