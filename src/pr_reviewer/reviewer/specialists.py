"""Concern-specific specialist reviewers. Off by default."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.contracts.review_context import PackedDiff, ReviewContextItem
from pr_reviewer.github.pull_request import PullRequestSnapshot
from pr_reviewer.reviewer.aggregate_findings import aggregate_findings
from pr_reviewer.security.instruction_sources import ReviewPolicy

SPECIALIST_CONCERNS = ("security", "correctness", "tests", "docs")

ESTIMATED_COST_PER_SPECIALIST_USD = 0.012

_ENABLED_SPECIALISTS_KEY = "enabled_specialists_by_repo"

SpecialistFn = Callable[
    [PullRequestSnapshot, PackedDiff, Sequence[ReviewContextItem]],
    Sequence[FindingCandidate],
]


class SpecialistTimeout(Exception):
    """One specialist exceeded its deadline. Other concerns keep their findings."""

    def __init__(self, concern: str) -> None:
        self.concern = concern
        super().__init__(concern)


@dataclass(frozen=True)
class SpecialistRun:
    candidates: tuple[FindingCandidate, ...]
    timed_out_concerns: tuple[str, ...]
    missing_concerns: tuple[str, ...]


def specialists_enabled(policy: ReviewPolicy) -> bool:
    return policy.specialist_mode


def specialist_cost_notice(enabled_count: int) -> str:
    if enabled_count <= 0:
        return ""
    total = enabled_count * ESTIMATED_COST_PER_SPECIALIST_USD
    noun = "specialist" if enabled_count == 1 else "specialists"
    return (
        f"Adds about ${total:.2f} per review "
        f"({enabled_count} {noun} at about ${ESTIMATED_COST_PER_SPECIALIST_USD:.2f} each)."
    )


def get_enabled_specialists(config_path: Path, github_repository_id: int) -> tuple[str, ...]:
    payload = _read_config_payload(config_path)
    mapping = payload.get(_ENABLED_SPECIALISTS_KEY, {})
    if not isinstance(mapping, dict):
        return ()
    raw = mapping.get(str(github_repository_id), [])
    if not isinstance(raw, list):
        return ()
    return tuple(concern for concern in raw if concern in SPECIALIST_CONCERNS)


def set_enabled_specialists(
    config_path: Path,
    github_repository_id: int,
    concerns: Sequence[str],
) -> None:
    validated = tuple(concern for concern in concerns if concern in SPECIALIST_CONCERNS)
    payload = _read_config_payload(config_path)
    mapping = payload.setdefault(_ENABLED_SPECIALISTS_KEY, {})
    if not isinstance(mapping, dict):
        raise ValueError("enabled_specialists_by_repo must be a JSON object")
    mapping[str(github_repository_id)] = list(validated)
    _write_config_payload(config_path, payload)


def run_specialists(
    snapshot: PullRequestSnapshot,
    packed: PackedDiff,
    context: Sequence[ReviewContextItem],
    reviewers: Mapping[str, SpecialistFn],
    *,
    policy: ReviewPolicy,
    enabled_concerns: Sequence[str] | None = None,
) -> SpecialistRun:
    if enabled_concerns is not None:
        if not enabled_concerns:
            return SpecialistRun(candidates=(), timed_out_concerns=(), missing_concerns=())
        concerns_to_run = tuple(
            concern for concern in enabled_concerns if concern in SPECIALIST_CONCERNS
        )
    elif policy.specialist_mode:
        concerns_to_run = SPECIALIST_CONCERNS
    else:
        return SpecialistRun(candidates=(), timed_out_concerns=(), missing_concerns=())

    missing = tuple(concern for concern in concerns_to_run if concern not in reviewers)
    collected: list[FindingCandidate] = []
    timed_out: list[str] = []
    for concern in concerns_to_run:
        reviewer = reviewers.get(concern)
        if reviewer is None:
            continue
        try:
            collected.extend(reviewer(snapshot, packed, context))
        except SpecialistTimeout:
            timed_out.append(concern)
    merged = aggregate_findings(
        collected,
        repository=f"{snapshot.repo_owner}/{snapshot.repo_name}",
        head_sha=snapshot.head_sha,
    )
    return SpecialistRun(
        candidates=merged,
        timed_out_concerns=tuple(timed_out),
        missing_concerns=missing,
    )


def _read_config_payload(config_path: Path) -> dict[str, object]:
    if not config_path.is_file():
        return {}
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("repo config must be a JSON object")
    return raw


def _write_config_payload(config_path: Path, payload: dict[str, object]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
