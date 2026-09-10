"""Build public GitHub pull request URLs from owner/repo and PR number."""

from __future__ import annotations


def github_pull_request_url(
    repository_full_name: str,
    pull_request_number: int | None,
) -> str | None:
    """Return https://github.com/<owner>/<repo>/pull/<number> when both parts are known."""
    if pull_request_number is None:
        return None
    owner, separator, name = repository_full_name.partition("/")
    if not separator or not owner or not name:
        return None
    return f"https://github.com/{owner}/{name}/pull/{pull_request_number}"
