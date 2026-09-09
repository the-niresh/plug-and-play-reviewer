"""Stale-safe, idempotent GitHub review posting. Runs on the runner.

Findings are passed in by the caller. This module never imports the hosted
database or the App-token connector. submit, list_reviews,
render_hunks, lookup, record_post, and record_event are injected, the same
way retrieval takes record_selection.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Literal

import httpx

from pr_reviewer.contracts.finding import Finding
from pr_reviewer.contracts.github import PullRequestRef
from pr_reviewer.contracts.review_context import FilePatch
from pr_reviewer.github.lifecycle import reviewed_head_is_current

Confidentiality = Literal["restricted", "ordinary"]
CommentSide = Literal["RIGHT", "LEFT"]
_NEW_LINE = re.compile(r"^(\d+)\| ")
_MARKER_PREFIX = "<!-- pr-reviewer:post:"
_FINDING_MARKER = "<!-- pr-reviewer:finding:{finding_id} -->"


class StalePullRequestHead(RuntimeError):
    """The PR head moved after the review was computed and before the API call."""


@dataclass(frozen=True)
class RouteDecision:
    """The posting half of Task 15's GateDecision. Copied in, never recomputed."""

    allow_public_post: bool
    confidentiality: Confidentiality


@dataclass(frozen=True)
class ReviewComment:
    path: str
    line: int
    side: CommentSide
    body: str
    start_line: int | None = None


@dataclass(frozen=True)
class ReviewSubmission:
    commit_id: str
    body: str
    comments: tuple[ReviewComment, ...]


@dataclass(frozen=True)
class PostedReview:
    github_review_id: str | None
    comment_ids: tuple[str, ...]
    response_status: int | None
    body: str
    comments: tuple[ReviewComment, ...]
    summary_only: bool = False
    idempotency_key: str = ""
    suggestion_dropped_count: int = 0


