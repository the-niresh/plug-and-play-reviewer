"""OpenAI embedding provider for retrieval indexing and query."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from pr_reviewer.models.provider import ModelProviderFailure, raise_for_provider_status
from pr_reviewer.retrieval.embed import (
    OPENAI_EMBEDDING_MODEL,
    V1_EMBEDDING_DIMENSIONS,
    EmbeddingCostLedger,
    embedding_cost_usd_for,
)


class _EmbeddingHttp(Protocol):
    def post(
        self,
        path: str,
        *,
        json: object,
        headers: dict[str, str],
        timeout: float,
    ) -> httpx.Response: ...


class OpenAIEmbeddingProvider:
    model_name = OPENAI_EMBEDDING_MODEL
    dimensions = V1_EMBEDDING_DIMENSIONS

    def __init__(
        self,
        api_key: str,
        *,
        ledger: EmbeddingCostLedger | None = None,
        http: _EmbeddingHttp | None = None,
        base_url: str = "https://api.openai.com",
    ) -> None:
        self._api_key = api_key
        self._ledger = ledger
        self._http = http if http is not None else httpx.Client(base_url=base_url)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._http.post(
            "/v1/embeddings",
            json={"model": self.model_name, "input": list(texts)},
            headers={"authorization": f"Bearer {self._api_key}"},
            timeout=60.0,
        )
        raise_for_provider_status(response)
        payload = response.json()
        try:
            rows = payload["data"]
            usage = payload.get("usage") or {}
            prompt_tokens = int(usage.get("prompt_tokens", 0))
        except (KeyError, TypeError, ValueError) as exc:
            raise ModelProviderFailure("embedding response was malformed") from exc
        if self._ledger is not None and prompt_tokens > 0:
            self._ledger.record(
                prompt_tokens,
                embedding_cost_usd_for(prompt_tokens, self.model_name),
            )
        vectors = [_coerce_vector(row["embedding"]) for row in rows]
        if len(vectors) != len(texts):
            raise ModelProviderFailure("embedding response returned the wrong count")
        return vectors


def _coerce_vector(raw: Any) -> list[float]:
    if not isinstance(raw, list):
        raise ModelProviderFailure("embedding vector was not a list")
    return [float(value) for value in raw]
