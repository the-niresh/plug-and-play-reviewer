"""Context-overflow fallback must jump to a larger window model."""

from __future__ import annotations

from pr_reviewer.models.provider_errors import ProviderErrorKind, ProviderFailure
from pr_reviewer.models.retry import RetryPolicy


def test_context_overflow_skips_next_name_and_chooses_larger_window() -> None:
    from pr_reviewer.models.fallback import FallbackModel, fallback_across_models

    calls: list[str] = []

    def attempt(model: FallbackModel) -> str | ProviderFailure:
        calls.append(model.model)
        if model.model == "gpt-4o-mini":
            return ProviderFailure(
                provider="openai",
                kind=ProviderErrorKind.BAD_REQUEST,
                reason="context_length_exceeded: prompt too long",
            )
        if model.model == "gpt-4o":
            raise AssertionError("next-in-list is wrong: context overflow needs larger window")
        return "ok"

    result = fallback_across_models(
        attempt,
        candidates=(
            FallbackModel(vendor="openai", model="gpt-4o-mini"),
            FallbackModel(vendor="openai", model="gpt-4o"),
            FallbackModel(vendor="openai", model="gpt-4.1-mini"),
        ),
        retry_policy=RetryPolicy(max_attempts=2, max_elapsed_seconds=5),
    )

    assert result.value == "ok"
    assert calls == ["gpt-4o-mini", "gpt-4.1-mini"]
