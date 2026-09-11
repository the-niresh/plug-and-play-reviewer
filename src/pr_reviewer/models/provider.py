"""Runner-side model adapter interface. Holds no hosted database handle.

The hosted ledger type for openai|anthropic is ModelProviderName in events/record_model_call.py.
This module's ModelProvider is the adapter Protocol. They are different types.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from decimal import Decimal
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pr_reviewer.contracts.finding_candidate import FindingCandidate, FindingDraft
from pr_reviewer.models.providers import provider_auth_headers
from pr_reviewer.security.prompt_boundaries import UntrustedText, wrap_untrusted

ModelVendor = Literal["openai", "anthropic"]

# USD per million tokens (input, output). Unpriced models record tokens with cost_usd=None.
_PRICE_PER_MILLION: dict[tuple[str, str], tuple[Decimal, Decimal]] = {
    ("openai", "gpt-4o-mini"): (Decimal("0.15"), Decimal("0.60")),
    ("openai", "gpt-4o"): (Decimal("2.50"), Decimal("10.00")),
    ("openai", "gpt-4.1-mini"): (Decimal("0.40"), Decimal("1.60")),
    ("openai", "gpt-4.1"): (Decimal("2.00"), Decimal("8.00")),
    ("openai", "o3-mini"): (Decimal("1.10"), Decimal("4.40")),
    ("anthropic", "claude-3-5-haiku-latest"): (Decimal("0.80"), Decimal("4.00")),
    ("anthropic", "claude-3-5-sonnet-latest"): (Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-3-7-sonnet-latest"): (Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-sonnet-4-20250514"): (Decimal("3.00"), Decimal("15.00")),
    ("anthropic", "claude-haiku-4-5-20251001"): (Decimal("1.00"), Decimal("5.00")),
}


class ModelTimeout(Exception):
    """The provider did not answer before ModelRequest.timeout_seconds."""


class InvalidModelJson(Exception):
    """The provider returned a body that is not JSON."""


class ModelSchemaMismatch(Exception):
    """The provider JSON did not match the requested schema."""


class ModelContextLimit(Exception):
    """The prompt exceeded the model's context window."""


class ModelRateLimit(Exception):
    """The provider rejected the call as rate limited."""


