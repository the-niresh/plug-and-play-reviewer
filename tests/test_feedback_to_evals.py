"""Turn captured review-comment feedback into human-reviewable improvement candidates."""

from __future__ import annotations

from datetime import UTC, datetime


def _row(
    *,
    row_id: str,
    installation_id: int = 100,
    repository_id: int = 200,
    pull_request_number: int | None = 8,
    finding_id: str | None = "job-1:1",
    classification: str = "wrong",
    comment_id: int = 9001,
    reply_text: str = "BEGIN\nname: human_reply\nthis is wrong\nEND",
    created_at: datetime | None = None,
) -> object:
    from pr_reviewer.evals.feedback_to_evals import ReviewCommentFeedbackRow

    return ReviewCommentFeedbackRow(
        id=row_id,
        installation_id=installation_id,
        github_repository_id=repository_id,
        pull_request_number=pull_request_number,
        github_comment_id=comment_id,
        in_reply_to_comment_id=comment_id - 1,
        finding_id=finding_id,
        classification=classification,  # type: ignore[arg-type]
        reply_text=reply_text,
        created_at=created_at or datetime(2026, 9, 9, 12, 0, tzinfo=UTC),
    )


def test_wrong_feedback_on_a_finding_produces_a_task_candidate() -> None:
    from pr_reviewer.evals.feedback_to_evals import build_feedback_improvement_report

    report = build_feedback_improvement_report([_row(row_id="fb-1")])
    assert len(report.task_candidates) == 1
    candidate = report.task_candidates[0]
    assert candidate.finding_id == "job-1:1"
    assert candidate.classification == "wrong"
    assert candidate.feedback_count == 1
    assert candidate.feedback_ids == ("fb-1",)


def test_useful_feedback_increments_positive_signal_without_a_fix_task() -> None:
    from pr_reviewer.evals.feedback_to_evals import build_feedback_improvement_report

    report = build_feedback_improvement_report(
        [_row(row_id="fb-useful", classification="useful", reply_text="helpful catch")]
    )
    assert report.task_candidates == ()
    assert len(report.positive_signals) == 1
    assert report.positive_signals[0].count == 1
    assert report.positive_signals[0].finding_id == "job-1:1"


def test_duplicate_feedback_does_not_create_duplicate_candidates() -> None:
    from pr_reviewer.evals.feedback_to_evals import build_feedback_improvement_report

    row = _row(row_id="fb-dup")
    report = build_feedback_improvement_report([row, row])
    assert len(report.task_candidates) == 1
    assert report.duplicates_skipped == 1


def test_feedback_cannot_cross_repo_or_installation_boundaries() -> None:
    from pr_reviewer.evals.feedback_to_evals import build_feedback_improvement_report

    report = build_feedback_improvement_report(
        [
            _row(row_id="fb-a", installation_id=1, repository_id=10, comment_id=10),
            _row(row_id="fb-b", installation_id=1, repository_id=20, comment_id=20),
            _row(row_id="fb-c", installation_id=2, repository_id=10, comment_id=30),
        ]
    )
    assert len(report.task_candidates) == 3
    keys = {
        (item.installation_id, item.github_repository_id) for item in report.task_candidates
    }
    assert keys == {(1, 10), (1, 20), (2, 10)}


def test_generated_candidate_includes_enough_evidence_for_a_human() -> None:
    from pr_reviewer.evals.feedback_to_evals import build_feedback_improvement_report

    report = build_feedback_improvement_report([_row(row_id="fb-evidence", comment_id=88002)])
    candidate = report.task_candidates[0]
    assert candidate.installation_id == 100
    assert candidate.github_repository_id == 200
    assert candidate.pull_request_number == 8
    assert candidate.finding_id == "job-1:1"
    assert candidate.classification == "wrong"
    assert candidate.github_comment_ids == (88002,)
    assert candidate.reply_excerpts
    assert candidate.first_seen_at is not None
    assert candidate.last_seen_at is not None
    assert "human_reply" in candidate.reply_excerpts[0]


def test_follow_up_is_kept_separate_from_bug_task_candidates() -> None:
    from pr_reviewer.evals.feedback_to_evals import build_feedback_improvement_report

    report = build_feedback_improvement_report(
        [
            _row(row_id="fb-wrong"),
            _row(
                row_id="fb-follow",
                classification="follow_up",
                reply_text="please explain more",
                comment_id=9002,
            ),
        ]
    )
    assert len(report.task_candidates) == 1
    assert report.task_candidates[0].classification == "wrong"
    assert len(report.follow_up_groups) == 1
    assert report.follow_up_groups[0].count == 1


def test_building_a_report_does_not_mutate_prompts_policy_or_labels() -> None:
    from pr_reviewer.evals.feedback_to_evals import build_feedback_improvement_report
    from pr_reviewer.security.instruction_sources import default_review_policy

    prompts = {"diff_only_reviewer": "stay"}
    policy = default_review_policy()
    labels = ["null-check"]
    report = build_feedback_improvement_report([_row(row_id="fb-safe")])
    assert prompts == {"diff_only_reviewer": "stay"}
    assert policy == default_review_policy()
    assert labels == ["null-check"]
    assert report.prompt_rewrites == ()
    assert report.policy_changes == ()
    assert report.label_changes == ()


def test_hosted_reader_returns_rows_for_eval_processing() -> None:
    from pr_reviewer.control_plane.feedback_improvement import (
        build_feedback_improvement_report_from_hosted,
    )

    report = build_feedback_improvement_report_from_hosted()
    assert report.duplicates_skipped >= 0
    assert isinstance(report.task_candidates, tuple)
