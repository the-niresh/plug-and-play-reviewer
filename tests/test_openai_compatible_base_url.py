"""An OpenAI-compatible adapter can target unknown providers by configuration."""

from __future__ import annotations

import json

import httpx
import pytest


def test_openai_compatible_provider_uses_configured_base_url_for_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pr_reviewer.models.openai_compatible import (
        OpenAICompatibleProvider,
        OpenAICompatibleProviderConfig,
    )
    from pr_reviewer.models.provider import ModelRequest, UntrustedInput

    provider_id = "totally-unknown-gateway"
    api_key = "sk-test-unknown-provider"
    captured: list[httpx.Request] = []
    constructed_base_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-config-only",
                "usage": {"prompt_tokens": 11, "completion_tokens": 7},
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "concern": "correctness",
                                    "severity": "low",
                                    "category": "logic",
                                    "file_path": "app.py",
                                    "line_start": 4,
                                    "line_end": 4,
                                    "title": "unknown provider still works",
                                    "rationale": "adapter only needs OpenAI-compatible wire format",
                                    "evidence": ["return items[index]"],
                                    "confidence": 0.6,
                                }
                            )
                        }
                    }
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    base_url = "https://fake-gateway.local"
    real_client = httpx.Client

    def build_client(*args: object, **kwargs: object) -> httpx.Client:
        configured_base_url = str(kwargs["base_url"])
        constructed_base_urls.append(configured_base_url)
        return real_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "Client", build_client)
    provider = OpenAICompatibleProvider(
        config=OpenAICompatibleProviderConfig(
            provider_id=provider_id,
            base_url=base_url,
        ),
        api_key=api_key,
    )
    request = ModelRequest(
        model="gpt-4o-mini",
        prompt_name="reviewer",
        prompt_version="1",
        prompt_content="review safely",
        schema_name="FindingCandidate",
        untrusted_inputs=[UntrustedInput(name="diff", content="+return items[index]")],
        timeout_seconds=5.0,
        max_output_tokens=128,
    )

    response = provider.complete_json(request)

    assert response.provider == "openai"
    assert response.model == "gpt-4o-mini"
    assert response.prompt_name == "reviewer"
    assert response.prompt_version == "1"
    assert response.parsed["title"] == "unknown provider still works"
    assert len(response.output_hash) == 64
    assert constructed_base_urls == [base_url]
    assert captured
    sent = captured[0]
    assert str(sent.url) == "https://fake-gateway.local/v1/chat/completions"
    assert sent.headers["authorization"] == f"Bearer {api_key}"
