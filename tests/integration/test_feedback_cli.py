from __future__ import annotations

from datetime import UTC, datetime


def _report() -> object:
    from pr_reviewer.evals.feedback_to_evals import (
        FeedbackImprovementReport,
        ImprovementTaskCandidate,
        PositiveFeedbackSignal,
    )

    return FeedbackImprovementReport(
        task_candidates=(
            ImprovementTaskCandidate(
                candidate_id="cand-1",
                installation_id=100,
                github_repository_id=200,
                pull_request_number=9,
                finding_id="job-1:1",
                classification="wrong",
                feedback_count=2,
                feedback_ids=("fb-1", "fb-2"),
                github_comment_ids=(9001, 9002),
                reply_excerpts=("this is wrong",),
                first_seen_at=datetime(2026, 9, 10, 1, 0, tzinfo=UTC),
                last_seen_at=datetime(2026, 9, 10, 2, 0, tzinfo=UTC),
            ),
        ),
        positive_signals=(
            PositiveFeedbackSignal(
                installation_id=100,
                github_repository_id=200,
                pull_request_number=9,
                finding_id="job-1:1",
                count=1,
                feedback_ids=("fb-3",),
            ),
        ),
    )


def test_feedback_candidates_cli_prints_human_report(monkeypatch, capsys) -> None:
    from pr_reviewer.cli import feedback

    monkeypatch.setattr(
        feedback,
        "build_feedback_improvement_report_from_hosted",
        _report,
    )

    assert feedback.main(["candidates"]) == 0

    output = capsys.readouterr().out
    assert "# Feedback improvement report" in output
    assert "Task candidates: 1" in output
    assert "cand-1" in output


def test_feedback_candidates_cli_prints_json(monkeypatch, capsys) -> None:
    import json

    from pr_reviewer.cli import feedback

    monkeypatch.setattr(
        feedback,
        "build_feedback_improvement_report_from_hosted",
        _report,
    )

    assert feedback.main(["candidates", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["task_candidates"][0]["candidate_id"] == "cand-1"
    assert payload["prompt_rewrites"] == []
    assert payload["policy_changes"] == []
    assert payload["label_changes"] == []


def test_reviewer_entry_routes_feedback_candidates(monkeypatch) -> None:
    import pr_reviewer.reviewer_entry as entry

    calls: list[list[str]] = []

    def fake_main(args: list[str]) -> int:
        calls.append(args)
        return 0

    import types

    fake_module = types.ModuleType("pr_reviewer.cli.feedback")
    fake_module.main = fake_main  # type: ignore[attr-defined]
    monkeypatch.setitem(__import__("sys").modules, "pr_reviewer.cli.feedback", fake_module)

    assert entry.main(["feedback", "candidates"]) == 0
    assert calls == [["candidates"]]
