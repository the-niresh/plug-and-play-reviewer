"""GitHub pull request URLs are built from owner/repo and PR number only."""

from __future__ import annotations

from pr_reviewer.github.pull_request_url import github_pull_request_url


def test_github_pull_request_url_uses_owner_repo_and_number() -> None:
    assert (
        github_pull_request_url("octocat/widget", 3)
        == "https://github.com/octocat/widget/pull/3"
    )


def test_github_pull_request_url_returns_none_without_a_number() -> None:
    assert github_pull_request_url("octocat/widget", None) is None


def test_github_pull_request_url_returns_none_for_invalid_repository_name() -> None:
    assert github_pull_request_url("not-a-full-name", 1) is None
