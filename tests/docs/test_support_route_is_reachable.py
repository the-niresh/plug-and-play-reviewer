"""A person who hits a bug must be able to tell us, from wherever they hit it.

Before this, the issue template existed and nothing in the product linked to it, blank
issues were disabled, Discussions were off, and no email address appeared anywhere. Every
bug listed in the launch review was one nobody could have reported.
"""

from __future__ import annotations

from pathlib import Path

from repo_paths import REPO_ROOT

REPO = REPO_ROOT
WEB = REPO / "apps" / "web" / "src"
SUPPORT_EMAIL = "niresh@yeahscene.com"


def _read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def test_one_constant_owns_the_support_address() -> None:
    """Three copies of an address drift. The page, the form handler and the docs all read
    this one."""
    assert f'SUPPORT_EMAIL = "{SUPPORT_EMAIL}"' in _read("apps/web/src/lib/site.ts")


def test_every_surface_a_stuck_person_is_on_offers_a_way_out() -> None:
    surfaces = {
        "site nav": "apps/web/src/components/SiteNav.tsx",
        "landing footer": "apps/web/src/app/page.tsx",
        "docs page": "apps/web/src/app/docs/page.tsx",
        "cli help": "src/pr_reviewer/reviewer_entry.py",
    }
    missing = [name for name, path in surfaces.items() if "/contact" not in _read(path)]
    assert missing == [], f"no route to support from: {missing}"


def test_the_cli_names_the_address_as_well_as_the_page() -> None:
    """A terminal is often the one place with no browser to hand."""
    assert SUPPORT_EMAIL in _read("src/pr_reviewer/reviewer_entry.py")


def test_the_form_handler_is_not_under_the_proxied_api_prefix() -> None:
    """next.config.ts rewrites /api/:path* to the control plane, so a handler there would
    never run. This is the kind of thing that only fails in production."""
    route = Path(WEB / "app" / "contact" / "send" / "route.ts")
    assert route.is_file(), "the contact form has no handler"
    assert "api" not in route.parts[route.parts.index("app") + 1 :][:1]


def test_a_missing_resend_key_says_so_instead_of_pretending() -> None:
    """Reporting a bug into a black hole is worse than no form at all."""
    handler = _read("apps/web/src/app/contact/send/route.ts")
    assert "RESEND_API_KEY" in handler
    assert "503" in handler
    assert "SUPPORT_EMAIL" in handler
