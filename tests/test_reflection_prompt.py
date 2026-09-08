"""Reflection prompt must describe ReflectionScore and the exactly-once index rule."""

from __future__ import annotations

import json

import pytest
from test_review_pull_request import _draft_dict, _file, _packed, _snapshot


def test_reflection_prompt_names_index_score_reason_and_exactly_once_rule() -> None:
    from pr_reviewer.reviewer.reflect import reflection_prompt_text

    prompt = reflection_prompt_text().lower()
    for field_name in ("index", "score", "reason"):
        assert field_name in prompt
    assert "0-based" in prompt or "0 based" in prompt
    assert "exactly once" in prompt
    assert "repeated or omitted" in prompt
    assert "0 to 1" in reflection_prompt_text()


def test_reflection_scores_rejects_bare_numbers_at_provider_boundary() -> None:
    from pr_reviewer.models.provider import (
        ModelRequest,
        ModelSchemaMismatch,
        UntrustedInput,
        finish_completion,
    )

    request = ModelRequest(
        model="gpt-4o-mini",
        prompt_name="finding_reflection",
        prompt_version="1",
        prompt_content="score findings",
        schema_name="FindingReflectionScores",
        untrusted_inputs=[UntrustedInput(name="candidate_findings", content="[]")],
        timeout_seconds=5.0,
        max_output_tokens=512,
    )
    with pytest.raises(ModelSchemaMismatch):
        finish_completion(
            vendor="openai",
            request=request,
            content=json.dumps({"scores": [1.0, 1.0, 1.0, 1.0]}),
            input_tokens=1,
            output_tokens=1,
            provider_request_id=None,
            latency_ms=1,
        )


def test_reflection_accepts_one_object_per_finding_end_to_end() -> None:
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    class TwoFindingReflectingModel:
        def __init__(self) -> None:
            self.calls: list[object] = []

        def complete_json(self, request: object) -> object:
            from pr_reviewer.models.provider import ModelResponse

            self.calls.append(request)
            parsed = (
                {
                    "findings": [
                        _draft_dict(title="first"),
                        _draft_dict(title="second"),
                    ]
                }
                if len(self.calls) == 1
                else {
                    "scores": [
                        {"index": 0, "score": 1.0, "reason": "grounded"},
                        {"index": 1, "score": 0.0, "reason": "weak"},
                    ]
                }
            )
            return ModelResponse(
                parsed=parsed,
                output_hash="a" * 64,
                provider_request_id=None,
                provider="openai",
                model=getattr(request, "model", "gpt-4o-mini"),
                prompt_name=getattr(request, "prompt_name", ""),
                prompt_version=getattr(request, "prompt_version", ""),
                input_tokens=1,
                output_tokens=1,
                cost_usd="0",
                latency_ms=1,
            )

    outcome = review_pull_request(
        _snapshot([_file("app.py")]),
        _packed([_file("app.py")]),
        [],
        TwoFindingReflectingModel(),
        model_name="gpt-4o-mini",
    )
    assert [item.title for item in outcome.candidates] == ["first"]
    assert outcome.candidates[0].reflection_reason == "grounded"
