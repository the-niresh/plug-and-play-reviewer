"""Scorecard generator (Task 31.1, phase 35 F1): real eval run or verbatim refusal."""

from __future__ import annotations

from eval_holdout_fixtures import dev_only_cases, single_holdout_case

from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
from pr_reviewer.evals.scorecard import (
    ZERO_COST_SCORECARD_REFUSAL,
    Scorecard,
    generate_scorecard,
    is_scorecard_refusal,
    validate_published_scorecard,
)


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


def test_validate_published_scorecard_requires_provenance_on_measured_numbers() -> None:
    scorecard = Scorecard(
        precision_per_finding=0.5,
        precision_per_case=0.5,
        recall_per_finding=0.5,
        recall_per_case=0.5,
        false_findings_per_pr=0.1,
        cost_usd=0.01,
        reviewed_pr_count=7,
    )
    try:
        validate_published_scorecard(scorecard)
    except ValueError as exc:
        assert "published scorecard missing required fields" in str(exc)
    else:
        raise AssertionError("measured scorecard without provenance must be rejected")


def test_validate_published_scorecard_accepts_provenance_on_measured_numbers() -> None:
    scorecard = Scorecard(
        model="gpt-4o-mini",
        measured_at="2026-09-10",
        sample_limitation="7 holdout cases, all from the Zod repository",
        precision_per_finding=0.667,
        precision_per_case=0.571,
        recall_per_finding=0.571,
        recall_per_case=0.571,
        false_findings_per_pr=0.286,
        cost_usd=0.004606,
        reviewed_pr_count=7,
    )
    validate_published_scorecard(scorecard)
    assert not is_scorecard_refusal(scorecard)


def test_scorecard_refuses_a_zero_cost_run_on_a_synthetic_non_empty_holdout() -> None:
    scorecard = generate_scorecard(
        FixtureReviewer.perfect(), cases=[single_holdout_case()], repeats=3
    )
    assert scorecard.recall_per_finding == ZERO_COST_SCORECARD_REFUSAL
    assert scorecard.false_findings_per_pr == ZERO_COST_SCORECARD_REFUSAL
