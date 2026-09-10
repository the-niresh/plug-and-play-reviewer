"""Out-of-credit fallback must cross vendor, not burn same-vendor models."""

from __future__ import annotations

from pr_reviewer.models.provider_errors import ProviderErrorKind, ProviderFailure
from pr_reviewer.models.retry import RetryPolicy


def test_out_of_credit_skips_same_vendor_and_crosses_to_another_vendor() -> None:
    from pr_reviewer.models.fallback import FallbackModel, fallback_across_models

    calls: list[tuple[str, str]] = []

    def attempt(model: FallbackModel) -> str | ProviderFailure:
        calls.append((model.vendor, model.model))
        if model.vendor == "openai" and model.model == "gpt-4o-mini":
            return ProviderFailure(
                provider="openai",
                kind=ProviderErrorKind.OUT_OF_TOKENS,
                reason="credit balance exhausted",
            )
        if model.vendor == "openai":
            raise AssertionError("same-vendor fallback after out-of-credit is forbidden")
        return "ok"

    result = fallback_across_models(
        attempt,
        candidates=(
            FallbackModel(vendor="openai", model="gpt-4o-mini"),
            FallbackModel(vendor="openai", model="gpt-4.1"),
            FallbackModel(vendor="anthropic", model="claude-3-5-haiku-latest"),
        ),
        retry_policy=RetryPolicy(max_attempts=3, max_elapsed_seconds=5),
    )

    assert result.value == "ok"
    assert calls == [
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-3-5-haiku-latest"),
    ]
