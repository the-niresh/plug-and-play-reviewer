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
