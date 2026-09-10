"""Vercel deploy config for the hosted Next.js web app."""

from __future__ import annotations

import json

from repo_paths import REPO_ROOT

REPO = REPO_ROOT
WEB = REPO / "apps" / "web"
README = REPO / "README.md"


def _read(relative: str) -> str:
    path = REPO / relative
    assert path.is_file(), f"missing {relative}"
    return path.read_text(encoding="utf-8")


def test_no_root_vercel_json_overrides_the_build() -> None:
    """The repo root must NOT carry a vercel.json. Deploy with Root Directory=apps/web.

    A root vercel.json with `cd apps/web` commands cannot work: Vercel resolves the
    framework from the Root Directory's package.json, and the repo root is a Python
    project with none, so the import fails with "No Next.js version detected". Setting
    Root Directory to apps/web fixes detection but then the same commands resolve to
    apps/web/apps/web. Worse, a checked-in vercel.json greys out the Build & Development
    Settings in the dashboard, so the bad values cannot be cleared from the UI at all.

    Vercel's own defaults are correct here and are verified below: apps/web declares next
    and a build script, and its lockfile is committed.
    """
    assert not (REPO / "vercel.json").is_file(), (
        "a root vercel.json locks the Vercel dashboard settings and breaks framework "
        "detection; deploy with Root Directory=apps/web and Vercel's defaults instead"
    )


def test_web_app_is_self_sufficient_for_vercel_defaults() -> None:
    payload = json.loads(_read("apps/web/package.json"))
    assert "next" in payload.get("dependencies", {})
    assert payload["scripts"]["build"] == "next build"
    assert (REPO / "apps" / "web" / "bun.lock").is_file(), (
        "Vercel's default install needs a committed lockfile"
    )


def test_vercel_ignores_backend_and_local_build_noise() -> None:
    text = _read(".vercelignore")
    for needle in (
        # Anchored: bare "src/" is unanchored and also matches apps/web/src, which
        # deleted the entire Next.js app on Vercel and produced a /404-only build.
        "/src/",
        ".venv/",
        "apps/web/.next",
        "apps/web/.next-dev",
        "apps/web/node_modules",
        ".env",
        ".env.*",
    ):
        assert needle in text
    assert "!docs/reports/scorecard.json" in text
    assert "!docs/reports/feature_flags.json" in text


def test_next_config_proxies_api_routes_to_the_control_plane() -> None:
    text = _read("apps/web/next.config.ts")
    assert "async rewrites()" in text
    assert 'source: "/api/:path*"' in text
    assert 'destination: `${controlPlaneOrigin}/api/:path*`' in text
    assert "normalizeOrigin(process.env.NEXT_PUBLIC_CONTROL_PLANE_ORIGIN)" in text


def test_root_layout_installs_vercel_analytics_and_speed_insights() -> None:
    """Analytics must load only after the visitor accepts, never on first paint.

    This used to assert the layout mounted <Analytics /> directly. That is exactly the
    behaviour the cookie notice exists to prevent: the page was collecting before it ever
    asked. The requirement is unchanged in spirit (observability ships) but the mount now
    belongs to AnalyticsGate, which renders nothing until stored consent says accepted.
    """
    layout = _read("apps/web/src/app/layout.tsx")
    assert "<AnalyticsGate />" in layout
    assert "<CookieNotice />" in layout
    # A direct mount here would bypass the gate entirely.
    assert "<Analytics />" not in layout
    assert "<SpeedInsights />" not in layout

    gate = _read("apps/web/src/components/AnalyticsGate.tsx")
    assert 'from "@vercel/analytics/next"' in gate
    assert 'from "@vercel/speed-insights/next"' in gate
    assert "<Analytics />" in gate
    assert "<SpeedInsights />" in gate
    assert 'readConsent() === "accepted"' in gate


def test_web_package_declares_vercel_observability_packages() -> None:
    payload = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    dependencies = payload["dependencies"]
    assert "@vercel/analytics" in dependencies
    assert "@vercel/speed-insights" in dependencies


