"""Real holdout ablation reviewers. Reuses review_pull_request and hybrid retrieval."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import psycopg

from pr_reviewer.context_budget import context_budget_for_model
from pr_reviewer.contracts.review_context import ReviewContextItem
from pr_reviewer.evals.eval_snapshot import snapshot_from_eval_case
from pr_reviewer.evals.types import EvalCase, EvalReviewResult, ReviewerCallable
from pr_reviewer.models.provider import ModelProvider
from pr_reviewer.retrieval.chunk_code import chunk_tree
from pr_reviewer.retrieval.deterministic_embed import DeterministicEmbeddingProvider
from pr_reviewer.retrieval.embed import (
    DEFAULT_ESTIMATED_SHA_INDEX_TOKENS,
    EmbeddingCostLedger,
    EmbeddingProvider,
    embedding_cost_usd_for,
    estimate_embedding_tokens,
)
from pr_reviewer.retrieval.hybrid_search import RetrievalQuery, RetrievedChunk, retrieve_context
from pr_reviewer.retrieval.index_repository import index_repository
from pr_reviewer.retrieval.openai_embeddings import OpenAIEmbeddingProvider
from pr_reviewer.reviewer.diff_budget import pack_diff
from pr_reviewer.reviewer.review_pull_request import estimate_review_cost, review_pull_request

EVAL_INSTALLATION_ID = 9_001
EVAL_REPOSITORY_IDS: dict[str, int] = {
    "pallets/flask": 901,
    "colinhacks/zod": 902,
}
OFFLINE_EMBEDDINGS_WARNING = (
    "NOT A VALID MEASUREMENT: offline embeddings produce no semantic similarity "
    "and cannot support a retrieval ablation conclusion."
)


class EvalAblationConfigurationError(RuntimeError):
    """The ablation command is missing a required provider or key."""


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def resolve_eval_embedder(
    *,
    offline: bool,
    ledger: EmbeddingCostLedger | None = None,
) -> tuple[EmbeddingProvider, bool]:
    active_ledger = ledger if ledger is not None else EmbeddingCostLedger()
    if offline:
        return DeterministicEmbeddingProvider(), True
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EvalAblationConfigurationError(
            "OPENAI_API_KEY is required for embedding-backed ablation."
        )
    return OpenAIEmbeddingProvider(api_key=api_key, ledger=active_ledger), False



@contextmanager
def local_retrieval_connection() -> Iterator[psycopg.Connection[Any]]:
    """Open the runner local pgvector store, migrating it if needed."""
    from pr_reviewer.local_store.postgres import LocalVectorStore, LocalVectorStoreError
    from pr_reviewer.runner.modes import ModeDecision
    from pr_reviewer.runner.secrets import FileSecretStore, default_config_dir

    config_dir = default_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    secrets = FileSecretStore(config_dir)
    store = LocalVectorStore(
        secrets=secrets,
        mode=ModeDecision(
            requested_mode="full",
            granted_mode="full",
            retrieval_available=True,
            verification_available=True,
            forces_human_approval=False,
            downgraded=False,
            disabled_features=(),
            probe_failures=(),
        ),
        work_directory=config_dir,
    )
    status = store.health()
    if not status.healthy:
        try:
            store.start()
        except LocalVectorStoreError as exc:
            raise EvalAblationConfigurationError(
                f"Local pgvector failed to start: {exc}"
            ) from exc
    try:
        store.migrate()
    except LocalVectorStoreError as exc:
        raise EvalAblationConfigurationError(
            f"Local pgvector migrations failed: {exc}"
        ) from exc
    try:
        conn = psycopg.connect(store.connection_url())
    except Exception as exc:
        raise EvalAblationConfigurationError(
            f"Local pgvector connection failed: {exc}"
        ) from exc
    try:
        yield conn
    finally:
        conn.close()


class EvalRepositoryCache:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._indexed: set[tuple[str, str]] = set()

    def ensure_checkout(self, repository: str, sha: str) -> Path:
        slug = repository.replace("/", "__")
        repo_dir = self._root / slug
        if not (repo_dir / ".git").exists():
            subprocess.run(
                ["git", "clone", f"https://github.com/{repository}.git", str(repo_dir)],
                check=True,
            )
        subprocess.run(["git", "fetch", "--all"], cwd=repo_dir, check=True)
        subprocess.run(["git", "checkout", sha], cwd=repo_dir, check=True)
        return repo_dir

    def ensure_indexed(
        self,
        conn: Any,
        *,
        repository: str,
        sha: str,
        checkout: Path,
        embedder: EmbeddingProvider,
    ) -> None:
        key = (repository, sha)
        if key in self._indexed:
            return
        index_repository(
            conn,
            root=checkout,
            installation_id=EVAL_INSTALLATION_ID,
            repository_id=EVAL_REPOSITORY_IDS[repository],
            commit_sha=sha,
            embedder=embedder,
        )
        self._indexed.add(key)


@dataclass
class EvalAblationDependencies:
    model: ModelProvider
    model_name: str
    conn: Any
    repo_cache: EvalRepositoryCache
    embedder: EmbeddingProvider | None = None
    embedding_ledger: EmbeddingCostLedger = field(default_factory=EmbeddingCostLedger)
    offline_embeddings: bool = False


def context_items_from_chunks(chunks: Sequence[RetrievedChunk]) -> list[ReviewContextItem]:
    return [
        ReviewContextItem(
            source_kind="diff_file",
            file_path=chunk.file_path,
            line_start=chunk.line_start,
            line_end=chunk.line_end,
            content=chunk.content,
            content_hash=chunk.content_hash,
        )
        for chunk in chunks
    ]


def review_eval_case(
    case: EvalCase, *, use_retrieval: bool, deps: EvalAblationDependencies
) -> EvalReviewResult:
    snapshot = snapshot_from_eval_case(case)
    budget = context_budget_for_model(deps.model_name)
    packed = pack_diff(snapshot, budget, _count_tokens)
    if use_retrieval:
        embedder = cast(EmbeddingProvider, deps.embedder)
        checkout = deps.repo_cache.ensure_checkout(case.repository, case.sha)
        deps.repo_cache.ensure_indexed(
            deps.conn,
            repository=case.repository,
            sha=case.sha,
            checkout=checkout,
            embedder=embedder,
        )
        query = RetrievalQuery(
            installation_id=EVAL_INSTALLATION_ID,
            repository_id=EVAL_REPOSITORY_IDS[case.repository],
            commit_sha=case.sha,
            text="\n".join(item.content for item in packed.items),
        )
        chunks = retrieve_context(
            query,
            deps.conn,
            embedder,
            packed=packed,
            budget=budget,
            count_tokens=_count_tokens,
            enabled=True,
        )
        context = context_items_from_chunks(chunks)
    else:
        context = []
    outcome = review_pull_request(
        snapshot,
        packed,
        context,
        deps.model,
        model_name=deps.model_name,
    )
    return EvalReviewResult(
        findings=outcome.candidates,
        cost_usd=outcome.cost_usd,
        latency_ms=outcome.latency_ms,
    )


def build_eval_ablation_reviewers(
    deps: EvalAblationDependencies,
) -> tuple[ReviewerCallable, ReviewerCallable]:
    return (
        lambda case: review_eval_case(case, use_retrieval=False, deps=deps),
        lambda case: review_eval_case(case, use_retrieval=True, deps=deps),
    )


def _estimate_index_embedding_tokens(case: EvalCase, cache_root: Path) -> int:
    slug = case.repository.replace("/", "__")
    repo_dir = cache_root / slug
    if not (repo_dir / ".git").exists():
        return DEFAULT_ESTIMATED_SHA_INDEX_TOKENS
    try:
        subprocess.run(
            ["git", "checkout", case.sha],
            cwd=repo_dir,
            check=True,
            capture_output=True,
        )
        chunks = chunk_tree(repo_dir)
        if not chunks:
            return DEFAULT_ESTIMATED_SHA_INDEX_TOKENS
        return sum(estimate_embedding_tokens(chunk.content) for chunk in chunks)
    except subprocess.CalledProcessError:
        return DEFAULT_ESTIMATED_SHA_INDEX_TOKENS


def estimate_embedding_cost_usd(
    cases: Sequence[EvalCase],
    *,
    repeats: int,
    offline_embeddings: bool,
    cache_root: Path | None = None,
) -> Decimal:
    if offline_embeddings:
        return Decimal(0)
    holdout = [case for case in cases if case.split == "holdout"]
    total_tokens = 0
    seen_shas: set[tuple[str, str]] = set()
    root = cache_root or Path.home() / ".cache" / "pr-reviewer" / "eval-repos"
    for case in holdout:
        key = (case.repository, case.sha)
        if key not in seen_shas:
            seen_shas.add(key)
            total_tokens += _estimate_index_embedding_tokens(case, root)
        snapshot = snapshot_from_eval_case(case)
        packed = pack_diff(snapshot, context_budget_for_model("gpt-4o-mini"), _count_tokens)
        query_text = "\n".join(item.content for item in packed.items)
        total_tokens += estimate_embedding_tokens(query_text) * repeats
    return embedding_cost_usd_for(total_tokens, OpenAIEmbeddingProvider.model_name)


def estimate_ablation_cost_usd(
    cases: Sequence[EvalCase],
    model_name: str,
    *,
    repeats: int,
    offline_embeddings: bool = False,
    cache_root: Path | None = None,
) -> Decimal:
    holdout = [case for case in cases if case.split == "holdout"]
    model_total = Decimal(0)
    for case in holdout:
        snapshot = snapshot_from_eval_case(case)
        packed = pack_diff(snapshot, context_budget_for_model(model_name), _count_tokens)
        prompt = "\n".join(item.content for item in packed.items)
        per_review = estimate_review_cost(prompt, model_name).cost_usd * 2
        model_total += per_review * 2 * repeats
    embedding_total = estimate_embedding_cost_usd(
        cases,
        repeats=repeats,
        offline_embeddings=offline_embeddings,
        cache_root=cache_root,
    )
    return model_total + embedding_total


def format_ablation_cost_summary(
    *,
    model_cost_usd: Decimal,
    embedding_cost_usd: Decimal,
) -> str:
    total = model_cost_usd + embedding_cost_usd
    return (
        f"Total cost: models ${model_cost_usd:.4f} + embeddings ${embedding_cost_usd:.4f} "
        f"= ${total:.4f}"
    )
