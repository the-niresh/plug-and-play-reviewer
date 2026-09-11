"""Install a locally built versioned release asset in a clean Linux container."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from repo_paths import REPO_ROOT

REPO = REPO_ROOT


def _asset_name() -> str:
    """Derived, not pinned. scripts/build-local-release.sh names the asset from
    pyproject's version, so a version bump used to break these tests with a message
    about a missing file rather than about the release."""
    import tomllib

    version = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]["version"]
    return f"pr-reviewer-{version}-compose.release.yml"

BUSYBOX = "busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"


def test_local_versioned_asset_installs_in_clean_linux_container(tmp_path: Path) -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker is required for the local versioned-asset install proof")
    dest = tmp_path / "dist"
    built = subprocess.run(
        ["sh", str(REPO / "scripts" / "build-local-release.sh"), str(dest)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
    )
    assert built.returncode == 0, built.stderr + built.stdout
    asset = dest / _asset_name()
    sums = dest / "SHA256SUMS"
    assert asset.is_file()
    assert _asset_name() in sums.read_text(encoding="utf-8")
    asset_text = asset.read_text(encoding="utf-8")
    assert "${DATABASE_URL:?DATABASE_URL must be set}" in asset_text
    assert "${GITHUB_APP_PRIVATE_KEY:?GITHUB_APP_PRIVATE_KEY must be set}" in asset_text
    assert "${GITHUB_WEBHOOK_SECRET:?GITHUB_WEBHOOK_SECRET must be set}" in asset_text
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            "65532:65532",
            "-v",
            f"{REPO / 'scripts' / 'install.sh'}:/install.sh:ro",
            "-v",
            f"{asset}:/{_asset_name()}:ro",
            "-v",
            f"{sums}:/SHA256SUMS:ro",
            BUSYBOX,
            "sh",
            "/install.sh",
            "--archive",
            f"/{_asset_name()}",
            "--checksum-file",
            "/SHA256SUMS",
            "--prefix",
            "/tmp/prefix",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert f"{_asset_name()}: OK" in result.stdout
