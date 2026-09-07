"""Model fallback chain wrapped around the existing retry policy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pr_reviewer.context_budget import context_budget_for_model
from pr_reviewer.models.provider_errors import ProviderErrorKind, ProviderFailure
from pr_reviewer.models.retry import RetryPolicy, RetryResult, retry_provider_call

_CONTEXT_OVERFLOW_MARKERS = (
    "context_length_exceeded",
    "context window",
    "prompt is too long",
    "too long",
)


@dataclass(frozen=True)
class FallbackModel:
    vendor: str
    model: str


def _model_context_tokens(model: str) -> int:
    try:
        return context_budget_for_model(model).tokens
    except KeyError:
        return 0


def _is_context_overflow(failure: ProviderFailure) -> bool:
    if failure.kind is not ProviderErrorKind.BAD_REQUEST:
        return False
    text = failure.reason.lower()
    return any(marker in text for marker in _CONTEXT_OVERFLOW_MARKERS)


def _next_larger_window(
    candidates: tuple[FallbackModel, ...],
    *,
    current: FallbackModel,
    attempted: set[FallbackModel],
    blocked_vendors: set[str],
    model_context_tokens: Callable[[str], int],
) -> FallbackModel | None:
    current_tokens = model_context_tokens(current.model)
    for candidate in candidates:
        if candidate in attempted:
            continue
        if candidate.vendor in blocked_vendors:
            continue
        if model_context_tokens(candidate.model) > current_tokens:
            return candidate
    return None


def _next_cross_vendor(
    candidates: tuple[FallbackModel, ...],
    *,
    attempted: set[FallbackModel],
    blocked_vendors: set[str],
) -> FallbackModel | None:
    for candidate in candidates:
        if candidate in attempted:
            continue
        if candidate.vendor in blocked_vendors:
            continue
        return candidate
    return None


def fallback_across_models[Result](
    attempt: Callable[[FallbackModel], Result | ProviderFailure],
    *,
    candidates: tuple[FallbackModel, ...],
    retry_policy: RetryPolicy,
    model_context_tokens: Callable[[str], int] = _model_context_tokens,
) -> RetryResult[Result]:
    if not candidates:
        raise ValueError("candidates must not be empty")

    attempted: set[FallbackModel] = set()
    blocked_vendors: set[str] = set()
    current = candidates[0]

    while True:
        result = retry_provider_call(lambda c=current: attempt(c), policy=retry_policy)
        if result.value is not None:
            return RetryResult(value=result.value)
        failure = result.failure
        assert failure is not None
        attempted.add(current)

        if failure.kind is ProviderErrorKind.OUT_OF_TOKENS:
            blocked_vendors.add(current.vendor)
            next_model = _next_cross_vendor(
                candidates, attempted=attempted, blocked_vendors=blocked_vendors
            )
            if next_model is None:
                return RetryResult(failure=failure)
            current = next_model
            continue

        if _is_context_overflow(failure):
            next_model = _next_larger_window(
                candidates,
                current=current,
                attempted=attempted,
                blocked_vendors=blocked_vendors,
                model_context_tokens=model_context_tokens,
            )
            if next_model is None:
                return RetryResult(failure=failure)
            current = next_model
            continue

        return RetryResult(failure=failure)
