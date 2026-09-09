"""Logged-out dashboard must show sign-in, not a control-plane load error.

When gh_live_sign_in is absent, fetchReviews and fetchProfile must return
unauthenticated without calling the hosted API. A dead control plane must not
look like a broken signed-in session.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REVIEWS = REPO / "apps" / "web" / "src" / "lib" / "reviews.ts"
PROFILE = REPO / "apps" / "web" / "src" / "lib" / "profile.ts"
SESSION = REPO / "apps" / "web" / "src" / "lib" / "session.ts"


def test_session_helper_exists_and_names_the_live_cookie() -> None:
    source = SESSION.read_text(encoding="utf-8")
    assert 'export const SIGN_IN_COOKIE_NAME = "gh_live_sign_in"' in source
    assert "export function cookieHeaderHasSignIn" in source


def test_fetch_reviews_short_circuits_without_sign_in_cookie() -> None:
    source = REVIEWS.read_text(encoding="utf-8")
    assert 'from "@/lib/session"' in source
    assert "if (!cookieHeaderHasSignIn(cookieHeader))" in source
    assert 'return { kind: "unauthenticated" }' in source


def test_fetch_profile_short_circuits_without_sign_in_cookie() -> None:
    source = PROFILE.read_text(encoding="utf-8")
    assert 'from "@/lib/session"' in source
    assert "if (!cookieHeaderHasSignIn(cookieHeader))" in source
