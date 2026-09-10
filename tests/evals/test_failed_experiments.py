"""Failed-experiment log must name the nine misses and the tests that catch them."""

from __future__ import annotations

from repo_paths import REPO_ROOT

REPO = REPO_ROOT
DOC = REPO / "docs" / "FAILED_EXPERIMENTS.md"

EXPERIMENT_NEEDLES = (
    "optimistic precision denominator",
    "header-only PEM redaction",
    "direct-import-only boundary check",
    "mine_eval_candidates stub",
    "confidence default",
    "fence breakout in wrap_untrusted",
    "fail-open dashboard guard",
    "invented useful_findings_per_dollar",
    "unknown-age feedback default",
)

CATCHER_NEEDLES = (
    "tests/evals/test_eval_matching.py::test_semantic_near_miss_needs_human_match_and_is_not_a_pass",
    "tests/evals/test_eval_metrics.py::test_metrics_cover_precision_recall_and_cost",
    "tests/integration/test_connector_contracts.py::test_redaction_removes_pem_bodies_not_just_headers",
    "tests/security/test_package_boundaries.py::test_guarded_package_inventory_matches_snapshot",
    "tests/security/test_package_boundaries.py::test_guarded_packages_have_no_transitive_forbidden_reach",
    "tests/evals/test_eval_mining.py::test_mining_emits_candidates_not_labels",
    "tests/evals/test_eval_mining.py::test_commit_message_is_evidence_not_ground_truth",
    "tests/evals/test_eval_mining.py::test_mining_emits_one_candidate_per_commit",
    "tests/evals/test_eval_regression_gate.py::test_routing_source_does_not_read_confidence",
    "tests/reviewer/test_notification_policy.py::test_model_cannot_bypass_routing_through_severity_confidence_rationale_or_title",
    "tests/retrieval/test_code_graph.py::test_missing_confidence_does_not_count_toward_sensitivity",
    "tests/security/test_prompt_boundaries.py::test_wrap_untrusted_strips_inner_delimiter_breakout",
    "tests/control_plane/test_dashboard_auth.py::test_unauthenticated_docs_and_unknown_paths_are_not_ok",
    "tests/evals/test_eval_regression_gate.py::test_useful_findings_per_dollar_is_blocked_without_cost",
    "tests/evals/test_eval_regression_gate.py::test_useful_findings_per_dollar_uses_useful_finding_count",
    "tests/integration/test_feedback_candidates.py::test_missing_observed_at_is_dropped_while_a_fresh_event_is_kept",
)


def test_failed_experiments_doc_names_the_nine_and_their_catchers() -> None:
    assert DOC.is_file()
    text = DOC.read_text(encoding="utf-8")
    for needle in EXPERIMENT_NEEDLES + CATCHER_NEEDLES:
        assert needle in text, needle
    assert "tests/evals/test_failed_experiments.py" in text
