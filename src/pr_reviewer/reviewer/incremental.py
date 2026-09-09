"""Plan and run an incremental re-review from the local review cache."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from pr_reviewer.context_budget import context_budget_for_model
from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.contracts.review_context import ReviewOutcome
from pr_reviewer.contracts.runner import LeaseState
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
from pr_reviewer.reliability.budget import BudgetLimit
from pr_reviewer.reviewer.diff_budget import pack_diff
from pr_reviewer.reviewer.hunk_format import split_patch_hunks
from pr_reviewer.reviewer.review_cache import (
    CachedFinding,
    ReviewCacheRecord,
    ReviewCacheStore,
    ReviewedHunk,
    hunks_from_file,
    hunks_from_snapshot,
    record_from_review,
)
from pr_reviewer.reviewer.review_pull_request import review_pull_request
from pr_reviewer.security.prompt_boundaries import UntrustedText

PRIOR_FINDING_TOKEN_BUDGET = 128


@dataclass(frozen=True)
class IncrementalPlan:
    files_to_review: tuple[str, ...]
    hunks_to_review: tuple[ReviewedHunk, ...]
    carry: tuple[CachedFinding, ...]
    recheck: tuple[CachedFinding, ...]
    prior_for_prompt: tuple[CachedFinding, ...]


def plan_incremental_review(
    snapshot: PullRequestSnapshot,
    previous: ReviewCacheRecord | None,
    related_paths: frozenset[str] = frozenset(),
) -> IncrementalPlan:
    current_hunks = hunks_from_snapshot(snapshot)
    if previous is None:
        return IncrementalPlan(
            files_to_review=tuple(file.path for file in snapshot.files),
            hunks_to_review=current_hunks,
            carry=(),
            recheck=(),
            prior_for_prompt=(),
        )

    previous_hashes = {
        (hunk.file_path, hunk.line_start, hunk.line_end, hunk.content_hash)
        for hunk in previous.reviewed_hunks
    }

    changed: list[ReviewedHunk] = []
    unchanged_files: set[str] = set()
    for file in snapshot.files:
        file_hunks = hunks_from_file(file)
        if not file_hunks:
            continue
        if all(
            (hunk.file_path, hunk.line_start, hunk.line_end, hunk.content_hash)
            in previous_hashes
            for hunk in file_hunks
        ) and file.path in previous.reviewed_files:
            unchanged_files.add(file.path)
            continue
        for hunk in file_hunks:
            if (
                hunk.file_path,
                hunk.line_start,
                hunk.line_end,
                hunk.content_hash,
            ) not in previous_hashes:
                changed.append(hunk)

    files_to_review = list(dict.fromkeys(hunk.file_path for hunk in changed))
    for path in related_paths:
        if path not in files_to_review and any(file.path == path for file in snapshot.files):
            files_to_review.append(path)

    changed_ranges = [(hunk.file_path, hunk.line_start, hunk.line_end) for hunk in changed]
    carry: list[CachedFinding] = []
    recheck: list[CachedFinding] = []
    for finding in previous.findings:
        if _overlaps_any(finding, changed_ranges):
            recheck.append(finding)
            continue
        if (
            finding.file_path in unchanged_files or finding.file_path not in files_to_review
        ) and any(file.path == finding.file_path for file in snapshot.files):
            carry.append(finding)

    prior = budget_prior_findings(recheck, PRIOR_FINDING_TOKEN_BUDGET)
    return IncrementalPlan(
        files_to_review=tuple(files_to_review),
        hunks_to_review=tuple(changed),
        carry=tuple(carry),
        recheck=tuple(recheck),
        prior_for_prompt=prior,
    )


def budget_prior_findings(
    findings: Sequence[CachedFinding], max_tokens: int
) -> tuple[CachedFinding, ...]:
    kept: list[CachedFinding] = []
    used = 0
    for finding in findings:
        text = _prior_finding_text(finding)
        tokens = max(1, len(text) // 4)
        if used + tokens > max_tokens:
            break
        kept.append(finding)
        used += tokens
    return tuple(kept)


def incremental_review_pull_request(
    snapshot: PullRequestSnapshot,
    model: object,
    *,
    model_name: str,
    cache: ReviewCacheStore,
    installation_id: int,
    repository_id: int,
    heartbeat: Callable[[], LeaseState] | None = None,
    budget: BudgetLimit | None = None,
    related_paths: frozenset[str] = frozenset(),
) -> ReviewOutcome:
    previous = cache.load_previous(installation_id, repository_id, snapshot.number)
    plan = plan_incremental_review(snapshot, previous, related_paths)
    filtered = _snapshot_for_plan(snapshot, plan)
    if not plan.files_to_review:
        outcome = ReviewOutcome(
            candidates=tuple(item.to_candidate() for item in plan.carry),
            packing_strategy_version="v1-incremental-skip",
            covers_all_changed_files=True,
            omitted_files=(),
            cancelled=False,
            cost_usd=0.0,
            latency_ms=0,
        )
        cache.save(
            record_from_review(
                installation_id=installation_id,
                repository_id=repository_id,
                snapshot=snapshot,
                findings=outcome.candidates,
                cost_usd=Decimal("0"),
            )
        )
        return outcome

    packed = pack_diff(filtered, context_budget_for_model(model_name), _count_tokens)
    prior_texts = tuple(
        UntrustedText(_prior_finding_text(item)) for item in plan.prior_for_prompt
    )
    outcome = review_pull_request(
        snapshot,
        packed,
        [],
        model,  # type: ignore[arg-type]
        model_name=model_name,
        heartbeat=heartbeat,
        budget=budget,
        prior_findings=prior_texts,
    )
    merged = _merge_carried(outcome, plan.carry)
    cache.save(
        record_from_review(
            installation_id=installation_id,
            repository_id=repository_id,
            snapshot=snapshot,
            findings=merged.candidates,
            cost_usd=Decimal(str(merged.cost_usd)),
        )
    )
    return merged


def _snapshot_for_plan(snapshot: PullRequestSnapshot, plan: IncrementalPlan) -> PullRequestSnapshot:
    changed_paths = {hunk.file_path for hunk in plan.hunks_to_review}
    files: list[PullRequestFile] = []
    for path in plan.files_to_review:
        current = next(file for file in snapshot.files if file.path == path)
        if path in changed_paths and current.patch:
            keep_hashes = {
                hunk.content_hash for hunk in plan.hunks_to_review if hunk.file_path == path
            }
            filtered_patch = _filter_patch(current.patch, keep_hashes)
            files.append(current.model_copy(update={"patch": filtered_patch}))
        else:
            files.append(current)
    return snapshot.model_copy(update={"files": files})


def _filter_patch(patch: str, keep_hashes: set[str]) -> str:
    kept = [
        hunk.text
        for hunk in split_patch_hunks(patch)
        if _sha256(hunk.text) in keep_hashes
    ]
    return "\n".join(kept)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _merge_carried(outcome: ReviewOutcome, carry: Sequence[CachedFinding]) -> ReviewOutcome:
    seen = {
        (item.file_path, item.line_start, item.line_end, item.title) for item in outcome.candidates
    }
    extra: list[FindingCandidate] = []
    for finding in carry:
        key = (finding.file_path, finding.line_start, finding.line_end, finding.title)
        if key not in seen:
            extra.append(finding.to_candidate())
    if not extra:
        return outcome
    return outcome.model_copy(update={"candidates": outcome.candidates + tuple(extra)})


def _overlaps_any(finding: CachedFinding, ranges: Sequence[tuple[str, int, int]]) -> bool:
    for path, start, end in ranges:
        if finding.file_path != path:
            continue
        if finding.line_start <= end and finding.line_end >= start:
            return True
    return False


def _prior_finding_text(finding: CachedFinding) -> str:
    return (
        f"{finding.file_path}:{finding.line_start}-{finding.line_end} "
        f"{finding.title}\n{finding.rationale}"
    )


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)
