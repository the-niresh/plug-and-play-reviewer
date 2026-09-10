"""Failing tests for graph-connected retrieval (Task 35.A2).

Text similarity finds code that looks alike. A reviewer also needs code that is
connected: a caller of the changed function, in a different file, that shares no
words with the query. Only the call graph can find that caller. These tests fail
if retrieval only ever returns chunks that win on vector or lexical rank.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from test_index_repository import FakeEmbedder

pytest_plugins = ["test_index_repository"]

HELPER_CHUNK_CONTENT = "def helper():\n    return 1"
HELPER_FILE_CONTENT = HELPER_CHUNK_CONTENT + "\n"
CALLER_B_CHUNK_CONTENT = "def caller_b():\n    return 2"
CALLER_B_FILE_CONTENT = CALLER_B_CHUNK_CONTENT + "\n"
CALLER_C_CHUNK_CONTENT = "def caller_c():\n    return 3"
CALLER_C_FILE_CONTENT = CALLER_C_CHUNK_CONTENT + "\n"


def _index(
    conn: Any,
    root: Path,
    *,
    installation_id: int,
    repository_id: int,
    commit_sha: str,
) -> Any:
    from pr_reviewer.retrieval.index_repository import index_repository

    return index_repository(
        conn,
        root=root,
        installation_id=installation_id,
        repository_id=repository_id,
        commit_sha=commit_sha,
        embedder=FakeEmbedder(),
    )


def _query(**overrides: Any) -> Any:
    from pr_reviewer.retrieval.hybrid_search import RetrievalQuery

    fields: dict[str, Any] = {
        "installation_id": 1,
        "repository_id": 2,
        "commit_sha": "a" * 40,
        "text": HELPER_CHUNK_CONTENT,
    }
    fields.update(overrides)
    return RetrievalQuery(**fields)


def _one_caller_graph() -> Any:
    from pr_reviewer.retrieval.code_graph import CodeGraph, GraphEdge, GraphNode

    return CodeGraph(
        nodes={
            "helper_symbol": GraphNode(id="helper_symbol", label="helper()", source_file="a.py"),
            "caller_b_symbol": GraphNode(
                id="caller_b_symbol", label="caller_b()", source_file="b.py"
            ),
        },
        edges=(
            GraphEdge(
                source="caller_b_symbol",
                target="helper_symbol",
                relation="calls",
                confidence="EXTRACTED",
            ),
        ),
    )


def test_caller_in_a_different_file_is_found_only_through_the_call_graph(
    retrieval_conn: Any, tmp_path: Path
) -> None:
    from pr_reviewer.retrieval.hybrid_search import retrieve_context

    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text(HELPER_FILE_CONTENT, encoding="utf-8")
    (root / "b.py").write_text(CALLER_B_FILE_CONTENT, encoding="utf-8")
    _index(retrieval_conn, root, installation_id=1, repository_id=2, commit_sha="a" * 40)

    without_graph = retrieve_context(
        _query(),
        retrieval_conn,
        FakeEmbedder(),
        enabled=True,
        limit=1,
    )
    assert without_graph
    assert without_graph[0].file_path == "a.py"
    assert "b.py" not in {chunk.file_path for chunk in without_graph}

    with_graph = retrieve_context(
        _query(changed_symbols=("helper_symbol",)),
        retrieval_conn,
        FakeEmbedder(),
        enabled=True,
        limit=1,
        graph=_one_caller_graph(),
    )
    assert with_graph
    assert with_graph[0].file_path == "b.py"
    assert with_graph[0].identity == "b.py::caller_b"


def test_graph_ranking_is_reordered_by_sensitivity(retrieval_conn: Any, tmp_path: Path) -> None:
    from pr_reviewer.retrieval.code_graph import CodeGraph, GraphEdge, GraphNode
    from pr_reviewer.retrieval.hybrid_search import _graph_ranked_ids
    from pr_reviewer.retrieval.sensitivity import SensitivityScore

    root = tmp_path / "repo"
    root.mkdir()
    (root / "a.py").write_text(HELPER_FILE_CONTENT, encoding="utf-8")
    (root / "b.py").write_text(CALLER_B_FILE_CONTENT, encoding="utf-8")
    (root / "c.py").write_text(CALLER_C_FILE_CONTENT, encoding="utf-8")
    _index(retrieval_conn, root, installation_id=9, repository_id=9, commit_sha="c" * 40)

    graph = CodeGraph(
        nodes={
            "helper_symbol": GraphNode(id="helper_symbol", label="helper()", source_file="a.py"),
            "caller_b_symbol": GraphNode(
                id="caller_b_symbol", label="caller_b()", source_file="b.py"
            ),
            "caller_c_symbol": GraphNode(
                id="caller_c_symbol", label="caller_c()", source_file="c.py"
            ),
        },
        edges=(
            GraphEdge(
                source="caller_b_symbol",
                target="helper_symbol",
                relation="calls",
                confidence="EXTRACTED",
            ),
            GraphEdge(
                source="caller_c_symbol",
                target="helper_symbol",
                relation="calls",
                confidence="EXTRACTED",
            ),
        ),
    )
    query = _query(
        installation_id=9,
        repository_id=9,
        commit_sha="c" * 40,
        changed_symbols=("helper_symbol",),
    )

    def paths_for(chunk_ids: list[str]) -> list[str]:
        ordered = []
        for chunk_id in chunk_ids:
            row = retrieval_conn.execute(
                "select file_path from code_chunks where id = %s::uuid", (chunk_id,)
            ).fetchone()
            assert row is not None
            ordered.append(str(row["file_path"] if isinstance(row, dict) else row[0]))
        return ordered

    unweighted = _graph_ranked_ids(retrieval_conn, query, graph, 1, None)
    assert paths_for(unweighted) == ["b.py", "c.py"]

    scores = {
        "b.py": SensitivityScore(
            path="b.py",
            fix_density=0.0,
            fix_count=0,
            commit_count=0,
            caller_count=1,
            structural_flags=(),
            evidence=(),
        ),
        "c.py": SensitivityScore(
            path="c.py",
            fix_density=0.0,
            fix_count=0,
            commit_count=0,
            caller_count=5,
            structural_flags=(),
            evidence=(),
        ),
    }
    weighted = _graph_ranked_ids(retrieval_conn, query, graph, 1, scores)
    assert paths_for(weighted) == ["c.py", "b.py"]