class ModelProviderFailure(Exception):
    """Any other provider HTTP or protocol failure."""

    def __init__(self, message: str = "", *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ModelKeyInvalid(Exception):
    """The provider rejected the API key before any review ran."""


class UntrustedInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    content: str


class ModelRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: str = Field(min_length=1)
    prompt_name: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_content: str = Field(min_length=1)
    schema_name: str = Field(min_length=1)
    untrusted_inputs: list[UntrustedInput]
    timeout_seconds: float = Field(gt=0)
    max_output_tokens: int = Field(gt=0)


class ModelResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    parsed: dict[str, Any]
    output_hash: str = Field(min_length=64, max_length=64)
    provider_request_id: str | None
    provider: ModelVendor
    model: str
    prompt_name: str
    prompt_version: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    prompt_cache_hit_rate: float | None = Field(default=None, ge=0, le=1)
    cost_usd: str | None
    latency_ms: int = Field(ge=0)


class ModelProvider(Protocol):
    def complete_json(self, request: ModelRequest) -> ModelResponse: ...


def quote_untrusted(block: UntrustedInput) -> str:
    return wrap_untrusted(block.name, UntrustedText(block.content))


def render_untrusted_user_message(request: ModelRequest) -> str:
    return "\n\n".join(quote_untrusted(block) for block in request.untrusted_inputs)


def model_call_ledger_fields(response: ModelResponse) -> dict[str, Any]:
    """Aggregates plus identifiers. Never a key, a prompt, or a raw request."""
    fields: dict[str, Any] = {
        "provider": response.provider,
        "model": response.model,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cost_usd": response.cost_usd,
        "latency_ms": response.latency_ms,
        "output_hash": response.output_hash,
        "provider_request_id": response.provider_request_id,
        "prompt_name": response.prompt_name,
        "prompt_version": response.prompt_version,
    }
    if response.prompt_cache_hit_rate is not None:
        fields["prompt_cache_hit_rate"] = response.prompt_cache_hit_rate
    return fields


def optional_cost_usd_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def optional_cost_usd_float(value: str | None) -> float | None:
    if value is None:
        return None
    return float(value)


def sum_known_cost_usd(values: Iterable[str | None]) -> tuple[float, bool]:
    """Sum priced calls only. Returns (total, is_partial).

    is_partial is True when any call was unpriced.
    """
    total = 0.0
    is_partial = False
    for value in values:
        if value is None:
            is_partial = True
            continue
        total += float(value)
    return total, is_partial


def cost_usd_for(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> str | None:
    prices = _PRICE_PER_MILLION.get((provider, model))
    if prices is None:
        return None
    input_price, output_price = prices
    million = Decimal("1000000")
    total = (Decimal(input_tokens) / million * input_price) + (
        Decimal(output_tokens) / million * output_price
    )
    text = format(total, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text if text else "0"


def cache_hit_rate_for(input_tokens: int, cached_input_tokens: int | None) -> float | None:
    if cached_input_tokens is None:
        return None
    if input_tokens <= 0:
        return 0.0
    clipped = max(0, min(cached_input_tokens, input_tokens))
    return clipped / input_tokens


def finish_completion(
    *,
    vendor: ModelVendor,
    request: ModelRequest,
    content: str,
    input_tokens: int,
    output_tokens: int,
    prompt_cache_hit_rate: float | None = None,
    provider_request_id: str | None,
    latency_ms: int,
) -> ModelResponse:
    try:
        parsed: object = json.loads(content)
    except (TypeError, json.JSONDecodeError) as exc:
        raise InvalidModelJson() from exc
    if not isinstance(parsed, dict):
        raise InvalidModelJson()
    if request.schema_name == "FindingCandidate":
        try:
            FindingCandidate.model_validate(parsed)
        except ValidationError as exc:
            raise ModelSchemaMismatch() from exc
    elif request.schema_name == "ReviewFindingsDraft":
        findings = parsed.get("findings")
        if not isinstance(findings, list):
            raise ModelSchemaMismatch()
        for item in findings:
            try:
                FindingDraft.model_validate(item)
            except ValidationError:
                raise ModelSchemaMismatch() from None
    elif request.schema_name == "FindingReflectionScores":
        scores = parsed.get("scores")
        if not isinstance(scores, list):
            raise ModelSchemaMismatch()
        for score in scores:
            if not isinstance(score, dict):
                raise ModelSchemaMismatch()
            if not isinstance(score.get("index"), int):
                raise ModelSchemaMismatch()
            if not isinstance(score.get("score"), int | float):
                raise ModelSchemaMismatch()
            if not isinstance(score.get("reason"), str) or not score["reason"]:
                raise ModelSchemaMismatch()
    else:
        raise ModelSchemaMismatch()
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return ModelResponse(
        parsed=parsed,
        output_hash=digest,
        provider_request_id=provider_request_id,
        provider=vendor,
        model=request.model,
        prompt_name=request.prompt_name,
        prompt_version=request.prompt_version,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        prompt_cache_hit_rate=prompt_cache_hit_rate,
        cost_usd=cost_usd_for(vendor, request.model, input_tokens, output_tokens),
        latency_ms=latency_ms,
    )


def verify_provider_api_key(
    provider_id: ModelVendor,
    api_key: str,
    *,
    http: httpx.Client | None = None,
) -> None:
    """Probe the provider with a lightweight models listing call."""
    if provider_id == "openai":
        client = http if http is not None else httpx.Client(base_url="https://api.openai.com")
        response = client.get(
            "/v1/models",
            headers=provider_auth_headers("openai", api_key),
            timeout=10.0,
        )
    else:
        client = http if http is not None else httpx.Client(base_url="https://api.anthropic.com")
        response = client.get(
            "/v1/models",
            headers=provider_auth_headers("anthropic", api_key),
            timeout=10.0,
        )
    if response.status_code in {401, 403}:
        raise ModelKeyInvalid()
    if response.status_code != 200:
        raise ModelProviderFailure(
            f"provider returned {response.status_code}",
            status_code=response.status_code,
        )


def _provider_error_message(payload: Any) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message")
        if message is not None:
            return str(message)
    return ""


def raise_for_provider_status(response: httpx.Response) -> None:
    if response.status_code == 200:
        return
    if response.status_code == 429:
        raise ModelRateLimit()
    payload: Any
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    error = payload.get("error") if isinstance(payload, dict) else None
    code = ""
    message_lower = ""
    if isinstance(error, dict):
        code = str(error.get("code") or "")
        message_lower = str(error.get("message") or "").lower()
    if response.status_code == 400 and (
        code == "context_length_exceeded" or "too long" in message_lower
    ):
        raise ModelContextLimit()
    provider_message = _provider_error_message(payload)
    if provider_message:
        raise ModelProviderFailure(provider_message, status_code=response.status_code)
    raise ModelProviderFailure(
        f"provider returned {response.status_code}",
        status_code=response.status_code,
    )
