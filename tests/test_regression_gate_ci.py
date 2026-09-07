"""The CI-facing regression gate wrapper (Task 35.F3).

Today the public holdout is empty. run_diff_only_baseline raises BaselineBlocked by
design; the wrapper must turn that into a clear, visible skip, never a silent pass and
never a fake green number. Once a holdout and a frozen baseline report exist, the same
wrapper must fail the build on a real regression, proven end to end through the actual
match/metrics pipeline, not just by asserting on a hand-built GateResult.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest


def _holdout_case(case_id: str = "case-1") -> dict[str, object]:
    return {
        "id": case_id,
        "split": "holdout",
        "diff": "@@ -1 +1 @@\n+value = widget.value\n",
        "expected_labels": [
            {
                "concern": "correctness",
                "category": "null-check",
                "file_path": "src/widget.py",
                "line_start": 10,
                "line_end": 12,
            }
        ],
        "source_evidence": ["fix null check"],
        "human_auditor": "niresh",
        "committed_at": date(2026, 1, 1).isoformat(),
    }


def _dev_case(case_id: str = "case-dev") -> dict[str, object]:
    row = _holdout_case(case_id)
    row["split"] = "dev"
    return row


def _write_cases(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _good_baseline_report(path: Path) -> None:
    from pr_reviewer.evals.types import EvalRun

    run = EvalRun.model_validate(
        {
            "metrics": {
                "precision_per_finding": 0.9,
                "precision_per_case": 0.9,
                "recall_per_finding": 0.9,
                "recall_per_case": 0.9,
                "false_findings_per_pr": 0.0,
                "selectivity": 0.5,
                "verified_finding_rate": 0.0,
                "latency_ms": 100,
                "cost_usd": 0.01,
                "needs_human_rate": 0.0,
                "reviewed_pr_count": 3,
                "useful_finding_count": 3,
                "rule_adherence": {
                    "retrieval_only": 0.0,
                    "executable_check_only": 0.0,
                    "both": 0.0,
                },
            }
        }
    )
    path.write_text(run.model_dump_json(), encoding="utf-8")


def _thresholds() -> object:
    from pr_reviewer.evals.regression_gate import EvalThresholds

    return EvalThresholds(
        min_precision_per_finding=0.5,
        max_false_findings_per_pr=1.0,
        min_high_value_recall=0.5,
        max_cost_usd=1.0,
        max_latency_ms=5000,
    )


def test_gate_skips_with_a_clear_reason_when_holdout_is_empty(tmp_path: Path) -> None:
    from pr_reviewer.evals.regression_gate import run_diff_only_gate
    from pr_reviewer.evals.types import EvalCase

    cases = [EvalCase.model_validate(_dev_case())]

    def _boom(_case: EvalCase) -> list[object]:
        raise AssertionError("reviewer must not be called while the holdout is empty")

    outcome = run_diff_only_gate(
        cases, _boom, tmp_path / "baseline.json", _thresholds()
    )
    assert outcome.skipped is True
    assert outcome.result is None
    assert "holdout" in (outcome.reason or "")


def test_gate_raises_when_holdout_has_cases_but_baseline_report_is_missing(
    tmp_path: Path,
) -> None:
    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.regression_gate import BaselineReportMissing, run_diff_only_gate
    from pr_reviewer.evals.types import EvalCase

    cases = [EvalCase.model_validate(_holdout_case())]
    with pytest.raises(BaselineReportMissing):
        run_diff_only_gate(
            cases,
            FixtureReviewer.perfect(),
            tmp_path / "does-not-exist.json",
            _thresholds(),
        )


def test_gate_fails_a_real_regression_end_to_end(tmp_path: Path) -> None:
    """A reviewer that finds nothing must trip precision and recall, proven through
    the real match/metrics pipeline, not a hand-built GateResult."""
    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.regression_gate import run_diff_only_gate
    from pr_reviewer.evals.types import EvalCase

    cases = [EvalCase.model_validate(_holdout_case())]
    baseline_report = tmp_path / "baseline.json"
    _good_baseline_report(baseline_report)

    outcome = run_diff_only_gate(
        cases, FixtureReviewer.silent(), baseline_report, _thresholds(), repeats=1
    )

    assert outcome.skipped is False
    assert outcome.result is not None
    assert outcome.result.passed is False
    assert "precision_per_finding" in outcome.result.blocked_metrics
    assert "high_value_recall" in outcome.result.blocked_metrics


def test_gate_passes_when_candidate_meets_baseline_and_thresholds(tmp_path: Path) -> None:
    from pr_reviewer.evals.fixture_reviewer import FixtureReviewer
    from pr_reviewer.evals.regression_gate import run_diff_only_gate
    from pr_reviewer.evals.types import EvalCase

    cases = [EvalCase.model_validate(_holdout_case())]
    baseline_report = tmp_path / "baseline.json"
    _good_baseline_report(baseline_report)

    outcome = run_diff_only_gate(
        cases, FixtureReviewer.perfect(), baseline_report, _thresholds(), repeats=1
    )

    assert outcome.skipped is False
    assert outcome.result is not None
    assert outcome.result.passed is True


def test_cli_exits_zero_with_a_visible_skip_reason(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from pr_reviewer.evals.regression_gate import main

    cases_path = tmp_path / "cases.jsonl"
    _write_cases(cases_path, [_dev_case()])

    code = main(
        [
            "--cases",
            str(cases_path),
            "--baseline-report",
            str(tmp_path / "missing-baseline.json"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "SKIP" in captured.out
    assert "holdout" in captured.out


def test_cli_fails_the_build_when_the_gate_reports_a_regression(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import pr_reviewer.evals.regression_gate as regression_gate_module
    from pr_reviewer.evals.regression_gate import GateOutcome, GateResult

    cases_path = tmp_path / "cases.jsonl"
    _write_cases(cases_path, [_holdout_case()])

    def _fake_gate(*_args: object, **_kwargs: object) -> GateOutcome:
        return GateOutcome(
            skipped=False,
            reason=None,
            result=GateResult(passed=False, blocked_metrics=("precision_per_finding",)),
        )

    monkeypatch.setattr(regression_gate_module, "run_diff_only_gate", _fake_gate)

    code = regression_gate_module.main(["--cases", str(cases_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "REGRESSION" in captured.out
    assert "precision_per_finding" in captured.out


def test_cli_exits_zero_when_the_gate_reports_a_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import pr_reviewer.evals.regression_gate as regression_gate_module
    from pr_reviewer.evals.regression_gate import GateOutcome, GateResult

    cases_path = tmp_path / "cases.jsonl"
    _write_cases(cases_path, [_holdout_case()])

    def _fake_gate(*_args: object, **_kwargs: object) -> GateOutcome:
        return GateOutcome(
            skipped=False, reason=None, result=GateResult(passed=True, blocked_metrics=())
        )

    monkeypatch.setattr(regression_gate_module, "run_diff_only_gate", _fake_gate)

    code = regression_gate_module.main(["--cases", str(cases_path)])
    captured = capsys.readouterr()
    assert code == 0
    assert "PASS" in captured.out


def test_cli_fails_loudly_when_baseline_report_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    import pr_reviewer.evals.regression_gate as regression_gate_module
    from pr_reviewer.evals.regression_gate import BaselineReportMissing

    cases_path = tmp_path / "cases.jsonl"
    _write_cases(cases_path, [_holdout_case()])

    def _fake_gate(*_args: object, **_kwargs: object) -> object:
        raise BaselineReportMissing("holdout has cases but no baseline report exists")

    monkeypatch.setattr(regression_gate_module, "run_diff_only_gate", _fake_gate)

    code = regression_gate_module.main(["--cases", str(cases_path)])
    captured = capsys.readouterr()
    assert code == 1
    assert "ERROR" in captured.out
