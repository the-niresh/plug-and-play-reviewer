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
    count_embedding_tokens,
    embedding_cost_usd_for,
    estimate_embedding_tokens,
    split_text_to_max_embedding_tokens,
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
        pending: list[str] = []
        for text in texts:
            if count_embedding_tokens(text) > MAX_EMBEDDING_TOKENS_PER_INPUT:
                if pending:
                    vectors.extend(self._embed_batched_texts(pending))
                    pending = []
                vectors.append(self._embed_split_and_average(text))
            else:
                pending.append(text)
        if pending:
            vectors.extend(self._embed_batched_texts(pending))
        return vectors

    def _embed_batched_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for batch in _embedding_batches(texts):
            vectors.extend(self._embed_batch(batch))
        return vectors

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            return self._embed_batch_post(texts)
        except ModelProviderFailure as exc:
            if is_embedding_request_token_limit_failure(exc) and len(texts) > 1:
                midpoint = len(texts) // 2
                return self._embed_batch(texts[:midpoint]) + self._embed_batch(texts[midpoint:])
            if is_embedding_input_token_limit_failure(exc):
                if len(texts) == 1:
                    return [self._embed_split_and_average(texts[0])]
                return [self._embed_one_resilient(text) for text in texts]
            raise

    def _embed_one_resilient(self, text: str) -> list[float]:
        try:
            return self._embed_batch_post([text])[0]
        except ModelProviderFailure as exc:
            if is_embedding_input_token_limit_failure(exc):
                return self._embed_split_and_average(text)
            raise

    def _embed_split_and_average(self, text: str) -> list[float]:
        parts = split_text_to_max_embedding_tokens(text, MAX_EMBEDDING_TOKENS_PER_INPUT)
        vectors = [self._embed_text_piece(part) for part in parts]
        return _average_vectors(vectors)

    def _embed_text_piece(self, text: str) -> list[float]:
        try:
            return self._embed_batch_post([text])[0]
        except ModelProviderFailure as exc:
            if not is_embedding_input_token_limit_failure(exc):
                raise
            token_count = count_embedding_tokens(text)
            if token_count <= 1:
                raise
            parts = split_text_to_max_embedding_tokens(text, max(1, token_count // 2))
            if len(parts) == 1:
                midpoint = len(text) // 2
                parts = [text[:midpoint], text[midpoint:]]
            vectors = [self._embed_text_piece(part) for part in parts]
            return _average_vectors(vectors)

    def _embed_batch_post(self, texts: list[str]) -> list[list[float]]:
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


def is_embedding_request_token_limit_failure(exc: ModelProviderFailure) -> bool:
    """True when the provider rejected a batch for exceeding the request token cap."""
    if exc.status_code != 400:
        return False
    message = str(exc).lower()
    if is_embedding_input_token_limit_failure(exc):
        return False
    has_token_signal = "token" in message
    has_limit_signal = any(word in message for word in ("max", "limit", "exceed", "requested"))
    has_request_scope = "request" in message
    return has_token_signal and has_limit_signal and has_request_scope


def is_embedding_input_token_limit_failure(exc: ModelProviderFailure) -> bool:
    """True when the provider rejected one input for exceeding the per-input token cap."""
    if exc.status_code != 400:
        return False
    message = str(exc).lower()
    has_input_signal = "input[" in message or ("input" in message and "length" in message)
    has_token_signal = "token" in message
    has_limit_signal = any(word in message for word in ("max", "limit", "exceed"))
    return has_input_signal and has_token_signal and has_limit_signal


def _embedding_batches(texts: Sequence[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    current_tokens = 0
    for index, text in enumerate(texts):
        true_tokens = count_embedding_tokens(text)
        if true_tokens > MAX_EMBEDDING_TOKENS_PER_INPUT:
            raise EmbeddingInputTooLargeError(index, true_tokens)
        tokens = estimate_embedding_tokens(text)
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


def _average_vectors(vectors: Sequence[Sequence[float]]) -> list[float]:
    if not vectors:
        raise ModelProviderFailure("cannot average an empty vector list")
    width = len(vectors[0])
    total = [0.0] * width
    for vector in vectors:
        if len(vector) != width:
            raise ModelProviderFailure("embedding vectors had mismatched widths")
        for index, value in enumerate(vector):
            total[index] += float(value)
    count = float(len(vectors))
    return [value / count for value in total]


def _coerce_vector(raw: Any) -> list[float]:
    if not isinstance(raw, list):
        raise ModelProviderFailure("embedding vector was not a list")
    return [float(value) for value in raw]
