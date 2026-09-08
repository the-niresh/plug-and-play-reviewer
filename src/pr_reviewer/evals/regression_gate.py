"""Compare eval reports, score calibration, and flag drift. No model calls."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.evals.run_eval import (
    BaselineBlocked,
    load_public_eval_cases,
    run_diff_only_baseline,
)
from pr_reviewer.evals.types import EvalCase, EvalRun, ReviewerCallable


class EvalThresholds(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    min_precision_per_finding: float = Field(ge=0, le=1)
    max_false_findings_per_pr: float = Field(ge=0)
    min_high_value_recall: float = Field(ge=0, le=1)
    max_cost_usd: float = Field(ge=0)
    max_latency_ms: int = Field(ge=0)


@dataclass(frozen=True)
class GateResult:
    passed: bool
    blocked_metrics: tuple[str, ...]


@dataclass(frozen=True)
class CalibrationBucket:
    lower: float
    upper: float
    count: int
    accuracy: float
    mean_confidence: float


@dataclass(frozen=True)
class DriftSnapshot:
    rejection_rate: float
    dispute_rate: float
    no_finding_rate: float
    cost_usd: float
    latency_ms: int
    retrieval_miss_rate: float


def compare_eval_reports(
    candidate: EvalRun,
    baseline: EvalRun,
    thresholds: EvalThresholds,
) -> GateResult:
    blocked: list[str] = []
    cand = candidate.metrics
    base = baseline.metrics
    if (
        cand.precision_per_finding < base.precision_per_finding
        or cand.precision_per_finding < thresholds.min_precision_per_finding
    ):
        blocked.append("precision_per_finding")
    if (
        cand.false_findings_per_pr > base.false_findings_per_pr
        or cand.false_findings_per_pr > thresholds.max_false_findings_per_pr
    ):
        blocked.append("false_findings_per_pr")
    if (
        cand.recall_per_finding < base.recall_per_finding
        or cand.recall_per_finding < thresholds.min_high_value_recall
    ):
        blocked.append("high_value_recall")
    if cand.cost_usd > base.cost_usd or cand.cost_usd > thresholds.max_cost_usd:
        blocked.append("cost_usd")
    if cand.latency_ms > base.latency_ms or cand.latency_ms > thresholds.max_latency_ms:
        blocked.append("latency_ms")
    return GateResult(passed=not blocked, blocked_metrics=tuple(blocked))


def brier_score(predictions: Sequence[tuple[float, bool]]) -> float:
    if not predictions:
        return 0.0
    total = sum((confidence - float(outcome)) ** 2 for confidence, outcome in predictions)
    return total / len(predictions)


def calibration_buckets(
    predictions: Sequence[tuple[float, bool]],
    *,
    edges: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
) -> tuple[CalibrationBucket, ...]:
    buckets: list[CalibrationBucket] = []
    for index, lower in enumerate(edges[:-1]):
        upper = edges[index + 1]
        if index == len(edges) - 2:
            members = [item for item in predictions if lower <= item[0] <= upper]
        else:
            members = [item for item in predictions if lower <= item[0] < upper]
        if not members:
            continue
        hits = sum(1 for _confidence, outcome in members if outcome)
        mean_confidence = sum(confidence for confidence, _outcome in members) / len(members)
        buckets.append(
            CalibrationBucket(
                lower=lower,
                upper=upper,
                count=len(members),
                accuracy=hits / len(members),
                mean_confidence=mean_confidence,
            )
        )
    return tuple(buckets)


def detect_drift(current: DriftSnapshot, baseline: DriftSnapshot) -> tuple[str, ...]:
    alerts: list[str] = []
    if current.rejection_rate > baseline.rejection_rate:
        alerts.append("rejection_rate")
    if current.dispute_rate > baseline.dispute_rate:
        alerts.append("dispute_rate")
    if current.no_finding_rate > baseline.no_finding_rate:
        alerts.append("no_finding_rate")
    if current.cost_usd > baseline.cost_usd:
        alerts.append("cost_usd")
    if current.latency_ms > baseline.latency_ms:
        alerts.append("latency_ms")
    if current.retrieval_miss_rate > baseline.retrieval_miss_rate:
        alerts.append("retrieval_miss_rate")
    return tuple(alerts)


class NoReviewerConfigured(Exception):
    """The regression gate has no reviewer wired in for measurement."""


class BaselineReportMissing(Exception):
    """Holdout has cases but no frozen baseline report exists to compare against."""


@dataclass(frozen=True)
class GateOutcome:
    """skipped=True means the holdout is empty: a deliberate, visible non-result.

    It is never a pass and never a fake number. result is only set when a real
    comparison ran.
    """

    skipped: bool
    reason: str | None
    result: GateResult | None


DEFAULT_BASELINE_REPORT = (
    Path(__file__).resolve().parents[3] / "datasets" / "public" / "regression_baseline.json"
)

NO_REVIEWER_CONFIGURED_REFUSAL = (
    "no reviewer configured; refusing to measure without a configured reviewer"
)

DEFAULT_THRESHOLDS = EvalThresholds(
    min_precision_per_finding=0.6,
    max_false_findings_per_pr=1.0,
    min_high_value_recall=0.5,
    max_cost_usd=1.0,
    max_latency_ms=120_000,
)


def _unconfigured_reviewer(_case: EvalCase) -> Sequence[FindingCandidate]:
    raise NoReviewerConfigured()


def run_diff_only_gate(
    cases: Sequence[EvalCase],
    reviewer: ReviewerCallable,
    baseline_report: Path,
    thresholds: EvalThresholds,
    repeats: int = 3,
) -> GateOutcome:
    """Run the diff-only baseline and compare it to a frozen report.

    An empty holdout is a clear, visible skip (BaselineBlocked), never a silent pass.
    A holdout with cases but no baseline report on disk is an error, not a skip: there
    is nothing honest to compare against, so this refuses rather than reporting green.
    """
    try:
        candidate = run_diff_only_baseline(cases, reviewer, repeats=repeats)
    except BaselineBlocked as exc:
        return GateOutcome(skipped=True, reason=str(exc), result=None)
    if not baseline_report.exists():
        raise BaselineReportMissing(
            f"holdout has cases but no baseline report exists at {baseline_report}; "
            "Task 35.F2 must measure and commit the diff-only baseline before this "
            "gate can compare against it"
        )
    baseline = EvalRun.model_validate_json(baseline_report.read_text(encoding="utf-8"))
    result = compare_eval_reports(candidate, baseline, thresholds)
    return GateOutcome(skipped=False, reason=None, result=result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pr-reviewer-regression-gate")
    parser.add_argument("--cases", type=Path, default=None)
    parser.add_argument("--baseline-report", type=Path, default=DEFAULT_BASELINE_REPORT)
    args = parser.parse_args(argv)

    cases = load_public_eval_cases(args.cases)
    try:
        outcome = run_diff_only_gate(
            cases, _unconfigured_reviewer, args.baseline_report, DEFAULT_THRESHOLDS
        )
    except NoReviewerConfigured:
        outcome = GateOutcome(
            skipped=True,
            reason=NO_REVIEWER_CONFIGURED_REFUSAL,
            result=None,
        )
    except BaselineReportMissing as exc:
        print(f"ERROR: {exc}")
        return 1

    if outcome.skipped:
        message = f"SKIP: {outcome.reason}"
        print(message)
        print(f"::warning title=Eval regression gate skipped::{message}")
        return 0

    assert outcome.result is not None
    if not outcome.result.passed:
        blocked = ", ".join(outcome.result.blocked_metrics)
        print(f"REGRESSION: blocked on {blocked}")
        return 1

    print("PASS: no regression against the baseline or thresholds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
