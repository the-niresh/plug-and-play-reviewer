"""Embedding provider contract and the v1 1536-dimension check.

Model name and dimensions live on the generation, not on each chunk, so mixing
models or widths in one generation cannot be represented. The schema pins
vector(1536); this module fails closed if the live column drifts.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol

from psycopg import Connection

V1_EMBEDDING_DIMENSIONS = 1536
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
DETERMINISTIC_EMBEDDING_MODEL = "deterministic-sha256-v1"
_EMBEDDING_PRICE_PER_MILLION: dict[str, Decimal] = {
    OPENAI_EMBEDDING_MODEL: Decimal("0.02"),
}
DEFAULT_ESTIMATED_SHA_INDEX_TOKENS = 250_000
MAX_EMBEDDING_TOKENS_PER_INPUT = 8192
MAX_EMBEDDING_INPUT_CHARS = MAX_EMBEDDING_TOKENS_PER_INPUT * 3


@dataclass
class EmbeddingCostLedger:
    total_tokens: int = 0
    total_cost_usd: Decimal = field(default_factory=lambda: Decimal(0))

    def record(self, token_count: int, cost_usd: Decimal) -> None:
        self.total_tokens += token_count
        self.total_cost_usd += cost_usd


def estimate_embedding_tokens(text: str) -> int:
    return max(1, len(text) // 3)


def embedding_cost_usd_for(token_count: int, model_name: str) -> Decimal:
    if model_name == DETERMINISTIC_EMBEDDING_MODEL:
        return Decimal(0)
    price = _EMBEDDING_PRICE_PER_MILLION.get(model_name)
    if price is None:
        raise ValueError(f"unknown embedding model {model_name!r}")
    million = Decimal("1000000")
    return (Decimal(token_count) / million) * price

_VECTOR_TYPE = f"vector({V1_EMBEDDING_DIMENSIONS})"
_HOSTED_CONTROL_PLANE_TABLES = ("review_jobs", "github_deliveries")


class HostedRetrievalIndexError(RuntimeError):
    """Raised when indexing is attempted against the hosted control plane."""


class EmbeddingContractError(RuntimeError):
    """The local schema is not the v1 1536-dimension embedding contract."""


class EmbeddingDimensionError(ValueError):
    """An embedder advertised or returned a width other than 1536."""


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...




def assert_local_retrieval_store(conn: Connection[Any]) -> None:
    """Refuse to write retrieval indexes into the hosted control plane database."""
    row = conn.execute(
        """
        select 1
        from information_schema.tables
        where table_schema = 'public'
          and table_name = any(%s)
        limit 1
        """,
        (list(_HOSTED_CONTROL_PLANE_TABLES),),
    ).fetchone()
    if row is not None:
        raise HostedRetrievalIndexError(
            "the retrieval index may never live on the hosted control plane; "
            "connect to the local runner pgvector store instead"
        )


def assert_v1_embedding_contract(conn: Connection[Any]) -> None:
    row = conn.execute(
        """
        select format_type(a.atttypid, a.atttypmod) as typ
        from pg_attribute a
        join pg_class c on c.oid = a.attrelid
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public'
          and c.relname = 'code_chunks'
          and a.attname = 'embedding'
          and a.attnum > 0
          and not a.attisdropped
        """
    ).fetchone()
    typ = _value(row, "typ", 0) if row is not None else None
    if typ != _VECTOR_TYPE:
        raise EmbeddingContractError(f"code_chunks.embedding must be {_VECTOR_TYPE}, found {typ!r}")

    checks = conn.execute(
        """
        select pg_get_constraintdef(oid) as definition
        from pg_constraint
        where conrelid = 'embedding_generations'::regclass and contype = 'c'
        """
    ).fetchall()
    definitions = " ".join(str(_value(item, "definition", 0)) for item in checks)
    if "1536" not in definitions:
        raise EmbeddingContractError("embedding_generations.dimensions must be constrained to 1536")


def embed_texts(provider: EmbeddingProvider, texts: Sequence[str]) -> list[list[float]]:
    if provider.dimensions != V1_EMBEDDING_DIMENSIONS:
        raise EmbeddingDimensionError(
            f"embedder {provider.model_name!r} has dimensions "
            f"{provider.dimensions}, v1 requires {V1_EMBEDDING_DIMENSIONS}"
        )
    if not texts:
        return []
    vectors = provider.embed(texts)
    if len(vectors) != len(texts):
        raise EmbeddingDimensionError("embedder returned the wrong number of vectors")
    for vector in vectors:
        if len(vector) != V1_EMBEDDING_DIMENSIONS:
            raise EmbeddingDimensionError(
                f"embedder {provider.model_name!r} returned {len(vector)} dimensions, "
                f"v1 requires {V1_EMBEDDING_DIMENSIONS}"
            )
    return vectors


def _value(row: Any, key: str, index: int) -> Any:
    if isinstance(row, dict):
        return row[key]
    return row[index]
