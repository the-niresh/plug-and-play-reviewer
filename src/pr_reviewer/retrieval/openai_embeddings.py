"""OpenAI embedding provider for retrieval indexing and query."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from pr_reviewer.models.provider import ModelProviderFailure, raise_for_provider_status
from pr_reviewer.retrieval.embed import (
    MAX_EMBEDDING_TOKENS_PER_INPUT,
    OPENAI_EMBEDDING_MODEL,
    V1_EMBEDDING_DIMENSIONS,
    EmbeddingCostLedger,
    embedding_cost_usd_for,
    estimate_embedding_tokens,
)

MAX_EMBEDDING_INPUTS_PER_REQUEST = 2048
MAX_EMBEDDING_TOKENS_PER_REQUEST = 300_000


class EmbeddingInputTooLargeError(RuntimeError):
    """One input alone exceeds the provider per-input token cap."""

    def __init__(self, text_index: int, token_count: int) -> None:
        super().__init__(
            f"embedding input at index {text_index} has {token_count} tokens, "
            f"above the {MAX_EMBEDDING_TOKENS_PER_INPUT} token limit per input"
        )
        self.text_index = text_index
        self.token_count = token_count


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
        vectors: list[list[float]] = []
        for batch in _embedding_batches(texts):
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self._http.post(
            "/v1/embeddings",
            json={"model": self.model_name, "input": texts},
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
        ordered_rows = sorted(rows, key=lambda row: int(row["index"]))
        vectors = [_coerce_vector(row["embedding"]) for row in ordered_rows]
        if len(vectors) != len(texts):
            raise ModelProviderFailure("embedding response returned the wrong count")
        return vectors


def _embedding_batches(texts: Sequence[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    for index, text in enumerate(texts):
        tokens = estimate_embedding_tokens(text)
        if tokens > MAX_EMBEDDING_TOKENS_PER_INPUT:
            raise EmbeddingInputTooLargeError(index, tokens)
        if current and (
            len(current) >= MAX_EMBEDDING_INPUTS_PER_REQUEST
            or current_tokens + tokens > MAX_EMBEDDING_TOKENS_PER_REQUEST
        ):
            batches.append(current)
            current = []
            current_tokens = 0
        current.append(text)
        current_tokens += tokens
    if current:
        batches.append(current)
    return batches


def _coerce_vector(raw: Any) -> list[float]:
    if not isinstance(raw, list):
        raise ModelProviderFailure("embedding vector was not a list")
    return [float(value) for value in raw]
