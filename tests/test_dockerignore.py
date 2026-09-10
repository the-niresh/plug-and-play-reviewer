"""The UI image build must not copy local Next.js caches into the context."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCKERIGNORE = REPO / ".dockerignore"


def test_dockerignore_excludes_web_build_caches() -> None:
    assert DOCKERIGNORE.is_file(), "missing .dockerignore at repo root"
    ignored = DOCKERIGNORE.read_text(encoding="utf-8")
    for pattern in (".next", ".next-dev", "node_modules"):
        assert pattern in ignored, f".dockerignore must exclude {pattern}"
