from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Concern = Literal["security", "correctness", "tests", "docs", "maintainability"]
Severity = Literal["critical", "high", "medium", "low", "info"]
VerificationMethod = Literal["sandbox", "static", "not_applicable", "failed"]
FindingStatus = Literal["draft", "queued_for_human", "posted", "rejected", "disputed"]


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    review_job_id: str = Field(min_length=1)
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
    verified: bool
    verification_method: VerificationMethod
    public_safe: bool
    status: FindingStatus
    suggested_fix: str | None = None

    @field_validator("suggested_fix", mode="before")
    @classmethod
    def blank_suggested_fix_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_line_range(self) -> Finding:
        if self.line_end < self.line_start:
            raise ValueError("line_end must be greater than or equal to line_start")
        return self
