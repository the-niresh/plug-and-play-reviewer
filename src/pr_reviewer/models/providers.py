"""Authentication details for the providers supported by the local runner."""

from __future__ import annotations

from typing import Literal

ProviderName = Literal[
    "openai",
    "anthropic",
    "moonshot",
    "qwen",
    "openrouter",
    "groq",
    "xai",
    "deepseek",
    "github-copilot",
    "ollama",
    "opencode",
]

ANTHROPIC_VERSION = "2023-06-01"

OPENAI_COMPATIBLE_PROVIDERS: frozenset[ProviderName] = frozenset(
    {
        "openai",
        "moonshot",
        "qwen",
        "openrouter",
        "groq",
        "xai",
        "deepseek",
        "github-copilot",
        "ollama",
        "opencode",
    }
)


def provider_auth_headers(provider: ProviderName, api_key: str) -> dict[str, str]:
    """Return only the headers accepted by one provider's API."""
    if provider == "anthropic":
        return {"x-api-key": api_key, "anthropic-version": ANTHROPIC_VERSION}
    return {"authorization": f"Bearer {api_key}"}
