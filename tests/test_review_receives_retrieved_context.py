"""Failing tests for Task 35.A3: retrieved context must reach the model prompt.

agent_surfaces/backend.py used to pass a literal [] as the retrieval context to
review_pull_request, so nothing built by retrieval (35.A1, 35.A2) ever reached a
review. These tests assert the retrieved chunk content is actually present in the
prompt sent to the model, not merely that some retrieval function was called, and
that it arrives wrapped as untrusted input rather than interpolated raw.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from test_review_pull_request import _file, _packed, _snapshot

RETRIEVED_SENTINEL = "RETRIEVED_SENTINEL_caller_of_the_changed_helper"


def _capturing_model() -> Any:
    from pr_reviewer.models.provider import ModelResponse

    class CapturingModel:
        def __init__(self) -> None:
            self.calls: list[Any] = []

        def complete_json(self, request: Any) -> Any:
            self.calls.append(request)
            return ModelResponse(
                parsed={"findings": []},
                output_hash="a" * 64,
                provider_request_id=None,
                provider="anthropic",
                model=request.model,
                prompt_name=request.prompt_name,
                prompt_version=request.prompt_version,
                input_tokens=1,
                output_tokens=1,
                cost_usd="0",
                latency_ms=1,
            )

    return CapturingModel()


def _stub_indexed_retrieval(
    monkeypatch: Any, tmp_path: Path, *, seen: dict[str, Any]
) -> None:
    from pr_reviewer.retrieval.hybrid_search import RetrievedChunk
    from pr_reviewer.runner.eval_ablation import EvalRepositoryCache

    class FakeEmbedder:
        model_name = "text-embedding-3-small"
        dimensions = 1536

        def embed(self, texts: list[str]) -> list[list[float]]:
            del texts
            raise AssertionError("indexing is stubbed; embed must not run")

    @contextmanager
    def fake_connect() -> Iterator[object]:
        yield object()

    def fake_retrieve_context(
        query: object, conn: object, embedder: object, **kwargs: object
    ) -> list[RetrievedChunk]:
        del conn, embedder
        seen["enabled"] = kwargs.get("enabled")
        seen["commit_sha"] = getattr(query, "commit_sha", None)
        return [
            RetrievedChunk(
                chunk_id="1",
                file_path="unrelated_caller.py",
                line_start=1,
                line_end=1,
                content=RETRIEVED_SENTINEL,
                content_hash="a" * 64,
                identity="caller",
            )
        ]

    monkeypatch.setattr(
        "pr_reviewer.retrieval.hybrid_search.retrieve_context", fake_retrieve_context
    )
    monkeypatch.setattr(
        "pr_reviewer.runner.eval_ablation.local_retrieval_connection", fake_connect
    )
    monkeypatch.setattr(
        "pr_reviewer.runner.eval_ablation.resolve_eval_embedder",
        lambda **kwargs: (FakeEmbedder(), False),
    )
    monkeypatch.setattr(
        EvalRepositoryCache, "ensure_checkout", lambda self, repository, sha: tmp_path
    )
    monkeypatch.setattr(
        EvalRepositoryCache, "ensure_indexed", lambda *args, **kwargs: None
    )


def test_default_live_backend_retrieves_index_context_into_the_prompt(
    monkeypatch: Any, tmp_path: Path
) -> None:
    from pr_reviewer.agent_surfaces import backend
    from pr_reviewer.agent_surfaces.core import AgentReviewRequest

    seen: dict[str, Any] = {}
    _stub_indexed_retrieval(monkeypatch, tmp_path, seen=seen)
    model = _capturing_model()

    def fake_fetch_pull_request(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        return _snapshot([_file("app.py")])

    def fake_pack_diff(snapshot: Any, budget: Any, count_tokens: Any) -> Any:
        del count_tokens
        del budget
        return _packed(snapshot.files)

    monkeypatch.setenv(backend.GITHUB_TOKEN_ENV, "gh-token")
    monkeypatch.setattr(backend, "resolve_model_provider", lambda: ("anthropic", model))
    monkeypatch.setattr(backend, "fetch_pull_request", fake_fetch_pull_request)
    monkeypatch.setattr(backend, "pack_diff", fake_pack_diff)

    live = backend.LiveAgentReviewBackend()
    assert not isinstance(live._retrieval, backend.NullRetrievalExecutor)

    review = live.start_review(
        AgentReviewRequest(owner="acme", repository="widgets", pull_request=12)
    )

    assert review.status == "complete"
    assert seen.get("enabled") is True
    assert RETRIEVED_SENTINEL in model.calls[0].prompt_content


def test_live_backend_forwards_retrieved_chunks_into_the_prompt(monkeypatch: Any) -> None:
    from pr_reviewer.agent_surfaces import backend
    from pr_reviewer.agent_surfaces.core import AgentReviewRequest
    from pr_reviewer.contracts.review_context import ReviewContextItem

    class FakeRetrieval:
        def retrieve(
            self, snapshot: Any, packed: Any, budget: Any = None
        ) -> list[ReviewContextItem]:
            del snapshot, packed, budget
            return [
                ReviewContextItem(
                    source_kind="diff_file",
                    file_path="unrelated_caller.py",
                    line_start=1,
                    line_end=1,
                    content=RETRIEVED_SENTINEL,
                    content_hash="a" * 64,
                )
            ]

    class FakeProvider:
        pass

    model = _capturing_model()

    def fake_fetch_pull_request(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        return _snapshot([_file("app.py")])

    def fake_pack_diff(snapshot: Any, budget: Any, count_tokens: Any) -> Any:
        del count_tokens
        del budget
        return _packed(snapshot.files)

    monkeypatch.setenv(backend.GITHUB_TOKEN_ENV, "gh-token")
    monkeypatch.setattr(backend, "resolve_model_provider", lambda: ("anthropic", model))
    monkeypatch.setattr(backend, "fetch_pull_request", fake_fetch_pull_request)
    monkeypatch.setattr(backend, "pack_diff", fake_pack_diff)

    review = backend.LiveAgentReviewBackend(retrieval=FakeRetrieval()).start_review(
        AgentReviewRequest(owner="acme", repository="widgets", pull_request=12)
    )

    assert review.status == "complete"
    assert model.calls, "the model was never called"
    prompt_content = model.calls[0].prompt_content
    assert RETRIEVED_SENTINEL in prompt_content
    assert '"retrieved_chunk"' in prompt_content or "retrieved_chunk" in prompt_content


def test_null_retrieval_executor_sends_no_retrieved_chunks(
    monkeypatch: Any,
) -> None:
    from pr_reviewer.agent_surfaces import backend
    from pr_reviewer.agent_surfaces.core import AgentReviewRequest

    model = _capturing_model()

    def fake_fetch_pull_request(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        return _snapshot([_file("app.py")])

    def fake_pack_diff(snapshot: Any, budget: Any, count_tokens: Any) -> Any:
        del count_tokens
        del budget
        return _packed(snapshot.files)

    monkeypatch.setenv(backend.GITHUB_TOKEN_ENV, "gh-token")
    monkeypatch.setattr(backend, "resolve_model_provider", lambda: ("anthropic", model))
    monkeypatch.setattr(backend, "fetch_pull_request", fake_fetch_pull_request)
    monkeypatch.setattr(backend, "pack_diff", fake_pack_diff)

    review = backend.LiveAgentReviewBackend(
        retrieval=backend.NullRetrievalExecutor()
    ).start_review(
        AgentReviewRequest(owner="acme", repository="widgets", pull_request=12)
    )

    assert review.status == "complete"
    assert "retrieved_chunk" not in model.calls[0].prompt_content


def test_retrieved_chunks_are_wrapped_as_untrusted_not_interpolated_raw() -> None:
    from pr_reviewer.contracts.review_context import ReviewContextItem
    from pr_reviewer.reviewer.review_pull_request import review_pull_request
    from pr_reviewer.security.prompt_boundaries import UntrustedText, wrap_untrusted

    model = _capturing_model()
    context = [
        ReviewContextItem(
            source_kind="diff_file",
            file_path="unrelated_caller.py",
            line_start=1,
            line_end=1,
            content=RETRIEVED_SENTINEL,
            content_hash="a" * 64,
        )
    ]

    review_pull_request(
        _snapshot([_file("app.py")]),
        _packed([_file("app.py")]),
        context,
        model,
        model_name="claude-3-5-haiku-latest",
    )

    expected_section = wrap_untrusted("retrieved_chunk", UntrustedText(RETRIEVED_SENTINEL))
    assert expected_section in model.calls[0].prompt_content


def test_indexed_executor_refuses_the_hosted_control_plane_connection(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from pr_reviewer.contracts.review_context import ContextBudget
    from pr_reviewer.db.client import connection as hosted_connection
    from pr_reviewer.retrieval.embed import HostedRetrievalIndexError
    from pr_reviewer.retrieval.executor import IndexedRetrievalExecutor
    from pr_reviewer.runner.eval_ablation import EvalRepositoryCache

    (tmp_path / "a.py").write_text("def alpha():\n    return 1\n", encoding="utf-8")
    cache = EvalRepositoryCache(tmp_path)
    monkeypatch.setattr(
        EvalRepositoryCache, "ensure_checkout", lambda self, repository, sha: tmp_path
    )

    class FakeEmbedder:
        model_name = "text-embedding-3-small"
        dimensions = 1536

        def embed(self, texts: list[str]) -> list[list[float]]:
            del texts
            raise AssertionError("hosted index must fail before embed")

    executor = IndexedRetrievalExecutor(
        connect=hosted_connection,
        embedder=FakeEmbedder(),
        repo_cache=cache,
    )
    with pytest.raises(HostedRetrievalIndexError, match="hosted control plane"):
        executor.retrieve(
            _snapshot([_file("app.py")]),
            _packed([_file("app.py")]),
            ContextBudget(tokens=10_000),
        )
