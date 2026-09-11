"""The landing page must offer a working, obvious way to sign in.

Before this, apps/web/src/app/page.tsx's only call to action was "Connect GitHub" linking
to /onboarding -- a local-runner pairing page that talks to a daemon on 127.0.0.1:8741 and
does nothing for a plain browser visitor. The hosted GitHub OAuth flow
(/api/auth/github/sign-in) was unreachable from the front door. These guards fail if that
regresses, and fail if a signed-in visitor would see the sign-in button again instead of
being sent on to the dashboard.
"""

from __future__ import annotations

import re

from repo_paths import REPO_ROOT

from pr_reviewer.control_plane.github_oauth import (
    ALLOWED_RETURN_TO_PATHS,
)

WEB_SRC = REPO_ROOT / "apps" / "web" / "src"
LANDING_PAGE = WEB_SRC / "app" / "page.tsx"
MIDDLEWARE = WEB_SRC / "middleware.ts"
SESSION = WEB_SRC / "lib" / "session.ts"

SIGN_IN_HREF = re.compile(r"/api/auth/github/sign-in\?return_to=([^\"'`]+)")


def test_landing_page_exists() -> None:
    assert LANDING_PAGE.is_file(), f"missing {LANDING_PAGE}"


def test_landing_page_links_to_the_hosted_sign_in_route() -> None:
    source = LANDING_PAGE.read_text(encoding="utf-8")
    match = SIGN_IN_HREF.search(source)
    assert match is not None, "landing page has no /api/auth/github/sign-in link"
    return_to = match.group(1)
    assert return_to in ALLOWED_RETURN_TO_PATHS, (
        f"landing page's return_to={return_to!r} is not in the hosted allowlist"
    )


def test_landing_page_names_github_on_the_button_itself() -> None:
    """"Sign in" alone is not obvious about which provider; the visible label must name
    GitHub, and the element carrying that label must itself be the link (an href a short
    distance before the label, not just nearby prose anywhere in the file)."""
    source = LANDING_PAGE.read_text(encoding="utf-8")
    label_index = source.index("Sign in with GitHub")
    preceding = source[max(0, label_index - 250) : label_index]
    assert "href" in preceding, "no href found immediately before the \"Sign in with GitHub\" label"


def test_landing_page_sign_in_is_above_the_fold_not_in_a_footer() -> None:
    """It must be the hero's own call to action, not buried below the pillars or in the
    footer -- "obvious without scrolling" per the task."""
    source = LANDING_PAGE.read_text(encoding="utf-8")
    sign_in_index = source.index("/api/auth/github/sign-in")
    footer_index = source.index("<footer")
    assert sign_in_index < footer_index, "sign-in link appears after the footer"


def test_landing_page_no_longer_sends_a_fresh_visitor_to_local_runner_pairing() -> None:
    """/onboarding needs a local daemon on 127.0.0.1:8741 and does nothing for someone who
    has never installed the runner; it must not be the landing page's primary action."""
    source = LANDING_PAGE.read_text(encoding="utf-8")
    assert '"/onboarding"' not in source


def test_the_landing_page_is_reachable_when_signed_in() -> None:
    """There is no middleware, and there must not be one that bounces "/" to /dashboard.

    A signed-in visitor who clicks the logo, follows a shared link, or wants to read the
    docs pitch was redirected away from the page before it rendered. Nobody asked for
    that, and a marketing page that hides itself from its own users is a bug. Signed-in
    state belongs in what the page shows, not in whether the page loads.
    """
    assert not MIDDLEWARE.exists(), (
        f"{MIDDLEWARE} is back; the landing page must render for signed-in visitors too"
    )


def test_the_sign_in_href_pattern_actually_catches_a_violation() -> None:
    assert SIGN_IN_HREF.search('href="/api/auth/github/sign-in?return_to=/dashboard"')
    assert not SIGN_IN_HREF.search('href="/onboarding"')
