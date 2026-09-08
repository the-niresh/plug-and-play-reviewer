"""Shared eval holdout fixtures for tests.

Synthetic dev-only cases keep the refusal guards honest.
"""

from __future__ import annotations

from datetime import date

from pr_reviewer.evals.types import EvalCase, EvalLabel


def dev_only_cases() -> list[EvalCase]:
    """One dev case and zero holdout rows for BaselineBlocked tests."""
    return [
        EvalCase(
            id="dev-only-1",
            split="dev",
            diff="@@ -1 +1 @@\n-old\n+new\n",
            expected_labels=[
                EvalLabel(
                    concern="correctness",
                    category="null-check",
                    file_path="src/widget.py",
                    line_start=1,
                    line_end=1,
                )
            ],
            source_evidence=["dev fixture"],
            human_auditor=None,
            committed_at=date(2026, 1, 1),
            repository="pallets/flask",
            sha="d7b6c1f6703df405c69da45e7e0ba3d1aed512ce",
        )
    ]


def single_holdout_case() -> EvalCase:
    return EvalCase(
        id="holdout-1",
        split="holdout",
        diff="@@ -1 +1 @@\n+value = widget.value\n",
        expected_labels=[
            EvalLabel(
                concern="correctness",
                category="null-check",
                file_path="src/widget.py",
                line_start=10,
                line_end=12,
            )
        ],
        source_evidence=["fix null check"],
        human_auditor="niresh",
        committed_at=date(2024, 6, 1),
        repository="pallets/flask",
        sha="d7b6c1f6703df405c69da45e7e0ba3d1aed512ce",
    )
