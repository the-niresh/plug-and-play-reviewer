"""Phase 35 F2: retrieval ablation on the holdout."""

from __future__ import annotations

from pathlib import Path

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

def test_eval_ablation_arms_forward_different_context_lengths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from eval_holdout_fixtures import single_holdout_case

    from pr_reviewer.contracts.review_context import ReviewOutcome
    from pr_reviewer.retrieval.hybrid_search import RetrievedChunk
    from pr_reviewer.runner.eval_ablation import (
        EvalAblationDependencies,
        EvalRepositoryCache,
        review_eval_case,
    )

    context_lengths: list[int] = []

    class FakeModel:
        def complete_json(self, request: object) -> object:
            raise AssertionError("review_pull_request is spied; model must not be called")

    def fake_retrieve(*_args: object, **_kwargs: object) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id="1",
                file_path="src/caller.py",
                line_start=1,
                line_end=3,
                content="def caller():\n    return helper()\n",
                content_hash="a" * 64,
                identity="caller",
            )
        ]

    def spy_review(
        snapshot: object,
        packed: object,
        context: list[object],
        model: object,
        **kwargs: object,
    ) -> ReviewOutcome:
        del snapshot, model, kwargs
        context_lengths.append(len(context))
        return ReviewOutcome(
            candidates=(),
            packing_strategy_version=packed.packing_strategy_version,
            covers_all_changed_files=True,
            omitted_files=(),
            cost_usd=0.01,
            latency_ms=1,
        )

    monkeypatch.setattr("pr_reviewer.runner.eval_ablation.retrieve_context", fake_retrieve)
    monkeypatch.setattr("pr_reviewer.runner.eval_ablation.review_pull_request", spy_review)
    monkeypatch.setattr(
        EvalRepositoryCache,
        "ensure_checkout",
        lambda self, repository, sha: tmp_path,
    )
    monkeypatch.setattr(EvalRepositoryCache, "ensure_indexed", lambda *args, **kwargs: None)

    deps = EvalAblationDependencies(
        model=FakeModel(),
        model_name="claude-3-5-haiku-latest",
        conn=None,
        repo_cache=EvalRepositoryCache(tmp_path),
    )
    case = single_holdout_case()
    review_eval_case(case, use_retrieval=False, deps=deps)
    review_eval_case(case, use_retrieval=True, deps=deps)
    assert context_lengths == [0, 1]


def test_run_eval_sums_recorded_reviewer_cost() -> None:
    from eval_holdout_fixtures import single_holdout_case

    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.run_eval import run_eval
    from pr_reviewer.evals.types import EvalConfig

    run = run_eval(
        EvalConfig(cases=[single_holdout_case()], repeats=2),
        FixtureReviewer.with_cost(0.02),
    )
    assert run.metrics.cost_usd == 0.04


def test_zero_cost_run_leaves_metrics_at_zero_and_scorecard_refuses() -> None:
    from eval_holdout_fixtures import single_holdout_case

    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.run_eval import run_eval
    from pr_reviewer.evals.scorecard import ZERO_COST_SCORECARD_REFUSAL, generate_scorecard
    from pr_reviewer.evals.types import EvalConfig

    run = run_eval(EvalConfig(cases=[single_holdout_case()], repeats=1), FixtureReviewer.silent())
    assert run.metrics.cost_usd == 0.0
    scorecard = generate_scorecard(FixtureReviewer.silent(), cases=[single_holdout_case()])
    assert scorecard.cost_usd == ZERO_COST_SCORECARD_REFUSAL

