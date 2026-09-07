"""CLI-backed model provider for subscription-funded usage."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from pr_reviewer.models.provider import (
    ModelContextLimit,
    ModelKeyInvalid,
    ModelProviderFailure,
    ModelRateLimit,
    ModelRequest,
    ModelResponse,
    ModelTimeout,
    ModelVendor,
    finish_completion,
    render_untrusted_user_message,
)


@dataclass(frozen=True)
class CliSubscriptionProviderConfig:
    executable: str
    argv: tuple[str, ...]
    vendor: ModelVendor = "openai"


def _error_payload(stderr: str) -> dict[str, Any]:
    try:
        parsed = json.loads(stderr)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _raise_for_cli_error(stderr: str) -> None:
    payload = _error_payload(stderr)
    kind = str(payload.get("error_kind", payload.get("kind", ""))).lower()
    message = str(payload.get("message", stderr)).lower()
    if kind in {"rate_limit", "retryable_rate_limit"} or "rate limit" in message:
        raise ModelRateLimit()
    if kind in {"context_limit", "context_length_exceeded"} or "too long" in message:
        raise ModelContextLimit()
    if kind in {"bad_key", "invalid_api_key"}:
        raise ModelKeyInvalid()
    raise ModelProviderFailure()


def _request_payload(request: ModelRequest) -> dict[str, Any]:
    return {
        "model": request.model,
        "prompt_name": request.prompt_name,
        "prompt_version": request.prompt_version,
        "schema_name": request.schema_name,
        "prompt_content": request.prompt_content,
        "user_content": render_untrusted_user_message(request),
        "max_output_tokens": request.max_output_tokens,
    }


class CliSubscriptionProvider:
    def __init__(self, config: CliSubscriptionProviderConfig) -> None:
        self._config = config

    def complete_json(self, request: ModelRequest) -> ModelResponse:
        argv = [self._config.executable, *self._config.argv]
        try:
            completed = subprocess.run(
                argv,
                input=json.dumps(_request_payload(request)),
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelTimeout() from exc
        except OSError as exc:
            raise ModelProviderFailure() from exc

        if completed.returncode != 0:
            _raise_for_cli_error(completed.stderr)

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ModelProviderFailure() from exc
        if not isinstance(payload, dict):
            raise ModelProviderFailure()

        raw_content = payload.get("content")
        if isinstance(raw_content, str):
            content = raw_content
        elif isinstance(raw_content, dict):
            content = json.dumps(raw_content)
        else:
            raise ModelProviderFailure()
        try:
            input_tokens = int(payload.get("input_tokens", 0))
            output_tokens = int(payload.get("output_tokens", 0))
            if input_tokens < 0 or output_tokens < 0:
                raise ValueError("token counts must be non-negative")
            request_id = payload.get("provider_request_id")
            provider_request_id = str(request_id) if request_id is not None else None
        except (TypeError, ValueError) as exc:
            raise ModelProviderFailure() from exc

        return finish_completion(
            vendor=self._config.vendor,
            request=request,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_request_id=provider_request_id,
            latency_ms=0,
        )