def test_deploy_docs_explain_vercel_ui_and_api_proxy() -> None:
    text = _read("docs/DEPLOY.md")
    assert "## Vercel web UI" in text
    assert "NEXT_PUBLIC_SITE_ORIGIN" in text
    assert "NEXT_PUBLIC_CONTROL_PLANE_ORIGIN" in text
    assert "NEXT_PUBLIC_GITHUB_APP_SLUG" in text
    assert "PR_REVIEWER_HOSTED_ORIGIN" in text
    assert "proxies `/api/*`" in text
    assert "separate hosted API origin" in text
    assert "PR_REVIEWER_HOSTED_ORIGIN` to the\nVercel web origin" in text
    assert "api.reviewer.niresh.tech" in text
    assert "Homepage:" in text
    assert "/api/auth/github/callback" in text
    assert "/api/github/webhook" in text
    assert "Web Analytics and Speed Insights" in text
    assert "frontend traffic" in text
    assert "do not receive source code, diffs, model prompts, model replies, or model" in text
    assert "Vercel" in text and "frontend" in text.lower()
    assert "Render or Railway" in text
    assert "compose" in text.lower()
    assert "runner" in text.lower()


def test_readme_has_deploy_buttons_for_vercel_render_and_railway() -> None:
    text = README.read_text(encoding="utf-8")
    assert "Deploy frontend to Vercel" in text
    assert "Deploy API on Render" in text
    assert "Deploy API on Railway" in text
    assert "vercel.com/new/clone" in text
    assert "render.com/deploy" in text
    assert "railway.com/new" in text
    assert "One-click Render or Railway" not in text
    assert "Railway starts from a repo import until a public template id exists" in text


def test_landing_does_not_offer_to_clone_the_frontend() -> None:
    """The landing page must not tell a visitor to deploy their own copy of itself.

    A "Deploy frontend on Vercel" button clones the marketing site and dashboard the
    visitor is currently reading. Nobody using the product needs that; it is a fork
    button dressed as a product CTA, and it competed with the one action that matters
    (sign in). Removed 2026-09-11. Self-hosting the *control plane* is a real path and
    keeps its buttons, in the setup section rather than the hero.
    """
    text = _read("apps/web/src/app/page.tsx")
    assert "VERCEL_DEPLOY_URL" not in text
    assert "Deploy frontend on Vercel" not in text
    assert "vercel.com/new/clone" not in text


def test_landing_offers_control_plane_hosting_outside_the_hero() -> None:
    text = _read("apps/web/src/app/page.tsx")
    assert "RENDER_DEPLOY_URL" in text
    assert "RAILWAY_DEPLOY_URL" in text
    assert "Deploy API on Render" in text
    assert "Deploy API on Railway" in text
    assert "render.com/deploy" in text
    assert "railway.com/new" in text
    # They must sit in the setup section, after the hero CTA, not beside sign-in.
    assert text.index("Sign in with GitHub") < text.index("Deploy API on Render")
    assert text.index("how-to-set-it-up") < text.index("Deploy API on Render")


def test_landing_deploy_links_open_in_a_new_tab() -> None:
    text = _read("apps/web/src/app/page.tsx")
    for name in ("RENDER_DEPLOY_URL", "RAILWAY_DEPLOY_URL"):
        href_block = text.split(f"href={{{name}}}", 1)[1][:240]
        assert 'target="_blank"' in href_block, name
        assert 'rel="noopener noreferrer"' in href_block, name


def test_landing_deploy_buttons_use_a_mobile_safe_layout() -> None:
    text = _read("apps/web/src/app/page.tsx")
    assert "grid grid-cols-1" in text
    assert "sm:flex" in text


def test_railway_copy_is_not_called_one_click() -> None:
    landing = _read("apps/web/src/app/page.tsx")
    deploy = _read("docs/DEPLOY.md")
    assert "One-click Render or Railway" not in landing
    assert "Railway starts from a repo import until a public template id exists" in landing
    assert "one-click Render and Railway" not in deploy.lower()
    assert "repo import" in deploy.lower()
