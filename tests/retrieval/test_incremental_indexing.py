"""Failing tests for incremental re-indexing (Task 35.A1).

A second index of an unchanged repository must issue zero embedding calls: the
generation is rebuilt from the previous active generation's embeddings wherever
the chunk identity and content hash both still match. Only a genuinely changed
chunk is sent to the embedder. Proved with a counting fake, not a mock assertion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from test_index_repository import V1_DIM, _vector_for

pytest_plugins = ["test_index_repository"]

ALPHA_SOURCE = "def alpha():\n    return 1"
BETA_SOURCE = "def beta():\n    return 2"
BETA_CHANGED_SOURCE = "def beta():\n    return 999"


class CountingEmbedder:
    model_name = "text-embedding-3-small"
    dimensions = V1_DIM

    def __init__(self) -> None:
        self.calls = 0
        self.embedded_texts: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        self.embedded_texts.extend(texts)
        return [_vector_for(text) for text in texts]


def test_second_index_of_an_unchanged_repository_issues_zero_embedding_calls(
    retrieval_conn: Any, tmp_path: Path
) -> None:
    from pr_reviewer.retrieval.index_repository import index_repository, queryable_chunks

    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text(ALPHA_SOURCE, encoding="utf-8")
    (root / "b.py").write_text(BETA_SOURCE, encoding="utf-8")

    embedder = CountingEmbedder()
    index_repository(
        retrieval_conn,
        root=root,
        installation_id=11,
        repository_id=22,
        commit_sha="a" * 40,
        embedder=embedder,
    )
    assert embedder.calls == 1
    assert sorted(embedder.embedded_texts) == sorted([ALPHA_SOURCE, BETA_SOURCE])

    embedder.embedded_texts.clear()
    second = index_repository(
        retrieval_conn,
        root=root,
        installation_id=11,
        repository_id=22,
        commit_sha="b" * 40,
        embedder=embedder,
    )

    assert embedder.calls == 1
    assert embedder.embedded_texts == []
    assert second.state == "active"
    identities = {chunk.identity for chunk in queryable_chunks(retrieval_conn, 11, 22)}
    assert any("alpha" in identity for identity in identities)
    assert any("beta" in identity for identity in identities)


def test_only_the_changed_chunk_is_re_embedded(retrieval_conn: Any, tmp_path: Path) -> None:
    from pr_reviewer.retrieval.index_repository import index_repository, queryable_chunks

    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text(ALPHA_SOURCE, encoding="utf-8")
    (root / "b.py").write_text(BETA_SOURCE, encoding="utf-8")

    embedder = CountingEmbedder()
    index_repository(
        retrieval_conn,
        root=root,
        installation_id=33,
        repository_id=44,
        commit_sha="c" * 40,
        embedder=embedder,
    )
    assert sorted(embedder.embedded_texts) == sorted([ALPHA_SOURCE, BETA_SOURCE])

    (root / "b.py").write_text(BETA_CHANGED_SOURCE, encoding="utf-8")
    embedder.embedded_texts.clear()
    index_repository(
        retrieval_conn,
        root=root,
        installation_id=33,
        repository_id=44,
        commit_sha="d" * 40,
        embedder=embedder,
    )

    assert embedder.embedded_texts == [BETA_CHANGED_SOURCE]
    contents = {
        chunk.identity: chunk.content
        for chunk in queryable_chunks(retrieval_conn, 33, 44)
    }
    assert contents["a.py::alpha"] == ALPHA_SOURCE
    assert contents["b.py::beta"] == BETA_CHANGED_SOURCE


def test_no_previous_generation_embeds_every_chunk(retrieval_conn: Any, tmp_path: Path) -> None:
    from pr_reviewer.retrieval.index_repository import index_repository

    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text(ALPHA_SOURCE, encoding="utf-8")

    embedder = CountingEmbedder()
    index_repository(
        retrieval_conn,
        root=root,
        installation_id=55,
        repository_id=66,
        commit_sha="e" * 40,
        embedder=embedder,
    )
    assert embedder.calls == 1
    assert embedder.embedded_texts == [ALPHA_SOURCE]
