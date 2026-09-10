"""Each dashboard review must link to the original GitHub pull request."""

from __future__ import annotations

from repo_paths import REPO_ROOT

WEB_SRC = REPO_ROOT / "apps" / "web" / "src"
DASHBOARD_PAGE = WEB_SRC / "app" / "dashboard" / "page.tsx"
REVIEWS_PAGE = WEB_SRC / "app" / "dashboard" / "reviews" / "page.tsx"
REVIEW_DETAIL_PAGE = WEB_SRC / "app" / "dashboard" / "reviews" / "[reviewJobId]" / "page.tsx"
REVIEWS_LIB = WEB_SRC / "lib" / "reviews.ts"
PULL_REQUEST_LINK = WEB_SRC / "components" / "PullRequestLink.tsx"


def test_review_summary_exposes_pull_request_url_from_the_api() -> None:
    source = REVIEWS_LIB.read_text(encoding="utf-8")
    assert "pull_request_url" in source


def test_pull_request_link_component_opens_github_in_a_new_tab() -> None:
    assert PULL_REQUEST_LINK.is_file(), f"missing {PULL_REQUEST_LINK}"
    source = PULL_REQUEST_LINK.read_text(encoding="utf-8")
    assert 'target="_blank"' in source
    assert 'rel="noopener noreferrer"' in source
    assert "Open PR" in source


def test_dashboard_recent_reviews_render_a_github_pr_link() -> None:
    source = DASHBOARD_PAGE.read_text(encoding="utf-8")
    assert "<PullRequestLink" in source


def test_reviews_table_renders_a_github_pr_link() -> None:
    source = REVIEWS_PAGE.read_text(encoding="utf-8")
    assert "<PullRequestLink" in source


def test_review_detail_renders_a_github_pr_link() -> None:
    source = REVIEW_DETAIL_PAGE.read_text(encoding="utf-8")
    assert "<PullRequestLink" in source
