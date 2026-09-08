"""Task 35.B6: multi-model agreement ranking for generate-stage findings."""

from __future__ import annotations


def _candidate(*, title: str, rationale: str, confidence: float, line: int = 10):
    from pr_reviewer.contracts.finding_candidate import FindingCandidate

    return FindingCandidate(
        concern="correctness",
        severity="high",
        category="null-check",
        file_path="app.py",
        line_start=line,
        line_end=line,
        title=title,
        rationale=rationale,
        evidence=[f"app.py:{line}"],
        confidence=confidence,
    )


def test_two_models_agreeing_outranks_single_model_finding() -> None:
    from pr_reviewer.reviewer.consensus import rank_findings_by_agreement

    ranked = rank_findings_by_agreement(
        {
            "gpt-4o-mini": (
                _candidate(
                    title="shared finding",
                    rationale="first model says missing null check on the changed line",
                    confidence=0.7,
                ),
                _candidate(
                    title="single finding",
                    rationale="only one model reports this",
                    confidence=0.9,
                    line=20,
                ),
            ),
            "gpt-4.1-mini": (
                _candidate(
                    title="shared finding",
                    rationale="second model independently confirms the same issue",
                    confidence=0.6,
                ),
            ),
            "claude-3-5-haiku-latest": (),
        }
    )

    assert [item.title for item in ranked] == ["shared finding", "single finding"]
    assert ranked[0].agreement_count == 2
    assert ranked[1].agreement_count == 1
    assert [item.model for item in ranked[0].model_reasoning] == [
        "gpt-4o-mini",
        "gpt-4.1-mini",
    ]
    assert [item.rationale for item in ranked[0].model_reasoning] == [
        "first model says missing null check on the changed line",
        "second model independently confirms the same issue",
    ]