def submit_review_to_github(
    ref: PullRequestRef,
    submission: ReviewSubmission,
    token: str,
    *,
    client: httpx.Client | None = None,
    api_base_url: str = "https://api.github.com",
    timeout_seconds: float = 10.0,
) -> PostedReview:
    http_client = client if client is not None else httpx.Client()
    response = http_client.post(
        f"{api_base_url}/repos/{ref.owner}/{ref.repository}/pulls/{ref.number}/reviews",
        headers={
            "accept": "application/vnd.github+json",
            "authorization": f"Bearer {token}",
            "x-github-api-version": "2022-11-28",
        },
        json={
            "commit_id": submission.commit_id,
            "event": "COMMENT",
            "body": submission.body,
            "comments": [
                _comment_payload(comment) for comment in submission.comments
            ],
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = _json_object(response)
    comment_ids = tuple(str(item.get("id", "")) for item in _json_list(payload.get("comments")))
    return PostedReview(
        github_review_id=str(payload.get("id", "")),
        comment_ids=comment_ids,
        response_status=response.status_code,
        body=str(payload.get("body", submission.body)),
        comments=submission.comments,
    )


def list_pull_request_reviews(
    ref: PullRequestRef,
    token: str,
    *,
    client: httpx.Client | None = None,
    api_base_url: str = "https://api.github.com",
    timeout_seconds: float = 10.0,
) -> tuple[PostedReview, ...]:
    http_client = client if client is not None else httpx.Client()
    response = http_client.get(
        f"{api_base_url}/repos/{ref.owner}/{ref.repository}/pulls/{ref.number}/reviews",
        headers={
            "accept": "application/vnd.github+json",
            "authorization": f"Bearer {token}",
            "x-github-api-version": "2022-11-28",
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    posted: list[PostedReview] = []
    for item in _json_list(response.json()):
        posted.append(
            PostedReview(
                github_review_id=str(item.get("id", "")),
                comment_ids=(),
                response_status=response.status_code,
                body=str(item.get("body", "")),
                comments=(),
            )
        )
    return tuple(posted)


def posting_idempotency_key(ref: PullRequestRef, head_sha: str, policy_version: str) -> str:
    return f"{ref.owner}/{ref.repository}#{ref.number}@{head_sha}:{policy_version}"


def post_review(
    ref: PullRequestRef,
    head_sha: str,
    findings: Sequence[tuple[Finding, RouteDecision]],
    idempotency_key: str,
    *,
    patches: Sequence[FilePatch],
    current_head_sha: Callable[[], str],
    submit: Callable[[ReviewSubmission], PostedReview],
    render_hunks: Callable[[FilePatch], str],
    list_reviews: Callable[[PullRequestRef], Sequence[PostedReview]] | None = None,
    lookup: Callable[[str], PostedReview | None] | None = None,
    record_post: Callable[[PostedReview], None] | None = None,
    record_event: Callable[[str, str, dict[str, str | int]], None] | None = None,
    policy_version: str = "v1",
) -> PostedReview | None:
    del policy_version
    existing = _existing(idempotency_key, ref, lookup, list_reviews)
    if existing is not None:
        return existing

    public = [
        (finding, decision)
        for finding, decision in findings
        if _is_public(finding, decision)
    ]
    if not public:
        return None

    comments = tuple(
        _anchor(finding, patches, render_hunks) for finding, _decision in public
    )
    inline = tuple(comment for comment, _dropped in comments if comment is not None)
    suggestion_dropped_count = sum(1 for _comment, dropped in comments if dropped)
    titles = [finding.title for finding, _decision in public]
    body = f"{_marker(idempotency_key)}\n" + "\n".join(f"- {title}" for title in titles)
    submission = ReviewSubmission(commit_id=head_sha, body=body, comments=inline)

    live = current_head_sha()
    if not reviewed_head_is_current(head_sha, live):
        raise StalePullRequestHead(
            f"stale head: reviewed {head_sha} but live head is {live}"
        )

    try:
        posted = submit(submission)
    except httpx.TimeoutException:
        recovered = _existing(idempotency_key, ref, lookup, list_reviews)
        if recovered is None:
            raise
        posted = recovered

    posted = replace(
        posted,
        idempotency_key=idempotency_key,
        summary_only=len(inline) == 0,
        body=posted.body or body,
        comments=posted.comments or inline,
        suggestion_dropped_count=suggestion_dropped_count,
    )
    if record_post is not None:
        record_post(posted)
    _emit(record_event, findings, posted)
    return posted


def _comment_payload(comment: ReviewComment) -> dict[str, str | int]:
    payload: dict[str, str | int] = {
        "path": comment.path,
        "line": comment.line,
        "side": comment.side,
        "body": comment.body,
    }
    if comment.start_line is not None:
        payload["start_line"] = comment.start_line
    return payload


def _is_public(finding: Finding, decision: RouteDecision) -> bool:
    if finding.status == "rejected":
        return False
    if decision.confidentiality == "restricted":
        return False
    return decision.allow_public_post


def _anchor(
    finding: Finding,
    patches: Sequence[FilePatch],
    render_hunks: Callable[[FilePatch], str],
) -> tuple[ReviewComment | None, bool]:
    patch = next((item for item in patches if item.path == finding.file_path), None)
    if patch is None:
        return None, finding.suggested_fix is not None
    numbers = _new_side_numbers(render_hunks(patch))
    if finding.line_start not in numbers:
        return None, finding.suggested_fix is not None
    include_suggestion = _suggestion_applies_cleanly(finding, numbers)
    dropped = finding.suggested_fix is not None and not include_suggestion
    return (
        ReviewComment(
            path=patch.path,
            line=finding.line_end if include_suggestion else finding.line_start,
            side="RIGHT",
            body=_comment_body(finding, include_suggestion=include_suggestion),
            start_line=(
                finding.line_start
                if include_suggestion and finding.line_end > finding.line_start
                else None
            ),
        ),
        dropped,
    )


def _suggestion_applies_cleanly(finding: Finding, numbers: set[int]) -> bool:
    text = finding.suggested_fix
    if text is None:
        return False
    if not text.strip() or "```" in text:
        return False
    return all(line in numbers for line in range(finding.line_start, finding.line_end + 1))


def _finding_marker(finding_id: str) -> str:
    return _FINDING_MARKER.format(finding_id=finding_id)


def _comment_body(finding: Finding, *, include_suggestion: bool) -> str:
    marker = _finding_marker(finding.id)
    if not include_suggestion or finding.suggested_fix is None:
        return f"{finding.title}\n\n{marker}"
    replacement = finding.suggested_fix.rstrip("\n")
    return f"{finding.title}\n\n```suggestion\n{replacement}\n```\n\n{marker}"


def _new_side_numbers(rendered: str) -> set[int]:
    numbers: set[int] = set()
    in_new = False
    for line in rendered.splitlines():
        if line.startswith("NEW "):
            in_new = True
            continue
        if line.startswith("OLD "):
            in_new = False
            continue
        if not in_new:
            continue
        match = _NEW_LINE.match(line)
        if match is not None:
            numbers.add(int(match.group(1)))
    return numbers


def _existing(
    key: str,
    ref: PullRequestRef,
    lookup: Callable[[str], PostedReview | None] | None,
    list_reviews: Callable[[PullRequestRef], Sequence[PostedReview]] | None,
) -> PostedReview | None:
    if lookup is not None:
        found = lookup(key)
        if found is not None:
            return found
    if list_reviews is None:
        return None
    needle = _marker(key)
    for review in list_reviews(ref):
        if needle in review.body:
            return replace(review, idempotency_key=key)
    return None


def _marker(key: str) -> str:
    return f"{_MARKER_PREFIX}{key} -->"


def _json_object(response: httpx.Response) -> dict[str, Any]:
    payload = response.json()
    if isinstance(payload, dict):
        return payload
    return {}


def _json_list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _emit(
    record_event: Callable[[str, str, dict[str, str | int]], None] | None,
    findings: Sequence[tuple[Finding, RouteDecision]],
    posted: PostedReview,
) -> None:
    if record_event is None or posted.github_review_id is None or posted.response_status is None:
        return
    job_id = findings[0][0].review_job_id if findings else ""
    record_event(
        job_id,
        "github.review_posted",
        {
            "github_review_id": posted.github_review_id,
            "response_status": posted.response_status,
            "comment_count": len(posted.comment_ids),
        },
    )
