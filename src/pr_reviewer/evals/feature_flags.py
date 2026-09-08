"""Phase 31: the feature-flag table. retrieval, code graph, specialists, and LangGraph, each
with the real measurement that decided it, or the verbatim BaselineBlocked refusal when nothing
has been measured yet. Never a placeholder, and never a flag reported enabled without a
corresponding on-switch it actually reads.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.evals.run_eval import (
    BaselineBlocked,
    load_public_eval_cases,
    run_context_source_comparison,
    run_diff_only_baseline,
    run_retrieval_comparison,
    run_specialist_comparison,
)
from pr_reviewer.evals.types import EvalCase
from pr_reviewer.security.instruction_sources import ReviewPolicy

DEFAULT_FEATURE_FLAGS_PATH = (
    Path(__file__).resolve().parents[3] / "docs" / "reports" / "feature_flags.json"
)


class FeatureFlag(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    enabled: bool
    measurement: str



def _holdout_cases(cases: Sequence[EvalCase]) -> list[EvalCase]:
    return [case for case in cases if case.split == "holdout"]


def _blocked_refusal(run_comparison: object, *args: object) -> str:
    try:
        run_comparison(*args)  # type: ignore[operator]
    except BaselineBlocked as exc:
        return str(exc)
    raise AssertionError("expected BaselineBlocked for an empty holdout")


def _pending_comparison_message(name: str) -> str:
    return (
        f"holdout ready; {name} comparison not run without configured reviewers"
    )


def _unreachable_reviewer(_case: EvalCase) -> Sequence[FindingCandidate]:
    # Every comparison below checks the holdout before ever calling a reviewer, so this is never
    # invoked while the holdout is empty. It exists only to satisfy the ReviewerCallable shape.
    raise AssertionError("reviewer called despite an empty holdout")


def _retrieval_measurement(cases: Sequence[EvalCase]) -> str:
    if not _holdout_cases(cases):
        return _blocked_refusal(
            run_retrieval_comparison,
            cases,
            _unreachable_reviewer,
            _unreachable_reviewer,
        )
    return _pending_comparison_message("retrieval")


def _code_graph_measurement(cases: Sequence[EvalCase]) -> str:
    if not _holdout_cases(cases):
        return _blocked_refusal(
            run_context_source_comparison,
            cases,
            _unreachable_reviewer,
            _unreachable_reviewer,
            _unreachable_reviewer,
        )
    return _pending_comparison_message("context-source")


def _specialists_measurement(cases: Sequence[EvalCase]) -> str:
    if not _holdout_cases(cases):
        return _blocked_refusal(
            run_specialist_comparison,
            cases,
            _unreachable_reviewer,
            _unreachable_reviewer,
        )
    return _pending_comparison_message("specialist")


def _langgraph_measurement(cases: Sequence[EvalCase]) -> str:
    if not _holdout_cases(cases):
        return _blocked_refusal(run_diff_only_baseline, cases, _unreachable_reviewer)
    return _pending_comparison_message("langgraph")


def generate_feature_flags(cases: Sequence[EvalCase] | None = None) -> list[FeatureFlag]:
    source_cases = list(cases) if cases is not None else load_public_eval_cases()
    policy = ReviewPolicy()

    return [
        FeatureFlag(
            name="retrieval",
            enabled=False,  # No ReviewPolicy field reads it into the default review path yet.
            measurement=_retrieval_measurement(source_cases),
        ),
        FeatureFlag(
            name="code_graph",
            enabled=False,  # Same: retrieval/code_graph.py exists but nothing wires it in yet.
            measurement=_code_graph_measurement(source_cases),
        ),
        FeatureFlag(
            name="specialists",
            enabled=policy.specialist_mode,
            measurement=_specialists_measurement(source_cases),
        ),
        FeatureFlag(
            name="langgraph",
            enabled=False,  # workflow/langgraph_engine.py exists, off by default (Phase 12).
            measurement=_langgraph_measurement(source_cases),
        ),
    ]


def write_feature_flags(path: Path = DEFAULT_FEATURE_FLAGS_PATH) -> list[FeatureFlag]:
    flags = generate_feature_flags()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [flag.model_dump() for flag in flags]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return flags


def main() -> int:
    write_feature_flags()
    print(f"Wrote {DEFAULT_FEATURE_FLAGS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
