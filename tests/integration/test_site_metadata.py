"""Public pages must be findable and shareable.

These checks fail if the site goes back to one generic title and no preview card.
They read the source, not a production build.
"""

from __future__ import annotations

import re

from repo_paths import REPO_ROOT

REPO = REPO_ROOT
APP = REPO / "apps" / "web" / "src" / "app"
WEB_SRC = REPO / "apps" / "web" / "src"

TITLE_RE = re.compile(
    r"\btitle:\s*(?:[\"']([^\"']+)[\"']|pageTitle\()"
)
DESCRIPTION_RE = re.compile(r"\bdescription:\s*[\"']([^\"']+)[\"']")


def test_root_layout_has_metadata_base_and_share_cards() -> None:
    source = (APP / "layout.tsx").read_text(encoding="utf-8")
    assert "metadataBase" in source
    assert "openGraph" in source
    assert "twitter" in source
    assert "summary_large_image" in source
    # The name is centralised in lib/site.ts. Asserting the literal here would
    # re-hardcode what that refactor removed, and would go stale on every rename.
    assert "PRODUCT_NAME" in source


def test_sitemap_lists_public_routes_and_hides_private_ones() -> None:
    sitemap = APP / "sitemap.ts"
    assert sitemap.is_file(), "missing apps/web/src/app/sitemap.ts"
    source = sitemap.read_text(encoding="utf-8")
    for route in ("/", "/docs", "/docs/agents", "/scorecard"):
        assert route in source, f"sitemap missing {route}"
    assert "/dashboard" not in source
    assert "/connect" not in source


def test_robots_points_at_the_sitemap_and_hides_private_routes() -> None:
    robots = APP / "robots.ts"
    assert robots.is_file(), "missing apps/web/src/app/robots.ts"
    source = robots.read_text(encoding="utf-8")
    assert "sitemap" in source.lower()
    assert "/dashboard" in source
    assert "/connect" in source


def test_open_graph_image_declares_1200x630() -> None:
    og = APP / "opengraph-image.tsx"
    assert og.is_file(), "missing apps/web/src/app/opengraph-image.tsx"
    source = og.read_text(encoding="utf-8")
    assert "1200" in source
    assert "630" in source


def test_every_page_has_its_own_title_and_description() -> None:
    missing: list[str] = []
    seen_descriptions: dict[str, str] = {}
    for page in sorted(APP.rglob("page.tsx")):
        rel = page.relative_to(APP)
        source = page.read_text(encoding="utf-8")
        layout = page.parent / "layout.tsx"
        if layout.is_file() and layout != APP / "layout.tsx":
            source = source + "\n" + layout.read_text(encoding="utf-8")
        if page == APP / "page.tsx":
            source = source + "\n" + (APP / "layout.tsx").read_text(encoding="utf-8")
        title = TITLE_RE.search(source)
        description = DESCRIPTION_RE.search(source)
        if title is None or description is None:
            missing.append(str(rel))
            continue
        desc = description.group(1)
        owner = seen_descriptions.get(desc)
        if owner and owner != str(rel):
            missing.append(f"{rel} reuses description from {owner}")
        else:
            seen_descriptions[desc] = str(rel)
    assert missing == [], f"routes missing unique title+description: {missing}"


def test_site_nav_uses_the_product_name() -> None:
    nav = (WEB_SRC / "components" / "SiteNav.tsx").read_text(encoding="utf-8")
    assert "PRODUCT_NAME" in nav
    assert "pr-reviewer" not in nav
