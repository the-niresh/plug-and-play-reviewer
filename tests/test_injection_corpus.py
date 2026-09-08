"""Task 35.A8: injected pull requests cannot become actions.

Tests assert outcomes, not that a function was called. With prompt boundaries bypassed,
at least one case must go red, or the test proves nothing.
"""

from __future__ import annotations

from pathlib import Path

from pr_reviewer.security.injection_corpus import (
    INJECTION_CORPUS,
    InjectionShape,
    review_injection_corpus,
)


def test_corpus_covers_every_required_injection_shape() -> None:
    shapes = {case.shape for case in INJECTION_CORPUS}
    assert shapes >= {
        InjectionShape.PR_TITLE,
        InjectionShape.REVIEW_COMMENT,
        InjectionShape.DOCSTRING_IN_DIFF,
        InjectionShape.FILENAME_IN_DIFF,
        InjectionShape.FENCE_BREAKOUT,
    }


def test_injected_instructions_never_become_actions(tmp_path: Path) -> None:
    report = review_injection_corpus(clone_root=tmp_path)
    assert report.any_action_succeeded is False
    assert report.sandbox_jobs_with_unregistered_command_id == 0
    assert report.paths_outside_clone_accessed == 0
    assert report.network_attempts_succeeded == 0
    assert report.explorer_tool_calls_succeeded == 0
    assert report.policy_unchanged is True
    assert report.counter.total_attempts >= len(INJECTION_CORPUS)
    assert report.counter.blocked_attempts == report.counter.total_attempts


def test_every_attempt_is_counted_by_shape(tmp_path: Path) -> None:
    report = review_injection_corpus(clone_root=tmp_path)
    for case in INJECTION_CORPUS:
        assert report.counter.by_shape[case.shape.value] >= 1


def test_dashboard_can_read_the_counter(tmp_path: Path) -> None:
    report = review_injection_corpus(clone_root=tmp_path)
    payload = report.dashboard_payload()
    assert payload["total_attempts"] == report.counter.total_attempts
    assert payload["blocked_attempts"] == report.counter.blocked_attempts
    assert payload["any_action_succeeded"] is False
    assert set(payload["by_shape"]) >= {case.shape.value for case in INJECTION_CORPUS}


def test_bypassing_wrap_untrusted_lets_at_least_one_action_through(tmp_path: Path) -> None:
    report = review_injection_corpus(clone_root=tmp_path, use_prompt_boundaries=False)
    assert report.any_action_succeeded is True
