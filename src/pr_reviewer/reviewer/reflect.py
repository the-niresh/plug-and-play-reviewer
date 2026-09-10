"""Second-pass scoring for generated review findings."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.contracts.review_context import PackedDiff
from pr_reviewer.models.provider import (
    ModelProvider,
    ModelRequest,
    ModelSchemaMismatch,
    UntrustedInput,
    sum_known_cost_usd,
)
from pr_reviewer.prompts.reflection_schema import reflection_prompt_schema_section

REFLECTION_PROMPT_NAME = "finding_reflection"
REFLECTION_DROP_THRESHOLD = 0.0

_REFLECTION_PROMPT = f"""Score each proposed PR review finding against the packed diff.
{reflection_prompt_schema_section()}
Score 1.0 for a clear, grounded, actionable defect.
Score 0.0 for speculation, weak impact, bad grounding, or non-actionable advice.
Do not add findings. Do not change line numbers.
"""
REFLECTION_PROMPT_VERSION = hashlib.sha256(_REFLECTION_PROMPT.encode("utf-8")).hexdigest()[:16]


def reflection_prompt_text() -> str:
    return _REFLECTION_PROMPT


class ReflectionScore(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    index: int = Field(ge=0)
    score: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)


class ReflectionScores(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    scores: list[ReflectionScore]


class ReflectionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    accepted: tuple[FindingCandidate, ...]
    suppressed: tuple[FindingCandidate, ...]
    cost_usd: float = Field(default=0.0, ge=0)
    cost_is_partial: bool = False
    latency_ms: int = Field(default=0, ge=0)


def reflect_findings(
    *,
    model: ModelProvider,
    model_name: str,
    packed: PackedDiff,
    candidates: tuple[FindingCandidate, ...],
    drop_threshold: float = REFLECTION_DROP_THRESHOLD,
) -> ReflectionResult:
    if not candidates:
        return ReflectionResult(accepted=(), suppressed=(), cost_usd=0.0, latency_ms=0)

    response = model.complete_json(
        ModelRequest(
            model=model_name,
            prompt_name=REFLECTION_PROMPT_NAME,
            prompt_version=REFLECTION_PROMPT_VERSION,
            prompt_content=_REFLECTION_PROMPT,
            schema_name="FindingReflectionScores",
            untrusted_inputs=[
                UntrustedInput(
                    name="candidate_findings",
                    content=json.dumps(
                        [candidate.model_dump() for candidate in candidates],
                        sort_keys=True,
                    ),
                ),
                UntrustedInput(
                    name="packed_diff",
                    content="\n".join(item.content for item in packed.items),
                ),
            ],
            timeout_seconds=60.0,
            max_output_tokens=2048,
        )
    )
    try:
        scores = ReflectionScores.model_validate(response.parsed).scores
    except ValidationError as exc:
        raise ModelSchemaMismatch() from exc
    if {score.index for score in scores} != set(range(len(candidates))):
        raise ModelSchemaMismatch()

    score_by_index = {score.index: score for score in scores}
    accepted: list[FindingCandidate] = []
    suppressed: list[FindingCandidate] = []
    for index, candidate in enumerate(candidates):
        score = score_by_index.get(index)
        if score is None or score.score <= drop_threshold:
            suppressed.append(candidate)
            continue
        accepted.append(
            candidate.model_copy(
                update={
                    "reflection_score": score.score,
                    "reflection_reason": score.reason,
                }
            )
        )

    cost_usd, cost_is_partial = sum_known_cost_usd([response.cost_usd])
    return ReflectionResult(
        accepted=tuple(accepted),
        suppressed=tuple(suppressed),
        cost_usd=cost_usd,
        cost_is_partial=cost_is_partial,
        latency_ms=response.latency_ms,
    )
