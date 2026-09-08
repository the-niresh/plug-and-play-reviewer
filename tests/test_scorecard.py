"""Scorecard generator (Task 31.1, phase 35 F1): real eval run or verbatim refusal."""

from __future__ import annotations

from eval_holdout_fixtures import dev_only_cases, single_holdout_case

from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
from pr_reviewer.evals.scorecard import ZERO_COST_SCORECARD_REFUSAL, generate_scorecard


def test_scorecard_is_the_refusal_on_a_synthetic_empty_holdout() -> None:
    scorecard = generate_scorecard(
        FixtureReviewer.perfect(), cases=dev_only_cases(), repeats=3
    )
    assert scorecard.precision_per_finding == "holdout is empty; refusing to report a baseline"
    assert scorecard.reviewed_pr_count == "holdout is empty; refusing to report a baseline"


def test_scorecard_refuses_a_zero_cost_run_on_the_public_holdout() -> None:
    scorecard = generate_scorecard(FixtureReviewer.perfect())
    assert scorecard.precision_per_finding == ZERO_COST_SCORECARD_REFUSAL
    assert scorecard.cost_usd == ZERO_COST_SCORECARD_REFUSAL
    assert scorecard.reviewed_pr_count == ZERO_COST_SCORECARD_REFUSAL


def test_scorecard_refuses_a_zero_cost_run_on_a_synthetic_non_empty_holdout() -> None:
    scorecard = generate_scorecard(
        FixtureReviewer.perfect(), cases=[single_holdout_case()], repeats=3
    )
    assert scorecard.recall_per_finding == ZERO_COST_SCORECARD_REFUSAL
    assert scorecard.false_findings_per_pr == ZERO_COST_SCORECARD_REFUSAL
