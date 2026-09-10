"""next dev and next build must not share one cache directory.

A production next build writes hashed chunks (page-<hash>.js) into .next.
next dev HTML asks for unhashed page.js. When those share a folder, the
browser loads webpack.js then 404s the page chunk and throws
TypeError: __webpack_modules__[moduleId] is not a function.
"""

from __future__ import annotations

from repo_paths import REPO_ROOT

REPO = REPO_ROOT
CONFIG = REPO / "apps" / "web" / "next.config.ts"
GITIGNORE = REPO / ".gitignore"


def test_dev_uses_a_separate_dist_dir() -> None:
    source = CONFIG.read_text(encoding="utf-8")
    assert '".next-dev"' in source
    assert 'process.env.NODE_ENV === "production"' in source
    assert "distDir" in source


def test_dev_dist_dir_is_gitignored() -> None:
    ignored = GITIGNORE.read_text(encoding="utf-8")
    assert ".next-dev/" in ignored
