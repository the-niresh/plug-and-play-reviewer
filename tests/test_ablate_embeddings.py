"""Embedding provider wiring for reviewer ablate. Offline and free."""

from __future__ import annotations

import io
from decimal import Decimal

import pytest

from pr_reviewer.evals.run_eval import load_public_eval_cases
from pr_reviewer.retrieval.deterministic_embed import DeterministicEmbeddingProvider
from pr_reviewer.retrieval.embed import DETERMINISTIC_EMBEDDING_MODEL, OPENAI_EMBEDDING_MODEL
from pr_reviewer.retrieval.openai_embeddings import OpenAIEmbeddingProvider


def test_resolve_embedder_uses_openai_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from pr_reviewer.runner.eval_ablation import resolve_eval_embedder

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    embedder, offline = resolve_eval_embedder(offline=False)
    assert isinstance(embedder, OpenAIEmbeddingProvider)
    assert embedder.model_name == OPENAI_EMBEDDING_MODEL
    assert offline is False


def test_offline_embeddings_flag_uses_deterministic_provider() -> None:
    from pr_reviewer.runner.eval_ablation import resolve_eval_embedder

    embedder, offline = resolve_eval_embedder(offline=True)
    assert isinstance(embedder, DeterministicEmbeddingProvider)
    assert embedder.model_name == DETERMINISTIC_EMBEDDING_MODEL
    assert offline is True


