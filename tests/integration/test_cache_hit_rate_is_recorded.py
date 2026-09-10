"""Prompt-cache hit rate is measured from provider usage payloads."""

from __future__ import annotations

import json

import httpx


def test_openai_compatible_records_prompt_cache_hit_rate_from_response() -> None:
    from pr_reviewer.models.openai_compatible import (
        OpenAICompatibleProvider,
        OpenAICompatibleProviderConfig,
    )
    from pr_reviewer.models.provider import (
        ModelRequest,
        UntrustedInput,
        model_call_ledger_fields,
    )

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-cache-1",
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 120,
                    "prompt_tokens_details": {"cached_tokens": 750},
                },
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
                                    "title": "cached response parses",
                                    "rationale": "usage reports a cached read",
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
    client = httpx.Client(transport=transport, base_url="https://cache-aware.local")
    provider = OpenAICompatibleProvider(
        config=OpenAICompatibleProviderConfig(
            provider_id="totally-unknown-gateway",
            base_url="https://cache-aware.local",
            cache_request_overrides={"cache_control": {"type": "ephemeral"}},
        ),
        api_key="sk-test-cache",
        http=client,
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
    ledger = model_call_ledger_fields(response)

    assert captured, "provider must call an OpenAI-compatible endpoint"
    body = json.loads(captured[0].content.decode("utf-8"))
    assert body["cache_control"] == {"type": "ephemeral"}
    assert response.prompt_cache_hit_rate == 0.75
    assert ledger["prompt_cache_hit_rate"] == 0.75
