"""Role-based model routing chooses a stronger judge than generator by default."""

from __future__ import annotations

from typing import Any


def _request(schema_name: str, *, prompt_name: str = "reviewer") -> Any:
    from pr_reviewer.models.provider import ModelRequest, UntrustedInput

    return ModelRequest(
        model="caller-model-must-be-overridden",
        prompt_name=prompt_name,
        prompt_version="1",
        prompt_content="review safely",
        schema_name=schema_name,
        untrusted_inputs=[UntrustedInput(name="diff", content="+return items[index]")],
        timeout_seconds=5.0,
        max_output_tokens=128,
    )


class CapturingProvider:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def complete_json(self, request: Any) -> Any:
        from pr_reviewer.models.provider import ModelResponse

        self.calls.append(request)
        parsed = (
            {"findings": []}
            if request.schema_name == "ReviewFindingsDraft"
            else {"scores": [{"index": 0, "score": 1.0, "reason": "grounded"}]}
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


def test_role_routing_selects_declared_models_for_all_four_roles() -> None:
    from pr_reviewer.models.routing import RoleModels, RoleRoutedModelProvider

    base = CapturingProvider()
    routed = RoleRoutedModelProvider(
        base,
        role_models=RoleModels(
            triage="triage-model",
            generate="generate-model",
            judge="judge-model",
            explore="explore-model",
        ),
    )

    routed.complete_json(_request("TriageSummary", prompt_name="triage"))
    routed.complete_json(_request("ReviewFindingsDraft"))
    routed.complete_json(_request("FindingReflectionScores"))
    routed.complete_json(_request("ExploreDraft", prompt_name="explore"))

    assert [call.model for call in base.calls] == [
        "triage-model",
        "generate-model",
        "judge-model",
        "explore-model",
    ]


def test_default_role_routing_uses_cheap_generate_and_stronger_judge() -> None:
    from pr_reviewer.models.routing import RoleRoutedModelProvider

    base = CapturingProvider()
    routed = RoleRoutedModelProvider(base)

    triage_response = routed.complete_json(_request("TriageSummary", prompt_name="triage"))
    generate_response = routed.complete_json(_request("ReviewFindingsDraft"))
    judge_response = routed.complete_json(_request("FindingReflectionScores"))
    explore_response = routed.complete_json(_request("ExploreDraft", prompt_name="explore"))

    assert [call.model for call in base.calls] == [
        "gpt-4o-mini",
        "gpt-4o-mini",
        "gpt-4.1",
        "gpt-4o-mini",
    ]
    assert triage_response.model == "gpt-4o-mini"
    assert generate_response.model == "gpt-4o-mini"
    assert judge_response.model == "gpt-4.1"
    assert explore_response.model == "gpt-4o-mini"
    assert judge_response.model != generate_response.model