def test_offline_ablate_marks_output_as_not_a_measurement(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pr_reviewer.runner.cli.ablate import main

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    def _fake_ablation(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("ablation must not run in offline-embedding smoke mode")

    monkeypatch.setattr("pr_reviewer.runner.cli.ablate.run_retrieval_ablation", _fake_ablation)

    code = main(["--offline-embeddings", "--json"], stdin=io.StringIO("yes\n"))
    captured = capsys.readouterr()
    assert code != 0
    assert "NOT A VALID MEASUREMENT" in captured.err
    assert "diff-only precision=" not in captured.out


def test_estimate_ablation_cost_includes_embedding_cost() -> None:
    from pr_reviewer.runner.eval_ablation import estimate_ablation_cost_usd

    cases = load_public_eval_cases()
    offline_total = estimate_ablation_cost_usd(
        cases, "gpt-4o-mini", repeats=1, offline_embeddings=True
    )
    online_total = estimate_ablation_cost_usd(
        cases, "gpt-4o-mini", repeats=1, offline_embeddings=False
    )
    assert online_total > offline_total
    assert online_total - offline_total > Decimal("0")


def test_embedding_cost_ledger_records_usage_from_provider() -> None:
    from pr_reviewer.retrieval.embed import EmbeddingCostLedger, embedding_cost_usd_for

    ledger = EmbeddingCostLedger()
    provider = OpenAIEmbeddingProvider(api_key="sk-test", ledger=ledger, http=_FakeEmbeddingHttp())
    vectors = provider.embed(["hello", "world"])
    assert len(vectors) == 2
    assert ledger.total_tokens > 0
    assert ledger.total_cost_usd == embedding_cost_usd_for(
        ledger.total_tokens, OPENAI_EMBEDDING_MODEL
    )


class _FakeEmbeddingHttp:
    def post(self, path: str, *, json: object, headers: object, timeout: float) -> object:
        assert path == "/v1/embeddings"
        inputs = json["input"] if isinstance(json, dict) else []
        count = len(inputs) if isinstance(inputs, list) else 1
        return _FakeEmbeddingResponse(count)


class _FakeEmbeddingResponse:
    def __init__(self, count: int) -> None:
        self._count = count

    def json(self) -> dict[str, object]:
        return {
            "data": [{"embedding": [0.1] * 1536, "index": index} for index in range(self._count)],
            "usage": {"prompt_tokens": self._count * 4, "total_tokens": self._count * 4},
        }

    @property
    def status_code(self) -> int:
        return 200


def test_embed_batches_large_inputs_preserving_order() -> None:
    from pr_reviewer.retrieval.openai_embeddings import OpenAIEmbeddingProvider

    texts = [f"chunk-{index}" for index in range(5000)]
    http = _BatchRecordingEmbeddingHttp()
    provider = OpenAIEmbeddingProvider(api_key="sk-test", http=http)
    vectors = provider.embed(texts)

    assert len(http.requests) > 1
    assert all(len(batch) <= 2048 for batch in http.requests)
    assert len(vectors) == len(texts)
    for index, vector in enumerate(vectors):
        assert vector[0] == float(index)


def test_embed_ledger_sums_tokens_across_batches() -> None:
    from pr_reviewer.retrieval.embed import EmbeddingCostLedger, embedding_cost_usd_for
    from pr_reviewer.retrieval.openai_embeddings import OpenAIEmbeddingProvider

    ledger = EmbeddingCostLedger()
    http = _BatchRecordingEmbeddingHttp(tokens_per_request=1000)
    provider = OpenAIEmbeddingProvider(api_key="sk-test", ledger=ledger, http=http)
    provider.embed([f"chunk-{index}" for index in range(5000)])

    assert len(http.requests) > 1
    expected_tokens = len(http.requests) * 1000
    assert ledger.total_tokens == expected_tokens
    assert ledger.total_cost_usd == embedding_cost_usd_for(
        expected_tokens, OPENAI_EMBEDDING_MODEL
    )


def test_local_retrieval_connection_body_exception_propagates_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pr_reviewer.runner.eval_ablation import local_retrieval_connection

    class _HealthyStore:
        def health(self) -> object:
            return type("Status", (), {"healthy": True})()

        def migrate(self) -> None:
            return None

        def connection_url(self) -> str:
            return "postgresql://u:p@127.0.0.1:55432/db"

    monkeypatch.setattr(
        "pr_reviewer.local_store.postgres.LocalVectorStore",
        lambda **kwargs: _HealthyStore(),
    )
    class _FakeConn:
        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "pr_reviewer.runner.eval_ablation.psycopg.connect",
        lambda *args, **kwargs: _FakeConn(),
    )

    with (
        pytest.raises(ValueError, match="embedding request failed"),
        local_retrieval_connection(),
    ):
        raise ValueError("embedding request failed")


def test_local_retrieval_connection_wraps_genuine_connection_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pr_reviewer.runner.eval_ablation import (
        EvalAblationConfigurationError,
        local_retrieval_connection,
    )

    class _HealthyStore:
        def health(self) -> object:
            return type("Status", (), {"healthy": True})()

        def migrate(self) -> None:
            return None

        def connection_url(self) -> str:
            return "postgresql://u:p@127.0.0.1:55432/db"

    monkeypatch.setattr(
        "pr_reviewer.local_store.postgres.LocalVectorStore",
        lambda **kwargs: _HealthyStore(),
    )

    def _fail_connect(*args: object, **kwargs: object) -> object:
        raise OSError("connection refused")

    monkeypatch.setattr("pr_reviewer.runner.eval_ablation.psycopg.connect", _fail_connect)

    with (
        pytest.raises(EvalAblationConfigurationError, match="connection failed"),
        local_retrieval_connection(),
    ):
        pass


def test_embed_rejects_single_input_over_per_input_token_limit() -> None:
    from pr_reviewer.retrieval.embed import estimate_embedding_tokens
    from pr_reviewer.retrieval.openai_embeddings import (
        MAX_EMBEDDING_TOKENS_PER_INPUT,
        EmbeddingInputTooLargeError,
        OpenAIEmbeddingProvider,
    )

    huge = "x" * (MAX_EMBEDDING_TOKENS_PER_INPUT * 4 + 4)
    assert estimate_embedding_tokens(huge) > MAX_EMBEDDING_TOKENS_PER_INPUT
    http = _BatchRecordingEmbeddingHttp()
    provider = OpenAIEmbeddingProvider(api_key="sk-test", http=http)
    with pytest.raises(EmbeddingInputTooLargeError):
        provider.embed([huge])
    assert http.requests == []


def test_embed_never_sends_one_api_item_over_per_input_token_limit() -> None:
    from pr_reviewer.retrieval.embed import estimate_embedding_tokens
    from pr_reviewer.retrieval.openai_embeddings import (
        MAX_EMBEDDING_TOKENS_PER_INPUT,
        OpenAIEmbeddingProvider,
    )

    texts = [f"chunk-{index}" for index in range(10)]
    http = _BatchRecordingEmbeddingHttp()
    provider = OpenAIEmbeddingProvider(api_key="sk-test", http=http)
    provider.embed(texts)
    for batch in http.requests:
        for text in batch:
            assert estimate_embedding_tokens(text) <= MAX_EMBEDDING_TOKENS_PER_INPUT


class _BatchRecordingEmbeddingHttp:
    def __init__(self, *, tokens_per_input: int = 4, tokens_per_request: int | None = None) -> None:
        self.requests: list[list[str]] = []
        self._tokens_per_input = tokens_per_input
        self._tokens_per_request = tokens_per_request
        self._next_index = 0

    def post(self, path: str, *, json: object, headers: object, timeout: float) -> object:
        assert path == "/v1/embeddings"
        inputs = json["input"] if isinstance(json, dict) else []
        batch = list(inputs) if isinstance(inputs, list) else [str(inputs)]
        self.requests.append(batch)
        start = self._next_index
        self._next_index += len(batch)
        if self._tokens_per_request is not None:
            tokens = self._tokens_per_request
        else:
            tokens = len(batch) * self._tokens_per_input
        return _OrderedEmbeddingResponse(start, len(batch), tokens)


class _OrderedEmbeddingResponse:
    def __init__(self, start_index: int, count: int, prompt_tokens: int) -> None:
        self._start_index = start_index
        self._count = count
        self._prompt_tokens = prompt_tokens

    def json(self) -> dict[str, object]:
        return {
            "data": [
                {
                    "embedding": [float(self._start_index + offset)] + [0.0] * 1535,
                    "index": offset,
                }
                for offset in range(self._count)
            ],
            "usage": {
                "prompt_tokens": self._prompt_tokens,
                "total_tokens": self._prompt_tokens,
            },
        }

    @property
    def status_code(self) -> int:
        return 200
