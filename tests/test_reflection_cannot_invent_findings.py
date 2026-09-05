from __future__ import annotations

from typing import Any

import pytest
from test_review_pull_request import _draft_dict, _file, _packed, _snapshot


class SingleFindingReflectingModel:
    def __init__(self, reflection: dict[str, Any]) -> None:
        self.calls: list[Any] = []
        self._reflection = reflection

    def complete_json(self, request: Any) -> Any:
        from pr_reviewer.models.provider import ModelResponse

        self.calls.append(request)
        parsed = (
            {"findings": [_draft_dict(title="only input")]}
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


def test_reflection_cannot_create_a_finding_from_an_unknown_index() -> None:
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    model = SingleFindingReflectingModel(
        {"scores": [{"index": 99, "score": 1.0, "reason": "looks real"}]}
    )

    outcome = review_pull_request(
        _snapshot([_file("app.py")]),
        _packed([_file("app.py")]),
        [],
        model,
        model_name="gpt-4o-mini",
    )

    assert outcome.candidates == ()
    assert [item.title for item in outcome.suppressed_candidates] == ["only input"]


def test_reflection_length_mismatch_is_loud() -> None:
    from pr_reviewer.models.provider import ModelSchemaMismatch
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    model = SingleFindingReflectingModel({"scores": []})

    with pytest.raises(ModelSchemaMismatch):
        review_pull_request(
            _snapshot([_file("app.py")]),
            _packed([_file("app.py")]),
            [],
            model,
            model_name="gpt-4o-mini",
        )
