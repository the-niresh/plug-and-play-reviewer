"""Deterministic reviewers for evals. Flaky is seeded so variation is repeatable."""

from __future__ import annotations

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.evals.types import EvalCase, EvalReviewResult


def _candidate_for(
    case: EvalCase, *, file_path: str | None = None, title: str | None = None
) -> FindingCandidate:
    label = case.expected_labels[0]
    return FindingCandidate(
        concern=label.concern,
        severity="high",
        category=label.category,
        file_path=file_path or label.file_path,
        line_start=label.line_start,
        line_end=label.line_end,
        title=title or "Missing null check",
        rationale="widget.value can be None.",
        evidence=[f"{label.file_path}:{label.line_start}"],
        confidence=0.8,
    )


class FixtureReviewer:
    def __init__(self, mode: str, *, seed: int = 0, cost_usd: float = 0.0) -> None:
        self._mode = mode
        self._step = seed
        self._cost_usd = cost_usd

    @classmethod
    def perfect(cls) -> FixtureReviewer:
        return cls("perfect")

    @classmethod
    def silent(cls) -> FixtureReviewer:
        return cls("silent")

    @classmethod
    def noisy(cls) -> FixtureReviewer:
        return cls("noisy")

    @classmethod
    def flaky(cls, seed: int = 1) -> FixtureReviewer:
        return cls("flaky", seed=seed)

    @classmethod
    def with_cost(cls, cost_usd: float, mode: str = "silent") -> FixtureReviewer:
        return cls(mode, cost_usd=cost_usd)

    def __call__(self, case: EvalCase) -> EvalReviewResult | list[FindingCandidate]:
        mode = self._mode
        if mode == "flaky":
            cycle = self._step % 4
            self._step += 1
            if cycle == 0:
                mode = "perfect"
            elif cycle == 1:
                mode = "silent"
            elif cycle == 2:
                mode = "noisy"
            else:
                mode = "perfect"
        if mode == "silent":
            findings: list[FindingCandidate] = []
        elif mode == "noisy":
            matched = _candidate_for(case)
            extra = _candidate_for(
                case,
                file_path="src/other.py",
                title="unrelated style nit",
            )
            findings = [matched, extra]
        else:
            findings = [_candidate_for(case)]
        if self._cost_usd > 0:
            return EvalReviewResult(findings=tuple(findings), cost_usd=self._cost_usd)
        return findings
