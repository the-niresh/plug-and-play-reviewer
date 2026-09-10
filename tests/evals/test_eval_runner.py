"""Eval harness tests (master Task 11, phase 35 F1).

The public dataset now has 13 judged cases. Refusal guards use a synthetic dev-only list.
Imports of new modules stay inside test bodies.
"""

from __future__ import annotations

import pytest
from eval_holdout_fixtures import dev_only_cases
from repo_paths import REPO_ROOT

REPO = REPO_ROOT


def test_public_dataset_has_thirteen_cases_with_six_dev_and_seven_holdout() -> None:
    from pr_reviewer.evals.run_eval import load_public_eval_cases

    cases = load_public_eval_cases()
    assert len(cases) == 13
    assert sum(1 for case in cases if case.split == "dev") == 6
    assert sum(1 for case in cases if case.split == "holdout") == 7


def test_harness_runs_fixture_reviewer_on_dev_cases_only() -> None:
    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.run_eval import load_public_eval_cases, run_eval
    from pr_reviewer.evals.types import EvalConfig

    dev_cases = [case for case in load_public_eval_cases() if case.split == "dev"]
    run = run_eval(EvalConfig(cases=dev_cases, repeats=3), FixtureReviewer.perfect())
    assert run.metrics.precision_per_finding == 1.0
    assert run.metrics.recall_per_finding == 1.0
    assert run.metrics.reviewed_pr_count == 18


def test_diff_only_baseline_is_blocked_when_holdout_is_empty() -> None:
    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.run_eval import BaselineBlocked, run_diff_only_baseline

    with pytest.raises(BaselineBlocked, match="holdout"):
        run_diff_only_baseline(dev_only_cases(), FixtureReviewer.perfect())


def test_diff_only_baseline_runs_on_the_real_holdout() -> None:
    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.run_eval import load_public_eval_cases, run_diff_only_baseline

    run = run_diff_only_baseline(load_public_eval_cases(), FixtureReviewer.perfect())
    assert run.metrics.precision_per_finding == 1.0
    assert run.metrics.reviewed_pr_count == 21


def test_eval_runner_still_imports_nothing_from_models() -> None:
    from boundary_guards import _imports_matching_prefix, collect_imports

    evals_imports = collect_imports(REPO / "src" / "pr_reviewer" / "evals")
    assert not _imports_matching_prefix(evals_imports, "pr_reviewer.models")
    source = (REPO / "src" / "pr_reviewer" / "evals" / "run_eval.py").read_text(
        encoding="utf-8"
    )
    assert "httpx" not in source
    assert "openai" not in source
    assert "anthropic" not in source
