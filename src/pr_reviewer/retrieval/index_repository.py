"""Index a repository commit as one embedding generation.

The generation is inserted as building, chunks are written, then the previous
active generation is retired and this one is marked active in the same
transaction. Queries only read state = 'active', so a half-built generation is
never visible. Exact cosine distance first; no approximate index.
"""

from __future__ import annotations

from collections.abc import Sequence, Set
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from psycopg import Connection

from pr_reviewer.retrieval.chunk_code import ChunkingStrategy, CodeChunk, chunk_tree
from pr_reviewer.retrieval.embed import (
    V1_EMBEDDING_DIMENSIONS,
    EmbeddingProvider,
    assert_v1_embedding_contract,
    embed_texts,
)


@dataclass(frozen=True)
class IndexGeneration:
    id: str
    installation_id: int
    repository_id: int
    commit_sha: str
    model_name: str
    dimensions: int
    state: str


def index_repository(
    conn: Connection[Any],
    *,
    root: Path,
    installation_id: int,
    repository_id: int,
    commit_sha: str,
    embedder: EmbeddingProvider,
    generated_paths: Set[str] | None = None,
    ignored_paths: Set[str] | None = None,
) -> IndexGeneration:
    assert_v1_embedding_contract(conn)
    chunks = chunk_tree(
        root,
        generated_paths=generated_paths,
        ignored_paths=ignored_paths,
    )
    previous = _previous_chunk_embeddings(conn, installation_id, repository_id)
    to_embed = [
        index
        for index, chunk in enumerate(chunks)
        if previous.get(chunk.identity, (None, ""))[0] != chunk.content_hash
    ]
    texts_to_embed = [chunks[index].content for index in to_embed]
    embedded = embed_texts(embedder, texts_to_embed) if to_embed else []
    vector_literals: dict[int, str] = {
        index: _vector_literal(vector) for index, vector in zip(to_embed, embedded, strict=True)
    }
    for index, chunk in enumerate(chunks):
        if index not in vector_literals:
            vector_literals[index] = previous[chunk.identity][1]
    try:
        inserted = conn.execute(
            """
            insert into embedding_generations (
              installation_id, repository_id, commit_sha, model_name, dimensions, state
            ) values (%s, %s, %s, %s, %s, 'building')
            returning id
            """,
            (
                installation_id,
                repository_id,
                commit_sha,
                embedder.model_name,
                V1_EMBEDDING_DIMENSIONS,
            ),
        ).fetchone()
        generation_id = str(_value(inserted, "id", 0))
        for index, chunk in enumerate(chunks):
            conn.execute(
                """
                insert into code_chunks (
                  generation_id, file_path, language, start_line, end_line,
                  content, content_hash, identity, strategy, symbol_name, embedding
                ) values (
                  %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector
                )
                """,
                (
                    generation_id,
                    chunk.file_path,
                    chunk.language,
                    chunk.start_line,
                    chunk.end_line,
                    chunk.content,
                    chunk.content_hash,
                    chunk.identity,
                    chunk.strategy.value,
                    chunk.symbol_name,
                    vector_literals[index],
                ),
            )
        conn.execute(
            """
            update embedding_generations
            set state = 'retired'
            where installation_id = %s
              and repository_id = %s
              and state = 'active'
              and id <> %s::uuid
            """,
            (installation_id, repository_id, generation_id),
        )
        conn.execute(
            """
            update embedding_generations
            set state = 'active'
            where id = %s::uuid and state = 'building'
            """,
            (generation_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return IndexGeneration(
        id=generation_id,
        installation_id=installation_id,
        repository_id=repository_id,
        commit_sha=commit_sha,
        model_name=embedder.model_name,
        dimensions=V1_EMBEDDING_DIMENSIONS,
        state="active",
    )


def _previous_chunk_embeddings(
    conn: Connection[Any],
    installation_id: int,
    repository_id: int,
) -> dict[str, tuple[str, str]]:
    """Map chunk identity to (content_hash, embedding literal) for the active generation.

    Read once per index_repository call so an unchanged chunk can carry its embedding
    forward without a new call to the embedder.
    """
    rows = conn.execute(
        """
        select c.identity, c.content_hash, c.embedding::text as embedding
        from code_chunks c
        join embedding_generations g on g.id = c.generation_id
        where g.installation_id = %s
          and g.repository_id = %s
          and g.state = 'active'
        """,
        (installation_id, repository_id),
    ).fetchall()
    previous: dict[str, tuple[str, str]] = {}
    for row in rows:
        values = _row_map(row, ("identity", "content_hash", "embedding"))
        previous[str(values["identity"])] = (str(values["content_hash"]), str(values["embedding"]))
    return previous


def queryable_chunks(
    conn: Connection[Any],
    installation_id: int,
    repository_id: int,
) -> tuple[CodeChunk, ...]:
    rows = conn.execute(
        """
        select c.file_path, c.language, c.start_line, c.end_line, c.content,
               c.content_hash, c.identity, c.strategy, c.symbol_name
        from code_chunks c
        join embedding_generations g on g.id = c.generation_id
        where g.installation_id = %s
          and g.repository_id = %s
          and g.state = 'active'
        order by c.file_path, c.start_line
        """,
        (installation_id, repository_id),
    ).fetchall()
    return tuple(_chunk_from_row(row) for row in rows)


def exact_nearest_chunks(
    conn: Connection[Any],
    *,
    installation_id: int,
    repository_id: int,
    query: Sequence[float],
    limit: int,
) -> tuple[CodeChunk, ...]:
    rows = conn.execute(
        """
        select c.file_path, c.language, c.start_line, c.end_line, c.content,
               c.content_hash, c.identity, c.strategy, c.symbol_name
        from code_chunks c
        join embedding_generations g on g.id = c.generation_id
        where g.installation_id = %s
          and g.repository_id = %s
          and g.state = 'active'
        order by c.embedding <=> %s::vector
        limit %s
        """,
        (installation_id, repository_id, _vector_literal(query), limit),
    ).fetchall()
    return tuple(_chunk_from_row(row) for row in rows)


def _chunk_from_row(row: Any) -> CodeChunk:
    values = _row_map(
        row,
        (
            "file_path",
            "language",
            "start_line",
            "end_line",
            "content",
            "content_hash",
            "identity",
            "strategy",
            "symbol_name",
        ),
    )
    return CodeChunk(
        file_path=str(values["file_path"]),
        language=str(values["language"]),
        start_line=int(values["start_line"]),
        end_line=int(values["end_line"]),
        content=str(values["content"]),
        content_hash=str(values["content_hash"]),
        identity=str(values["identity"]),
        strategy=ChunkingStrategy(str(values["strategy"])),
        symbol_name=(str(values["symbol_name"]) if values["symbol_name"] is not None else None),
    )


def _row_map(row: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(row, dict):
        return {key: row[key] for key in keys}
    return {key: row[index] for index, key in enumerate(keys)}


def _value(row: Any, key: str, index: int) -> Any:
    if row is None:
        raise RuntimeError("expected a generation row")
    value = row[key] if isinstance(row, dict) else row[index]
    if isinstance(value, UUID):
        return str(value)
    return value


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(format(value, ".8f") for value in values) + "]"
