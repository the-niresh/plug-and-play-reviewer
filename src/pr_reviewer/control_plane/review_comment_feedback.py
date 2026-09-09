"""Capture human replies to our PR review comments. Not self-improvement."""

from __future__ import annotations

import re
from typing import Literal

from pr_reviewer.db.client import connection
from pr_reviewer.security.prompt_boundaries import UntrustedText, wrap_untrusted

HandleResult = Literal["recorded", "ignored", "duplicate"]
FeedbackClassification = Literal["useful", "wrong", "unclear", "follow_up", "unknown"]

FINDING_MARKER = re.compile(r"<!-- pr-reviewer:finding:([A-Za-z0-9._:-]{1,128}) -->")
MAX_REPLY_CHARS = 4000

_WRONG = ("wrong", "incorrect", "false positive", "not a bug", "not a problem", "disagree")
_USEFUL = ("useful", "helpful", "good catch", "thanks", "lgtm", "agree")
_UNCLEAR = ("unclear", "confusing", "what do you mean", "don't understand")
_FOLLOW_UP = ("follow up", "follow-up", "more detail", "can you", "please explain")


def classify_reply(untrusted: UntrustedText) -> FeedbackClassification:
    wrapped = wrap_untrusted("human_reply", untrusted)
    lowered = wrapped.lower()
    for needle in _WRONG:
        if needle in lowered:
            return "wrong"
    for needle in _USEFUL:
        if needle in lowered:
            return "useful"
    for needle in _UNCLEAR:
        if needle in lowered:
            return "unclear"
    for needle in _FOLLOW_UP:
        if needle in lowered:
            return "follow_up"
    return "unknown"


def handle_pull_request_review_comment(delivery_id: str, payload: object) -> HandleResult:
    parsed = _parse_review_comment(payload)
    if parsed is None:
        return "ignored"
    action, installation_id, repository_id, comment_id, in_reply_to_id, body = parsed
    if action != "created":
        return "ignored"

    finding_from_marker = _finding_id_from_body(body)
    untrusted = UntrustedText(body[:MAX_REPLY_CHARS])
    classification = classify_reply(untrusted)
    wrapped = wrap_untrusted("human_reply", untrusted)

    with connection() as conn, conn.transaction():
        delivery_cursor = conn.execute(
            """
            insert into github_deliveries (id, event_name)
            values (%s, 'pull_request_review_comment')
            on conflict (id) do nothing
            returning id
            """,
            (delivery_id,),
        )
        if delivery_cursor.rowcount == 0:
            return "duplicate"

        installation = conn.execute(
            "select id from installations where id = %s",
            (installation_id,),
        ).fetchone()
        if installation is None:
            return "ignored"

        recorded = False
        if finding_from_marker is not None:
            conn.execute(
                """
                insert into review_comment_posts (
                  github_comment_id, installation_id, github_repository_id, finding_id
                )
                values (%s, %s, %s, %s)
                on conflict (installation_id, github_repository_id, github_comment_id)
                do nothing
                """,
                (comment_id, installation_id, repository_id, finding_from_marker),
            )
            recorded = True

        if in_reply_to_id is not None:
            parent = conn.execute(
                """
                select finding_id
                from review_comment_posts
                where installation_id = %s
                  and github_repository_id = %s
                  and github_comment_id = %s
                """,
                (installation_id, repository_id, in_reply_to_id),
            ).fetchone()
            if parent is not None:
                conn.execute(
                    """
                    insert into review_comment_feedback (
                      delivery_id,
                      installation_id,
                      github_repository_id,
                      github_comment_id,
                      in_reply_to_comment_id,
                      finding_id,
                      classification,
                      reply_text
                    )
                    values (%s, %s, %s, %s, %s, %s, %s, %s)
                    on conflict (installation_id, github_repository_id, github_comment_id)
                    do nothing
                    """,
                    (
                        delivery_id,
                        installation_id,
                        repository_id,
                        comment_id,
                        in_reply_to_id,
                        parent["finding_id"],
                        classification,
                        wrapped,
                    ),
                )
                recorded = True

        return "recorded" if recorded else "ignored"


def _finding_id_from_body(body: str) -> str | None:
    match = FINDING_MARKER.search(body)
    if match is None:
        return None
    return match.group(1)


def _parse_review_comment(
    payload: object,
) -> tuple[str, int, int, int, int | None, str] | None:
    if not isinstance(payload, dict):
        return None
    installation = payload.get("installation")
    repository = payload.get("repository")
    comment = payload.get("comment")
    if not isinstance(installation, dict):
        return None
    if not isinstance(repository, dict):
        return None
    if not isinstance(comment, dict):
        return None
    installation_id = _as_int(installation.get("id"))
    repository_id = _as_int(repository.get("id"))
    comment_id = _as_int(comment.get("id"))
    if installation_id is None or repository_id is None or comment_id is None:
        return None
    action = payload.get("action")
    if not isinstance(action, str) or not action:
        return None
    body = comment.get("body")
    if not isinstance(body, str):
        return None
    in_reply_to_id = _as_int(comment.get("in_reply_to_id"))
    return action, installation_id, repository_id, comment_id, in_reply_to_id, body


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
