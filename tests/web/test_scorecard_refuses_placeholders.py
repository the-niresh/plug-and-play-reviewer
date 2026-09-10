"""Proves no number reaches the scorecard without a holdout behind it (Task 31.1)."""

from __future__ import annotations

from eval_holdout_fixtures import dev_only_cases, single_holdout_case

from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
from pr_reviewer.evals.run_eval import BaselineBlocked, run_diff_only_baseline
from pr_reviewer.evals.scorecard import ZERO_COST_SCORECARD_REFUSAL, generate_scorecard

_NUMERIC_FIELDS = (
    "precision_per_finding",
    "precision_per_case",
    "recall_per_finding",
    "recall_per_case",
    "false_findings_per_pr",
    "cost_usd",
    "reviewed_pr_count",
)


def test_every_field_is_the_verbatim_refusal_when_the_holdout_is_empty() -> None:
    cases = dev_only_cases()
    try:
        run_diff_only_baseline(cases, FixtureReviewer.perfect())
    except BaselineBlocked as exc:
        expected_refusal = str(exc)
    else:
        raise AssertionError("synthetic dataset must have zero holdout cases")

    scorecard = generate_scorecard(FixtureReviewer.perfect(), cases=cases)
    for field in _NUMERIC_FIELDS:
        value = getattr(scorecard, field)
        assert isinstance(value, str), f"{field} is {value!r}, not the refusal string"
        assert value == expected_refusal, f"{field} does not match the real BaselineBlocked message"


def test_every_field_is_the_zero_cost_refusal_when_nothing_was_measured() -> None:
    scorecard = generate_scorecard(
        FixtureReviewer.perfect(), cases=[single_holdout_case()], repeats=3
    )
    for field in _NUMERIC_FIELDS:
        value = getattr(scorecard, field)
        assert isinstance(value, str), f"{field} is {value!r}, not the refusal string"
        assert value == ZERO_COST_SCORECARD_REFUSAL, f"{field} does not match the zero-cost refusal"
