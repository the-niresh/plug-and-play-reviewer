"""Phase 35 F2: retrieval ablation on the holdout."""

from __future__ import annotations

import pytest
from eval_holdout_fixtures import dev_only_cases, single_holdout_case

from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
from pr_reviewer.evals.run_eval import (
    BaselineBlocked,
    format_retrieval_ablation,
    run_retrieval_ablation,
)


def test_retrieval_ablation_is_blocked_on_a_synthetic_empty_holdout() -> None:
    with pytest.raises(BaselineBlocked, match="holdout"):
        run_retrieval_ablation(
            dev_only_cases(),
            FixtureReviewer.silent(),
            FixtureReviewer.perfect(),
        )


def test_retrieval_ablation_reports_both_arms_and_the_deltas() -> None:
    result = run_retrieval_ablation(
        [single_holdout_case()],
        FixtureReviewer.silent(),
        FixtureReviewer.perfect(),
        repeats=2,
    )
    assert result.diff_only.metrics.recall_per_finding == 0.0
    assert result.retrieval_backed.metrics.recall_per_finding == 1.0
    assert result.recall_delta == 1.0
    assert result.precision_delta == 1.0
    assert result.false_findings_per_pr_delta == 0.0


def test_retrieval_ablation_format_includes_both_arms_and_deltas() -> None:
    result = run_retrieval_ablation(
        [single_holdout_case()],
        FixtureReviewer.noisy(),
        FixtureReviewer.perfect(),
        repeats=1,
    )
    text = format_retrieval_ablation(result)
    assert "diff-only precision=" in text
    assert "retrieval precision=" in text
    assert "delta precision=" in text
    assert result.precision_delta > 0


def test_real_holdout_ablation_with_identical_fixture_reviewers_is_a_tie() -> None:
    from pr_reviewer.evals.run_eval import load_public_eval_cases

    result = run_retrieval_ablation(
        load_public_eval_cases(),
        FixtureReviewer.perfect(),
        FixtureReviewer.perfect(),
    )
    assert result.precision_delta == 0.0
    assert result.recall_delta == 0.0
    assert result.false_findings_per_pr_delta == 0.0
