"""Run an injected reviewer over cases. No model HTTP client lives here."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.evals.match_findings import MatchResult, match_findings
from pr_reviewer.evals.metrics import compute_metrics
from pr_reviewer.evals.types import (
    EvalCase,
    EvalConfig,
    EvalMetrics,
    EvalReviewResult,
    EvalRun,
    RetrievalAblationResult,
    ReviewerCallable,
)

_PUBLIC_CASES = (
    Path(__file__).resolve().parents[3] / "datasets" / "public" / "eval_cases.jsonl"
)


class BaselineBlocked(Exception):
    """Holdout is empty. Refusing to publish a baseline number."""


def load_public_eval_cases(path: Path | None = None) -> list[EvalCase]:
    target = path or _PUBLIC_CASES
    cases: list[EvalCase] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(EvalCase.model_validate_json(line))
    return cases


def _normalize_reviewer_output(
    raw: EvalReviewResult | Sequence[FindingCandidate],
) -> EvalReviewResult:
    if isinstance(raw, EvalReviewResult):
        return raw
    return EvalReviewResult(findings=tuple(raw))


def run_eval(config: EvalConfig, reviewer: ReviewerCallable) -> EvalRun:
    results: list[MatchResult] = []
    total_cost_usd = 0.0
    total_latency_ms = 0
    schema_rejected_findings = 0
    grounding_rejected_findings = 0
    duplicate_rejected_findings = 0
    for _ in range(config.repeats):
        for case in config.cases:
            review = _normalize_reviewer_output(reviewer(case))
            total_cost_usd += review.cost_usd
            total_latency_ms += review.latency_ms
            schema_rejected_findings += review.schema_rejected_findings
            grounding_rejected_findings += review.grounding_rejected_findings
            duplicate_rejected_findings += review.duplicate_rejected_findings
            results.append(match_findings(case.expected_labels, list(review.findings)))
    metrics = compute_metrics(
        results,
        reviewed_pr_count=len(results),
        latency_ms=total_latency_ms,
        cost_usd=total_cost_usd,
    )
    metrics = metrics.model_copy(
        update={
            "schema_rejected_findings": schema_rejected_findings,
            "grounding_rejected_findings": grounding_rejected_findings,
            "duplicate_rejected_findings": duplicate_rejected_findings,
        }
    )
    return EvalRun(metrics=metrics)


def run_diff_only_baseline(
    cases: Sequence[EvalCase],
    reviewer: ReviewerCallable,
    repeats: int = 3,
) -> EvalRun:
    holdout = [case for case in cases if case.split == "holdout"]
    if not holdout:
        raise BaselineBlocked("holdout is empty; refusing to report a baseline")
    return run_eval(EvalConfig(cases=list(holdout), repeats=repeats), reviewer)


def run_retrieval_comparison(
    cases: Sequence[EvalCase],
    without_retrieval: ReviewerCallable,
    with_retrieval: ReviewerCallable,
    repeats: int = 3,
) -> tuple[EvalRun, EvalRun]:
    holdout = [case for case in cases if case.split == "holdout"]
    if not holdout:
        raise BaselineBlocked(
            "holdout is empty; refusing to report a retrieval comparison"
        )
    config = EvalConfig(cases=list(holdout), repeats=repeats)
    return run_eval(config, without_retrieval), run_eval(config, with_retrieval)


def run_context_source_comparison(
    cases: Sequence[EvalCase],
    profile_only: ReviewerCallable,
    graph_only: ReviewerCallable,
    profile_plus_graph: ReviewerCallable,
    repeats: int = 3,
) -> tuple[EvalRun, EvalRun, EvalRun]:
    holdout = [case for case in cases if case.split == "holdout"]
    if not holdout:
        raise BaselineBlocked(
            "holdout is empty; refusing to report a context-source comparison"
        )
    config = EvalConfig(cases=list(holdout), repeats=repeats)
    return (
        run_eval(config, profile_only),
        run_eval(config, graph_only),
        run_eval(config, profile_plus_graph),
    )


def run_specialist_comparison(
    cases: Sequence[EvalCase],
    one_agent: ReviewerCallable,
    specialists: ReviewerCallable,
    repeats: int = 3,
) -> tuple[EvalRun, EvalRun]:
    holdout = [case for case in cases if case.split == "holdout"]
    if not holdout:
        raise BaselineBlocked(
            "holdout is empty; refusing to report a specialist comparison"
        )
    config = EvalConfig(cases=list(holdout), repeats=repeats)
    return run_eval(config, one_agent), run_eval(config, specialists)




def run_retrieval_ablation(
    cases: Sequence[EvalCase],
    diff_only: ReviewerCallable,
    retrieval_backed: ReviewerCallable,
    repeats: int = 3,
) -> RetrievalAblationResult:
    """Same holdout cases, retrieval off then on. Reports both arms and the deltas."""
    diff_run, retrieval_run = run_retrieval_comparison(
        cases, diff_only, retrieval_backed, repeats=repeats
    )
    diff_metrics = diff_run.metrics
    retrieval_metrics = retrieval_run.metrics
    return RetrievalAblationResult(
        diff_only=diff_run,
        retrieval_backed=retrieval_run,
        precision_delta=(
            retrieval_metrics.precision_per_finding - diff_metrics.precision_per_finding
        ),
        recall_delta=retrieval_metrics.recall_per_finding - diff_metrics.recall_per_finding,
        false_findings_per_pr_delta=(
            retrieval_metrics.false_findings_per_pr - diff_metrics.false_findings_per_pr
        ),
    )


def _arm_rejection_summary(metrics: EvalMetrics) -> str:
    return (
        f"schema_rejected={metrics.schema_rejected_findings}, "
        f"grounding_rejected={metrics.grounding_rejected_findings}, "
        f"duplicate_rejected={metrics.duplicate_rejected_findings}"
    )


def _arm_status(metrics: EvalMetrics) -> str | None:
    if metrics.schema_rejected_findings > 0 and metrics.useful_finding_count == 0:
        return "all_findings_rejected"
    return None


def format_retrieval_ablation(result: RetrievalAblationResult) -> str:
    diff = result.diff_only.metrics
    retrieval = result.retrieval_backed.metrics
    diff_status = _arm_status(diff)
    retrieval_status = _arm_status(retrieval)
    parts = [
        "diff-only precision="
        f"{diff.precision_per_finding:.3f}, recall={diff.recall_per_finding:.3f}, "
        f"false/pr={diff.false_findings_per_pr:.3f}, "
        f"{_arm_rejection_summary(diff)}",
        "retrieval precision="
        f"{retrieval.precision_per_finding:.3f}, recall={retrieval.recall_per_finding:.3f}, "
        f"false/pr={retrieval.false_findings_per_pr:.3f}, "
        f"{_arm_rejection_summary(retrieval)}",
        "delta precision="
        f"{result.precision_delta:+.3f}, recall={result.recall_delta:+.3f}, "
        f"false/pr={result.false_findings_per_pr_delta:+.3f}",
    ]
    if diff_status:
        parts.append(f"diff-only status={diff_status}")
    if retrieval_status:
        parts.append(f"retrieval status={retrieval_status}")
    return "; ".join(parts)


def useful_findings_per_dollar(run: EvalRun) -> float:
    if run.metrics.cost_usd <= 0:
        raise BaselineBlocked(
            "cost_usd is zero; refusing to report useful findings per dollar"
        )
    return run.metrics.useful_finding_count / run.metrics.cost_usd


def write_eval_report(run: EvalRun, path: Path) -> None:
    path.write_text(run.model_dump_json(indent=2), encoding="utf-8")
