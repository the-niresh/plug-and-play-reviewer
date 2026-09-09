"""Indexed retrieval for a live review. Reuses eval checkout, index, and search."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

from pr_reviewer.context_budget import context_budget_for_model
from pr_reviewer.contracts.review_context import ContextBudget, PackedDiff, ReviewContextItem
from pr_reviewer.github.pull_request import PullRequestSnapshot
from pr_reviewer.retrieval.context_items import context_items_from_chunks
from pr_reviewer.retrieval.embed import EmbeddingProvider
from pr_reviewer.retrieval.hybrid_search import RetrievalQuery

LOCAL_REVIEW_INSTALLATION_ID = 1
DEFAULT_REPO_CACHE = Path.home() / ".cache" / "pr-reviewer" / "eval-repos"
ConnectFn = Callable[[], AbstractContextManager[Any]]


def local_repository_id(owner: str, name: str) -> int:
    digest = hashlib.sha256(f"{owner}/{name}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 2_147_483_646 + 1


def index_ids_for_snapshot(snapshot: PullRequestSnapshot) -> tuple[int, int]:
    if snapshot.identity is not None:
        return snapshot.identity.installation_id, snapshot.identity.repository_id
    return (
        LOCAL_REVIEW_INSTALLATION_ID,
        local_repository_id(snapshot.repo_owner, snapshot.repo_name),
    )


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def retrieve_indexed_context(
    *,
    packed: PackedDiff,
    conn: Any,
    embedder: EmbeddingProvider,
    installation_id: int,
    repository_id: int,
    commit_sha: str,
    budget: ContextBudget,
    count_tokens: Callable[[str], int],
) -> list[ReviewContextItem]:
    from pr_reviewer.retrieval import hybrid_search

    query = RetrievalQuery(
        installation_id=installation_id,
        repository_id=repository_id,
        commit_sha=commit_sha,
        text="\n".join(item.content for item in packed.items),
    )
    chunks = hybrid_search.retrieve_context(
        query,
        conn,
        embedder,
        packed=packed,
        budget=budget,
        count_tokens=count_tokens,
        enabled=True,
    )
    return context_items_from_chunks(chunks)


class IndexedRetrievalExecutor:
    """Checkout, index locally, then retrieve. Never writes to the hosted plane."""

    def __init__(
        self,
        *,
        connect: ConnectFn | None = None,
        embedder: EmbeddingProvider | None = None,
        repo_cache: Any | None = None,
        count_tokens: Callable[[str], int] = _count_tokens,
    ) -> None:
        self._connect = connect
        self._embedder = embedder
        self._repo_cache = repo_cache
        self._count_tokens = count_tokens

    def retrieve(
        self,
        snapshot: PullRequestSnapshot,
        packed: PackedDiff,
        budget: ContextBudget | None = None,
    ) -> list[ReviewContextItem]:
        from pr_reviewer.runner.eval_ablation import (
            EvalRepositoryCache,
            local_retrieval_connection,
            resolve_eval_embedder,
        )

        connect = self._connect if self._connect is not None else local_retrieval_connection
        cache = self._repo_cache
        if cache is None:
            cache = EvalRepositoryCache(DEFAULT_REPO_CACHE)
        active_budget = budget if budget is not None else context_budget_for_model("gpt-4o-mini")
        repository = f"{snapshot.repo_owner}/{snapshot.repo_name}"
        installation_id, repository_id = index_ids_for_snapshot(snapshot)
        with connect() as conn:
            embedder = self._embedder
            if embedder is None:
                embedder, _offline = resolve_eval_embedder(offline=False)
            checkout = cache.ensure_checkout(repository, snapshot.head_sha)
            cache.ensure_indexed(
                conn,
                repository=repository,
                sha=snapshot.head_sha,
                checkout=checkout,
                embedder=embedder,
                installation_id=installation_id,
                repository_id=repository_id,
            )
            return retrieve_indexed_context(
                packed=packed,
                conn=conn,
                embedder=embedder,
                installation_id=installation_id,
                repository_id=repository_id,
                commit_sha=snapshot.head_sha,
                budget=active_budget,
                count_tokens=self._count_tokens,
            )
