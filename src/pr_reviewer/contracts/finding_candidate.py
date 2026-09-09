"""Model-emitted finding shape. System code owns id, verification, and status."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Concern = Literal["security", "correctness", "tests", "docs", "maintainability"]
Severity = Literal["critical", "high", "medium", "low", "info"]


class FindingDraft(BaseModel):
    """Restricted model output. System-owned fields are absent, not stripped."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    concern: Concern
    severity: Severity
    category: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    line_start: int = Field(gt=0)
    line_end: int = Field(gt=0)
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    suggested_fix: str | None = None
    reflection_score: float | None = Field(default=None, ge=0, le=1)
    reflection_reason: str | None = Field(default=None, min_length=1)

    @field_validator("suggested_fix", mode="before")
    @classmethod
    def blank_suggested_fix_is_none(cls, value: object) -> object:
        return _blank_suggested_fix_is_none(value)

    @model_validator(mode="after")
    def validate_line_range(self) -> FindingDraft:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class FindingCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    concern: Concern
    severity: Severity
    category: str = Field(min_length=1)
    file_path: str = Field(min_length=1)
    line_start: int = Field(gt=0)
    line_end: int = Field(gt=0)
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    suggested_fix: str | None = None

    @field_validator("suggested_fix", mode="before")
    @classmethod
    def blank_suggested_fix_is_none(cls, value: object) -> object:
        return _blank_suggested_fix_is_none(value)

    @model_validator(mode="after")
    def validate_line_range(self) -> FindingCandidate:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return self


class ModelReasoning(BaseModel):
    """One model's rationale. Never merged with another model's voice."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class ConsensusFinding(FindingCandidate):
    """Generate-stage finding with cross-model agreement metadata."""

    agreement_count: int = Field(ge=1)
    model_reasoning: tuple[ModelReasoning, ...] = Field(min_length=1)
    needs_human_match: bool = False


def _blank_suggested_fix_is_none(value: object) -> object:
    if isinstance(value, str) and not value.strip():
        return None
    return value


_SECURITY_TEXT_MARKERS = (
    "prototype pollution",
    "prototype-pollution",
    "__proto__",
    "signing key",
)


def _concern_for_draft(draft: FindingDraft) -> Concern:
    text = " ".join((draft.category, draft.title, draft.rationale, *draft.evidence)).lower()
    if any(marker in text for marker in _SECURITY_TEXT_MARKERS):
        return "security"
    return draft.concern


def candidate_from_draft(draft: FindingDraft) -> FindingCandidate:
    return FindingCandidate(
        concern=_concern_for_draft(draft),
        severity=draft.severity,
        category=draft.category,
        file_path=draft.file_path,
        line_start=draft.line_start,
        line_end=draft.line_end,
        title=draft.title,
        rationale=draft.rationale,
        evidence=list(draft.evidence),
        confidence=draft.confidence,
        suggested_fix=draft.suggested_fix,
    )
