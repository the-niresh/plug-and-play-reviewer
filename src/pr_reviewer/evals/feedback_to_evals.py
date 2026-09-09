"""Turn captured review-comment feedback into human-reviewable candidates.

Reads structured feedback rows only. Never writes prompts, eval labels, datasets,
scorecard numbers, or model settings.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FeedbackClassification = Literal["useful", "wrong", "unclear", "follow_up", "unknown"]

TASK_CLASSIFICATIONS = frozenset({"wrong", "unclear", "unknown"})
REPLY_EXCERPT_MAX = 240


class ReviewCommentFeedbackRow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    installation_id: int = Field(gt=0)
    github_repository_id: int = Field(gt=0)
    pull_request_number: int | None = Field(default=None, gt=0)
    github_comment_id: int = Field(gt=0)
    in_reply_to_comment_id: int = Field(gt=0)
    finding_id: str | None = None
    classification: FeedbackClassification
    reply_text: str = Field(min_length=1)
    created_at: datetime


class ImprovementTaskCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str = Field(min_length=1)
    installation_id: int = Field(gt=0)
    github_repository_id: int = Field(gt=0)
    pull_request_number: int | None = Field(default=None, gt=0)
    finding_id: str = Field(min_length=1)
    classification: FeedbackClassification
    feedback_count: int = Field(ge=1)
    feedback_ids: tuple[str, ...] = Field(min_length=1)
    github_comment_ids: tuple[int, ...] = Field(min_length=1)
    reply_excerpts: tuple[str, ...] = Field(min_length=1)
    first_seen_at: datetime
    last_seen_at: datetime


class PositiveFeedbackSignal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    installation_id: int = Field(gt=0)
    github_repository_id: int = Field(gt=0)
    pull_request_number: int | None = Field(default=None, gt=0)
    finding_id: str | None = None
    count: int = Field(ge=1)
    feedback_ids: tuple[str, ...] = Field(min_length=1)


class FollowUpFeedbackGroup(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    installation_id: int = Field(gt=0)
    github_repository_id: int = Field(gt=0)
    pull_request_number: int | None = Field(default=None, gt=0)
    finding_id: str | None = None
    count: int = Field(ge=1)
    feedback_ids: tuple[str, ...] = Field(min_length=1)
    reply_excerpts: tuple[str, ...] = Field(min_length=1)


class FeedbackImprovementReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_candidates: tuple[ImprovementTaskCandidate, ...] = ()
    positive_signals: tuple[PositiveFeedbackSignal, ...] = ()
    follow_up_groups: tuple[FollowUpFeedbackGroup, ...] = ()
    duplicates_skipped: int = Field(default=0, ge=0)
    prompt_rewrites: tuple[str, ...] = ()
    policy_changes: tuple[str, ...] = ()
    label_changes: tuple[str, ...] = ()


def _aware(when: datetime) -> datetime:
    if when.tzinfo is None:
        return when.replace(tzinfo=UTC)
    return when


def _reply_excerpt(reply_text: str) -> str:
    text = reply_text.strip()
    if len(text) <= REPLY_EXCERPT_MAX:
        return text
    return text[: REPLY_EXCERPT_MAX - 3] + "..."


def _candidate_id(
    *,
    installation_id: int,
    github_repository_id: int,
    pull_request_number: int | None,
    finding_id: str,
    classification: str,
    feedback_ids: Sequence[str],
) -> str:
    payload = (
        f"{installation_id}:{github_repository_id}:{pull_request_number}:"
        f"{finding_id}:{classification}:{','.join(sorted(feedback_ids))}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _dedupe_rows(
    rows: Sequence[ReviewCommentFeedbackRow],
) -> tuple[tuple[ReviewCommentFeedbackRow, ...], int]:
    seen: set[str] = set()
    kept: list[ReviewCommentFeedbackRow] = []
    skipped = 0
    for row in sorted(rows, key=lambda item: (_aware(item.created_at), item.id)):
        if row.id in seen:
            skipped += 1
            continue
        seen.add(row.id)
        kept.append(row)
    return tuple(kept), skipped


def build_feedback_improvement_report(
    rows: Sequence[ReviewCommentFeedbackRow],
) -> FeedbackImprovementReport:
    deduped, duplicates_skipped = _dedupe_rows(rows)

    task_groups: dict[
        tuple[int, int, int | None, str, FeedbackClassification], list[ReviewCommentFeedbackRow]
    ] = defaultdict(list)
    positive_groups: dict[
        tuple[int, int, int | None, str | None], list[ReviewCommentFeedbackRow]
    ] = defaultdict(list)
    follow_up_groups: dict[
        tuple[int, int, int | None, str | None], list[ReviewCommentFeedbackRow]
    ] = defaultdict(list)

    for row in deduped:
        if row.classification in TASK_CLASSIFICATIONS:
            if row.finding_id is None:
                continue
            task_key = (
                row.installation_id,
                row.github_repository_id,
                row.pull_request_number,
                row.finding_id,
                row.classification,
            )
            task_groups[task_key].append(row)
            continue
        if row.classification == "useful":
            positive_key = (
                row.installation_id,
                row.github_repository_id,
                row.pull_request_number,
                row.finding_id,
            )
            positive_groups[positive_key].append(row)
            continue
        if row.classification == "follow_up":
            follow_up_key = (
                row.installation_id,
                row.github_repository_id,
                row.pull_request_number,
                row.finding_id,
            )
            follow_up_groups[follow_up_key].append(row)

    task_candidates: list[ImprovementTaskCandidate] = []
    for task_key in sorted(task_groups):
        group = task_groups[task_key]
        (
            installation_id,
            github_repository_id,
            pull_request_number,
            finding_id,
            classification,
        ) = task_key
        feedback_ids = tuple(sorted(item.id for item in group))
        comment_ids = tuple(sorted(item.github_comment_id for item in group))
        excerpts = tuple(_reply_excerpt(item.reply_text) for item in group)
        seen_at = [_aware(item.created_at) for item in group]
        task_candidates.append(
            ImprovementTaskCandidate(
                candidate_id=_candidate_id(
                    installation_id=installation_id,
                    github_repository_id=github_repository_id,
                    pull_request_number=pull_request_number,
                    finding_id=finding_id,
                    classification=classification,
                    feedback_ids=feedback_ids,
                ),
                installation_id=installation_id,
                github_repository_id=github_repository_id,
                pull_request_number=pull_request_number,
                finding_id=finding_id,
                classification=classification,
                feedback_count=len(group),
                feedback_ids=feedback_ids,
                github_comment_ids=comment_ids,
                reply_excerpts=excerpts,
                first_seen_at=min(seen_at),
                last_seen_at=max(seen_at),
            )
        )

    positive_signals: list[PositiveFeedbackSignal] = []
    for signal_key in sorted(positive_groups):
        group = positive_groups[signal_key]
        (
            signal_installation_id,
            signal_repository_id,
            signal_pull_request_number,
            signal_finding_id,
        ) = signal_key
        positive_signals.append(
            PositiveFeedbackSignal(
                installation_id=signal_installation_id,
                github_repository_id=signal_repository_id,
                pull_request_number=signal_pull_request_number,
                finding_id=signal_finding_id,
                count=len(group),
                feedback_ids=tuple(sorted(item.id for item in group)),
            )
        )

    follow_ups: list[FollowUpFeedbackGroup] = []
    for follow_up_key in sorted(follow_up_groups):
        group = follow_up_groups[follow_up_key]
        (
            follow_installation_id,
            follow_repository_id,
            follow_pull_request_number,
            follow_finding_id,
        ) = follow_up_key
        follow_ups.append(
            FollowUpFeedbackGroup(
                installation_id=follow_installation_id,
                github_repository_id=follow_repository_id,
                pull_request_number=follow_pull_request_number,
                finding_id=follow_finding_id,
                count=len(group),
                feedback_ids=tuple(sorted(item.id for item in group)),
                reply_excerpts=tuple(_reply_excerpt(item.reply_text) for item in group),
            )
        )

    return FeedbackImprovementReport(
        task_candidates=tuple(task_candidates),
        positive_signals=tuple(positive_signals),
        follow_up_groups=tuple(follow_ups),
        duplicates_skipped=duplicates_skipped,
    )


def format_feedback_improvement_report(report: FeedbackImprovementReport) -> str:
    lines = [
        "# Feedback improvement report",
        "",
        f"Duplicates skipped: {report.duplicates_skipped}",
        f"Task candidates: {len(report.task_candidates)}",
        f"Positive signals: {len(report.positive_signals)}",
        f"Follow-up groups: {len(report.follow_up_groups)}",
        "",
    ]
    if report.task_candidates:
        lines.append("## Task candidates")
        for candidate in report.task_candidates:
            lines.append(
                f"- {candidate.candidate_id}: install={candidate.installation_id} "
                f"repo={candidate.github_repository_id} pr={candidate.pull_request_number} "
                f"finding={candidate.finding_id} class={candidate.classification} "
                f"count={candidate.feedback_count}"
            )
        lines.append("")
    if report.positive_signals:
        lines.append("## Positive signals")
        for signal in report.positive_signals:
            lines.append(
                f"- install={signal.installation_id} repo={signal.github_repository_id} "
                f"pr={signal.pull_request_number} finding={signal.finding_id} count={signal.count}"
            )
        lines.append("")
    if report.follow_up_groups:
        lines.append("## Follow-up groups")
        for group in report.follow_up_groups:
            lines.append(
                f"- install={group.installation_id} repo={group.github_repository_id} "
                f"pr={group.pull_request_number} finding={group.finding_id} count={group.count}"
            )
    return "\n".join(lines)
