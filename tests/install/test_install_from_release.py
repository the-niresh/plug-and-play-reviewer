"""Install-from-release verifies SHA256SUMS before copying the compose asset."""

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



def test_install_from_release_script_uses_local_dist_with_checksum(tmp_path: Path) -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker is required to build the release asset")
    dest = tmp_path / "dist"
    built = subprocess.run(
        ["sh", str(REPO / "scripts" / "build-local-release.sh"), str(dest)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120,
    )
    assert built.returncode == 0, built.stderr + built.stdout
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    result = subprocess.run(
        [
            "sh",
            str(REPO / "scripts" / "install-from-release.sh"),
            "--dist",
            str(dest),
            "--prefix",
            str(prefix),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert (prefix / _asset_name()).is_file()
    assert _asset_name() in result.stdout


def test_release_docs_describe_checksum_path() -> None:
    release = (REPO / "docs" / "RELEASE.md").read_text(encoding="utf-8")
    install = (REPO / "docs" / "INSTALL.md").read_text(encoding="utf-8")
    assert "SHA256SUMS" in release
    assert "install-from-release.sh" in release
    assert "install-from-release.sh" in install
    assert "build-local-release.sh" in install
