"""OpenAI adapter backed by the generic OpenAI-compatible provider."""

from __future__ import annotations

import httpx

from pr_reviewer.models.openai_compatible import (
    OpenAICompatibleProvider,
    OpenAICompatibleProviderConfig,
)


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        super().__init__(
            config=OpenAICompatibleProviderConfig(
                provider_id="openai",
                base_url="https://api.openai.com",
            ),
            api_key=api_key,
            http=http,
            ledger_vendor="openai",
        )
