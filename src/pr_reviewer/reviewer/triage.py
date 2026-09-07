"""Keep cheap changes off the expensive review path.

Lockfiles, generated files, docs-only changes and dependency-version bumps carry no
hand-written logic to review. Path and content rules decide these without a model
call, reusing OmissionReason (GENERATED, IGNORED_PATH) rather than inventing a
second vocabulary for "why no review happened."

A triage decision always carries a reason, on both the skip and the no-skip branch,
because a silent skip is indistinguishable from a failure once it reaches a dashboard.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from pr_reviewer.contracts.github import OmissionReason
from pr_reviewer.contracts.review_context import PackedDiff, ReviewContextItem, ReviewOutcome
from pr_reviewer.contracts.runner import LeaseState
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
from pr_reviewer.models.provider import ModelProvider
from pr_reviewer.reviewer.review_pull_request import review_pull_request

NO_CHANGED_FILES_REASON = "no_changed_files"
ALL_FILES_TRIVIAL_REASON = "all_changed_files_are_trivial"
CONTAINS_REVIEWABLE_CHANGES_REASON = "contains_reviewable_changes"

_LOCKFILE_NAMES = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Pipfile.lock",
        "Cargo.lock",
        "Gemfile.lock",
        "composer.lock",
        "go.sum",
        "uv.lock",
        "mix.lock",
    }
)
_GENERATED_PATH_MARKERS = ("dist/", "build/", "generated/", "vendor/", "node_modules/")
_GENERATED_SUFFIXES = (".min.js", ".min.css", ".map")
_DOC_SUFFIXES = (".md", ".rst")
_DOC_PATH_MARKERS = ("docs/",)
_DOC_BASENAMES = frozenset({"license", "changelog", "notice", "readme.md", "contributing.md"})
_DEPENDENCY_MANIFESTS = frozenset(
    {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "Cargo.toml",
        "Gemfile",
        "go.mod",
        "composer.json",
    }
)
_VERSION_BUMP_LINE = re.compile(
    r'^[+-]\s*"?[\w@./-]*"?\s*[:=]{1,2}\s*"?[~^]?\d+(?:\.\d+){1,3}[\w.\-]*"?,?\s*$'
)


@dataclass(frozen=True)
class TriageDecision:
    """Whether the expensive call is skipped, and why, per file and overall."""

    skip_expensive_review: bool
    reason: str
    file_reasons: tuple[tuple[str, OmissionReason], ...]


@dataclass(frozen=True)
class TriagedReview:
    decision: TriageDecision
    outcome: ReviewOutcome


def classify_trivial_file(file: PullRequestFile) -> OmissionReason | None:
    """Return why a file needs no deep review, or None if it might."""
    basename = file.path.rsplit("/", 1)[-1]
    lower_path = file.path.lower()

    if basename in _LOCKFILE_NAMES:
        return OmissionReason.GENERATED
    if any(marker in lower_path for marker in _GENERATED_PATH_MARKERS):
        return OmissionReason.GENERATED
    if lower_path.endswith(_GENERATED_SUFFIXES):
        return OmissionReason.GENERATED
    if basename in _DEPENDENCY_MANIFESTS and _is_dependency_bump_only(file.patch):
        return OmissionReason.GENERATED

    if lower_path.endswith(_DOC_SUFFIXES):
        return OmissionReason.IGNORED_PATH
    if any(
        lower_path.startswith(marker) or f"/{marker}" in lower_path
        for marker in _DOC_PATH_MARKERS
    ):
        return OmissionReason.IGNORED_PATH
    if basename.lower() in _DOC_BASENAMES:
        return OmissionReason.IGNORED_PATH

    return None


def _is_dependency_bump_only(patch: str | None) -> bool:
    if not patch:
        return False
    changed_lines = [
        line
        for line in patch.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]
    if not changed_lines:
        return False
    return all(_VERSION_BUMP_LINE.match(line) for line in changed_lines)


def triage_pull_request(snapshot: PullRequestSnapshot) -> TriageDecision:
    if not snapshot.files:
        return TriageDecision(
            skip_expensive_review=True, reason=NO_CHANGED_FILES_REASON, file_reasons=()
        )

    file_reasons: list[tuple[str, OmissionReason]] = []
    for file in snapshot.files:
        reason = classify_trivial_file(file)
        if reason is None:
            return TriageDecision(
                skip_expensive_review=False,
                reason=CONTAINS_REVIEWABLE_CHANGES_REASON,
                file_reasons=tuple(file_reasons),
            )
        file_reasons.append((file.path, reason))

    return TriageDecision(
        skip_expensive_review=True,
        reason=ALL_FILES_TRIVIAL_REASON,
        file_reasons=tuple(file_reasons),
    )


def review_with_triage(
    snapshot: PullRequestSnapshot,
    packed: PackedDiff,
    context: list[ReviewContextItem],
    model: ModelProvider,
    *,
    model_name: str,
    heartbeat: Callable[[], LeaseState] | None = None,
) -> TriagedReview:
    decision = triage_pull_request(snapshot)
    if decision.skip_expensive_review:
        return TriagedReview(decision=decision, outcome=_triaged_outcome(packed))
    outcome = review_pull_request(
        snapshot, packed, context, model, model_name=model_name, heartbeat=heartbeat
    )
    return TriagedReview(decision=decision, outcome=outcome)


def _triaged_outcome(packed: PackedDiff) -> ReviewOutcome:
    return ReviewOutcome(
        candidates=(),
        packing_strategy_version=packed.packing_strategy_version,
        covers_all_changed_files=packed.covers_all_changed_files,
        omitted_files=packed.omitted_files,
        cancelled=False,
    )
