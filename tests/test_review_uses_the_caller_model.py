from __future__ import annotations

from typing import Any

from test_review_pull_request import _file, _packed, _snapshot


def test_review_pull_request_uses_the_caller_model() -> None:
    from pr_reviewer.models.provider import ModelResponse
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

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

    model = CapturingModel()

    review_pull_request(
        _snapshot([_file("app.py")]),
        _packed([_file("app.py")]),
        [],
        model,
        model_name="claude-3-5-haiku-latest",
    )

    assert model.calls[0].model == "claude-3-5-haiku-latest"


def test_live_agent_backend_uses_the_requested_model_and_its_budget(monkeypatch: Any) -> None:
    from pr_reviewer.agent_surfaces import backend
    from pr_reviewer.agent_surfaces.core import AgentReviewRequest
    from pr_reviewer.contracts.review_context import ContextBudget
    from pr_reviewer.github.pull_request import PullRequestSnapshot

    seen: dict[str, Any] = {}

    class FakeProvider:
        pass

    def fake_fetch_pull_request(*args: Any, **kwargs: Any) -> PullRequestSnapshot:
        del args, kwargs
        return _snapshot([_file("app.py")])

    def fake_pack_diff(snapshot: Any, budget: ContextBudget, count_tokens: Any) -> Any:
        del count_tokens
        seen["budget"] = budget
        return _packed(snapshot.files)

    def fake_review_pull_request(*args: Any, **kwargs: Any) -> Any:
        from pr_reviewer.contracts.review_context import ReviewOutcome

        seen["model_name"] = kwargs["model_name"]
        return ReviewOutcome(
            candidates=(),
            packing_strategy_version=args[1].packing_strategy_version,
            covers_all_changed_files=True,
            omitted_files=(),
        )

    monkeypatch.setenv(backend.GITHUB_TOKEN_ENV, "gh-token")
    monkeypatch.setattr(backend, "resolve_model_provider", lambda: ("openai", FakeProvider()))
    monkeypatch.setattr(backend, "fetch_pull_request", fake_fetch_pull_request)
    monkeypatch.setattr(backend, "pack_diff", fake_pack_diff)
    monkeypatch.setattr(backend, "review_pull_request", fake_review_pull_request)

    review = backend.LiveAgentReviewBackend().start_review(
        AgentReviewRequest(
            owner="acme",
            repository="widgets",
            pull_request=12,
            model="gpt-4.1",
        )
    )

    assert review.status == "complete"
    assert seen["model_name"] == "gpt-4.1"
    assert seen["budget"].tokens > 128_000
