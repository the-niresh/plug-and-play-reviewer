"""OpenAI-compatible adapter with a configurable base URL."""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from pr_reviewer.models.provider import (
    ModelProviderFailure,
    ModelRequest,
    ModelResponse,
    ModelTimeout,
    ModelVendor,
    finish_completion,
    raise_for_provider_status,
    render_untrusted_user_message,
)


@dataclass(frozen=True)
class OpenAICompatibleProviderConfig:
    provider_id: str
    base_url: str


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"authorization": f"Bearer {api_key}"}


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        config: OpenAICompatibleProviderConfig,
        api_key: str,
        http: httpx.Client | None = None,
        ledger_vendor: ModelVendor = "openai",
    ) -> None:
        self._config = config
        self._api_key = api_key
        self._vendor = ledger_vendor
        self._http = http if http is not None else httpx.Client(base_url=config.base_url)

    @property
    def provider_id(self) -> str:
        return self._config.provider_id

    def complete_json(self, request: ModelRequest) -> ModelResponse:
        started = time.perf_counter()
        body = {
            "model": request.model,
            "max_tokens": request.max_output_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": request.prompt_content},
                {"role": "user", "content": render_untrusted_user_message(request)},
            ],
        }
        try:
            response = self._http.post(
                "/v1/chat/completions",
                json=body,
                headers=_auth_headers(self._api_key),
                timeout=request.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise ModelTimeout() from exc
        latency_ms = max(0, int((time.perf_counter() - started) * 1000))
        raise_for_provider_status(response)
        payload = response.json()
        try:
            content = str(payload["choices"][0]["message"]["content"])
            usage = payload.get("usage") or {}
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
            request_id = payload.get("id")
            provider_request_id = str(request_id) if request_id is not None else None
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelProviderFailure() from exc
        return finish_completion(
            vendor=self._vendor,
            request=request,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_request_id=provider_request_id,
            latency_ms=latency_ms,
        )
