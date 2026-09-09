"""Phase 31: the scorecard generator.

Every number here comes from a real eval run against the frozen holdout, produced by
run_diff_only_baseline. When the holdout is empty, or the run recorded zero cost,
generate_scorecard does not compute anything and does not invent a number: every field
becomes the verbatim BaselineBlocked message. There is no
hand-typed scorecard and no placeholder path.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from pr_reviewer.evals.run_eval import (
    BaselineBlocked,
    load_public_eval_cases,
    run_diff_only_baseline,
)
from pr_reviewer.evals.types import EvalCase, ReviewerCallable

DEFAULT_SCORECARD_PATH = Path(__file__).resolve().parents[3] / "docs" / "reports" / "scorecard.json"

ZERO_COST_SCORECARD_REFUSAL = (
    "no measured run; refusing to report a scorecard from a zero-cost run"
)


class Scorecard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str | None = None
    measured_at: str | None = None
    sample_limitation: str | None = None
    precision_per_finding: float | str
    precision_per_case: float | str
    recall_per_finding: float | str
    recall_per_case: float | str
    false_findings_per_pr: float | str
    cost_usd: float | str
    reviewed_pr_count: int | str


_METRIC_FIELDS = (
    "precision_per_finding",
    "precision_per_case",
    "recall_per_finding",
    "recall_per_case",
    "false_findings_per_pr",
    "cost_usd",
    "reviewed_pr_count",
)


def is_scorecard_refusal(scorecard: Scorecard) -> bool:
    """True when every metric field is a refusal string, not a measured number."""
    return all(isinstance(getattr(scorecard, field), str) for field in _METRIC_FIELDS)


def validate_published_scorecard(scorecard: Scorecard) -> None:
    """Require provenance fields when the on-disk scorecard holds a live baseline."""
    if is_scorecard_refusal(scorecard):
        return
    missing = [
        name
        for name, value in (
            ("model", scorecard.model),
            ("measured_at", scorecard.measured_at),
            ("sample_limitation", scorecard.sample_limitation),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"published scorecard missing required fields: {joined}")
    if not isinstance(scorecard.cost_usd, (int, float)) or scorecard.cost_usd <= 0:
        raise ValueError("published scorecard cost_usd must be a positive number")
    if not isinstance(scorecard.reviewed_pr_count, int) or scorecard.reviewed_pr_count <= 0:
        raise ValueError("published scorecard reviewed_pr_count must be a positive integer")


def generate_scorecard(
    reviewer: ReviewerCallable,
    *,
    cases: Sequence[EvalCase] | None = None,
    repeats: int = 3,
) -> Scorecard:
    source_cases = list(cases) if cases is not None else load_public_eval_cases()
    try:
        run = run_diff_only_baseline(source_cases, reviewer, repeats=repeats)
        if run.metrics.cost_usd <= 0:
            raise BaselineBlocked(ZERO_COST_SCORECARD_REFUSAL)
    except BaselineBlocked as exc:
        refusal = str(exc)
        return Scorecard(
            precision_per_finding=refusal,
            precision_per_case=refusal,
            recall_per_finding=refusal,
            recall_per_case=refusal,
            false_findings_per_pr=refusal,
            cost_usd=refusal,
            reviewed_pr_count=refusal,
        )

    metrics = run.metrics
    return Scorecard(
        precision_per_finding=metrics.precision_per_finding,
        precision_per_case=metrics.precision_per_case,
        recall_per_finding=metrics.recall_per_finding,
        recall_per_case=metrics.recall_per_case,
        false_findings_per_pr=metrics.false_findings_per_pr,
        cost_usd=metrics.cost_usd,
        reviewed_pr_count=metrics.reviewed_pr_count,
    )

def write_scorecard(path: Path = DEFAULT_SCORECARD_PATH) -> Scorecard:
    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer

    scorecard = generate_scorecard(FixtureReviewer.perfect())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(scorecard.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return scorecard


def main() -> int:
    write_scorecard()
    print(f"Wrote {DEFAULT_SCORECARD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
