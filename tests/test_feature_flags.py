"""Task 31.2 and phase 35 F1: feature-flag measurements refuse on empty holdout."""

from __future__ import annotations

from eval_holdout_fixtures import dev_only_cases

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.evals.feature_flags import generate_feature_flags
from pr_reviewer.evals.run_eval import (
    BaselineBlocked,
    load_public_eval_cases,
    run_context_source_comparison,
    run_retrieval_comparison,
    run_specialist_comparison,
)
from pr_reviewer.evals.types import EvalCase


def _empty_reviewer(_case: EvalCase) -> list[FindingCandidate]:
    return []


def test_every_flag_is_off_until_a_real_switch_turns_it_on() -> None:
    flags = generate_feature_flags()
    by_name = {flag.name: flag for flag in flags}
    assert set(by_name) == {"retrieval", "code_graph", "specialists", "langgraph"}
    assert by_name["retrieval"].enabled is False
    assert by_name["code_graph"].enabled is False
    assert by_name["specialists"].enabled is False
    assert by_name["langgraph"].enabled is False


def test_each_measurement_is_the_real_verbatim_refusal_on_a_synthetic_empty_holdout() -> None:
    cases = dev_only_cases()
    flags = generate_feature_flags(cases)
    by_name = {flag.name: flag for flag in flags}

    try:
        run_retrieval_comparison(cases, _empty_reviewer, _empty_reviewer)
        raise AssertionError("synthetic dataset must have zero holdout cases")
    except BaselineBlocked as exc:
        assert by_name["retrieval"].measurement == str(exc)

    try:
        run_context_source_comparison(cases, _empty_reviewer, _empty_reviewer, _empty_reviewer)
        raise AssertionError("synthetic dataset must have zero holdout cases")
    except BaselineBlocked as exc:
        assert by_name["code_graph"].measurement == str(exc)

    try:
        run_specialist_comparison(cases, _empty_reviewer, _empty_reviewer)
        raise AssertionError("synthetic dataset must have zero holdout cases")
    except BaselineBlocked as exc:
        assert by_name["specialists"].measurement == str(exc)

    for flag in flags:
        assert "holdout is empty" in flag.measurement


def test_real_dataset_reports_pending_comparisons_instead_of_a_holdout_refusal() -> None:
    flags = generate_feature_flags(load_public_eval_cases())
    for flag in flags:
        assert "holdout is empty" not in flag.measurement
        assert "not run without configured reviewers" in flag.measurement
