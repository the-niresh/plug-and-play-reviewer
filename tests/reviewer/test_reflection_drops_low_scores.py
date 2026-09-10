from __future__ import annotations

from typing import Any

from test_review_pull_request import _draft_dict, _file, _packed, _snapshot


class ReflectingModel:
    def __init__(self, reflection: dict[str, Any]) -> None:
        self.calls: list[Any] = []
        self._reflection = reflection

    def complete_json(self, request: Any) -> Any:
        from pr_reviewer.models.provider import ModelResponse

        self.calls.append(request)
        parsed = (
            {
                "findings": [
                    _draft_dict(title="real issue"),
                    _draft_dict(title="weak issue"),
                ]
            }
            if len(self.calls) == 1
            else self._reflection
        )
        return ModelResponse(
            parsed=parsed,
            output_hash="a" * 64,
            provider_request_id=None,
            provider="openai",
            model=request.model,
            prompt_name=request.prompt_name,
            prompt_version=request.prompt_version,
            input_tokens=1,
            output_tokens=1,
            cost_usd="0",
            latency_ms=1,
        )


def test_reflection_drops_low_scored_findings() -> None:
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    model = ReflectingModel(
        {
            "scores": [
                {"index": 0, "score": 1.0, "reason": "grounded bug"},
                {"index": 1, "score": 0.0, "reason": "not actionable"},
            ]
        }
    )

    outcome = review_pull_request(
        _snapshot([_file("app.py")]),
        _packed([_file("app.py")]),
        [],
        model,
        model_name="gpt-4o-mini",
    )

    assert [item.title for item in outcome.candidates] == ["real issue"]
    assert outcome.candidates[0].reflection_score == 1.0
    assert outcome.candidates[0].reflection_reason == "grounded bug"
    assert [item.title for item in outcome.suppressed_candidates] == ["weak issue"]


def test_provider_accepts_the_reflection_schema_name() -> None:
    from pr_reviewer.models.provider import ModelRequest, UntrustedInput, finish_completion

    request = ModelRequest(
        model="gpt-4o-mini",
        prompt_name="finding_reflection",
        prompt_version="reflection-v1",
        prompt_content="score findings",
        schema_name="FindingReflectionScores",
        untrusted_inputs=[UntrustedInput(name="candidate_findings", content="[]")],
        timeout_seconds=1,
        max_output_tokens=10,
    )

    response = finish_completion(
        vendor="openai",
        request=request,
        content='{"scores":[{"index":0,"score":1.0,"reason":"grounded"}]}',
        input_tokens=1,
        output_tokens=1,
        provider_request_id=None,
        latency_ms=1,
    )

    assert response.parsed["scores"][0]["reason"] == "grounded"
