"""Shared repo paths for tests. Keep this file at tests/repo_paths.py."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TESTS_ROOT = Path(__file__).resolve().parent
SRC_ROOT = REPO_ROOT / "src" / "pr_reviewer"
