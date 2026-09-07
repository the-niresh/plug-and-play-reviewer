"""Hybrid vector + full-text retrieval, merged with RRF. Off by default."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from psycopg import Connection

from pr_reviewer.contracts.review_context import ContextBudget, PackedDiff
from pr_reviewer.retrieval.code_graph import CodeGraph
from pr_reviewer.retrieval.embed import EmbeddingProvider, embed_texts
from pr_reviewer.retrieval.rrf import reciprocal_rank_fusion
from pr_reviewer.retrieval.sensitivity import SensitivityScore
from pr_reviewer.security.prompt_boundaries import UntrustedText, wrap_untrusted

RETRIEVAL_ENABLED_DEFAULT = False
_CANDIDATE_MULTIPLIER = 4
_GRAPH_DEPTH_DEFAULT = 2
_GRAPH_RANKING_WEIGHT = 2.0
"""A call-graph connection is verified, not incidental. It outweighs a text match."""


@dataclass(frozen=True)
class RetrievalQuery:
    installation_id: int
    repository_id: int
    commit_sha: str
    text: str
    changed_symbols: tuple[str, ...] = field(default=())


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    file_path: str
    line_start: int
    line_end: int
    content: str
    content_hash: str
    identity: str


def retrieve_context(
    query: RetrievalQuery,
    conn: Connection[Any],
    embedder: EmbeddingProvider,
    *,
    packed: PackedDiff | None = None,
    budget: ContextBudget | None = None,
    count_tokens: Callable[[str], int] | None = None,
    limit: int = 8,
    record_selection: Callable[[Sequence[str]], None] | None = None,
    enabled: bool | None = None,
    graph: CodeGraph | None = None,
    graph_depth: int = _GRAPH_DEPTH_DEFAULT,
    sensitivity_scores: Mapping[str, SensitivityScore] | None = None,
) -> list[RetrievedChunk]:
    if enabled is None:
        enabled = RETRIEVAL_ENABLED_DEFAULT
    if not enabled:
        return []

    candidate_limit = max(limit, limit * _CANDIDATE_MULTIPLIER)
    vectors = embed_texts(embedder, [query.text])
    query_vector = _vector_literal(vectors[0])
    vector_ids = _rank_ids(
        conn,
        query,
        extra_where="",
        extra_params=(),
        order_sql="c.embedding <=> %s::vector",
        order_params=(query_vector,),
        limit=candidate_limit,
    )
    lexical_ids = _rank_ids(
        conn,
        query,
        extra_where="and c.content_tsv @@ plainto_tsquery('simple', %s)",
        extra_params=(query.text,),
        order_sql="ts_rank(c.content_tsv, plainto_tsquery('simple', %s)) desc",
        order_params=(query.text,),
        limit=candidate_limit,
    )
    rankings = [vector_ids, lexical_ids]
    weights = [1.0, 1.0]
    if graph is not None and query.changed_symbols:
        graph_ids = _graph_ranked_ids(conn, query, graph, graph_depth, sensitivity_scores)
        if graph_ids:
            rankings.append(graph_ids)
            weights.append(_GRAPH_RANKING_WEIGHT)
    fused = reciprocal_rank_fusion(rankings, weights=weights)
    chunks = _load_chunks(conn, fused)[:limit]
    if packed is not None and budget is not None:
        if count_tokens is None:
            raise TypeError("count_tokens is required when fitting chunks to a packed diff")
        chunks = fit_retrieved_chunks(packed, chunks, budget, count_tokens)
    if record_selection is not None:
        record_selection([chunk.chunk_id for chunk in chunks])
    return chunks


def fit_retrieved_chunks(
    packed: PackedDiff,
    chunks: Sequence[RetrievedChunk],
    budget: ContextBudget,
    count_tokens: Callable[[str], int],
) -> list[RetrievedChunk]:
    remaining = budget.tokens - packed.prompt_tokens
    selected: list[RetrievedChunk] = []
    for chunk in chunks:
        cost = count_tokens(chunk.content)
        if cost <= remaining:
            selected.append(chunk)
            remaining -= cost
    return selected


def wrap_retrieved_chunks(chunks: Sequence[RetrievedChunk]) -> list[str]:
    return [
        wrap_untrusted("retrieved_chunk", UntrustedText(chunk.content))
        for chunk in chunks
    ]


def selection_event_payload(chunk_ids: Sequence[str]) -> dict[str, int | str]:
    return {"chunk_ids": ",".join(chunk_ids), "count": len(chunk_ids)}


def _graph_ranked_ids(
    conn: Connection[Any],
    query: RetrievalQuery,
    graph: CodeGraph,
    depth: int,
    sensitivity_scores: Mapping[str, SensitivityScore] | None,
) -> list[str]:
    """Rank chunk ids from files connected to the changed symbols, not from text.

    A caller or importer of a changed symbol is included even if its own content
    shares no words with the query. Connected files are ordered by descending
    sensitivity caller_count when scores are available, so the most-called file
    among several callers is offered to the model first.
    """
    connected_paths: list[str] = []
    seen: set[str] = set()
    for symbol in query.changed_symbols:
        for node_id in graph.blast_radius(symbol, depth):
            node = graph.nodes.get(node_id)
            path = node.source_file if node is not None else ""
            if not path or path in seen:
                continue
            seen.add(path)
            connected_paths.append(path)
    if sensitivity_scores:
        connected_paths.sort(key=lambda path: -_caller_count(sensitivity_scores, path))
    ids: list[str] = []
    for path in connected_paths:
        ids.extend(_chunk_ids_for_path(conn, query, path))
    return ids


def _caller_count(scores: Mapping[str, SensitivityScore], path: str) -> int:
    score = scores.get(path)
    return score.caller_count if score is not None else 0


def _chunk_ids_for_path(conn: Connection[Any], query: RetrievalQuery, path: str) -> list[str]:
    rows = conn.execute(
        """
        select c.id
        from code_chunks c
        join embedding_generations g on g.id = c.generation_id
        where g.installation_id = %s
          and g.repository_id = %s
          and g.commit_sha = %s
          and g.state = 'active'
          and c.file_path = %s
        order by c.start_line
        """,
        (query.installation_id, query.repository_id, query.commit_sha, path),
    ).fetchall()
    return [_id_from_row(row) for row in rows]


def _rank_ids(
    conn: Connection[Any],
    query: RetrievalQuery,
    *,
    extra_where: str,
    extra_params: tuple[object, ...],
    order_sql: str,
    order_params: tuple[object, ...],
    limit: int,
) -> list[str]:
    rows = conn.execute(
        f"""
        select c.id
        from code_chunks c
        join embedding_generations g on g.id = c.generation_id
        where g.installation_id = %s
          and g.repository_id = %s
          and g.commit_sha = %s
          and g.state = 'active'
          {extra_where}
        order by {order_sql}
        limit %s
        """,
        (
            query.installation_id,
            query.repository_id,
            query.commit_sha,
            *extra_params,
            *order_params,
            limit,
        ),
    ).fetchall()
    return [_id_from_row(row) for row in rows]


def _load_chunks(conn: Connection[Any], chunk_ids: Sequence[str]) -> list[RetrievedChunk]:
    if not chunk_ids:
        return []
    rows = conn.execute(
        """
        select id, file_path, start_line, end_line, content, content_hash, identity
        from code_chunks
        where id = any(%s::uuid[])
        """,
        (list(chunk_ids),),
    ).fetchall()
    by_id: dict[str, RetrievedChunk] = {}
    for row in rows:
        chunk = _chunk_from_row(row)
        by_id[chunk.chunk_id] = chunk
    return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]


def _chunk_from_row(row: Any) -> RetrievedChunk:
    values = _row_map(
        row,
        (
            "id",
            "file_path",
            "start_line",
            "end_line",
            "content",
            "content_hash",
            "identity",
        ),
    )
    return RetrievedChunk(
        chunk_id=_as_id(values["id"]),
        file_path=str(values["file_path"]),
        line_start=int(values["start_line"]),
        line_end=int(values["end_line"]),
        content=str(values["content"]),
        content_hash=str(values["content_hash"]),
        identity=str(values["identity"]),
    )


def _row_map(row: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(row, dict):
        return {key: row[key] for key in keys}
    return {key: row[index] for index, key in enumerate(keys)}


def _id_from_row(row: Any) -> str:
    return _as_id(row["id"] if isinstance(row, dict) else row[0])


def _as_id(value: Any) -> str:
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(format(value, ".8f") for value in values) + "]"
