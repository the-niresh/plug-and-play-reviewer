"""Failing tests for Task 35.A5: refuse a review before spending, not after.

The test that matters counts model calls with a fake: an estimate over the cap must
mean the fake's complete_json is never invoked, not merely that some check ran.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pr_reviewer.contracts.review_context import ContextBudget
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
from pr_reviewer.reviewer.diff_budget import pack_diff

SMALL_PATCH = "@@ -1,1 +1,1 @@\n-old\n+new\n"
KNOWN_MODEL = "claude-3-5-haiku-latest"


def _snapshot(files: list[PullRequestFile]) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=12,
        base_sha="a" * 40,
        head_sha="b" * 40,
        title="Add widget",
        body="please review",
        files=files,
    )


def _file(path: str = "app.py", patch: str = SMALL_PATCH) -> PullRequestFile:
    return PullRequestFile.model_validate({"path": path, "status": "modified", "patch": patch})


def _packed(files: list[PullRequestFile]) -> Any:
    return pack_diff(_snapshot(files), ContextBudget(tokens=10_000), lambda _text: 1)


def _counting_model() -> Any:
    from pr_reviewer.models.provider import ModelResponse

    class CountingModel:
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

    return CountingModel()


def test_an_estimate_over_the_cost_cap_never_reaches_the_model_call() -> None:
    from pr_reviewer.reliability.budget import BudgetDenied, BudgetLimit
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    files = [_file()]
    model = _counting_model()
    tiny_budget = BudgetLimit(max_tokens=1_000_000, max_cost_usd=Decimal("0.00000001"))

    try:
        review_pull_request(
            _snapshot(files),
            _packed(files),
            [],
            model,
            model_name=KNOWN_MODEL,
            budget=tiny_budget,
        )
        raised = None
    except BudgetDenied as exc:
        raised = exc

    assert model.calls == []
    assert raised is not None
    assert raised.reason == "insufficient"


def test_an_estimate_over_the_token_cap_never_reaches_the_model_call() -> None:
    from pr_reviewer.reliability.budget import BudgetDenied, BudgetLimit
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    files = [_file()]
    model = _counting_model()
    tiny_budget = BudgetLimit(max_tokens=1, max_cost_usd=Decimal("10"))

    try:
        review_pull_request(
            _snapshot(files),
            _packed(files),
            [],
            model,
            model_name=KNOWN_MODEL,
            budget=tiny_budget,
        )
        raised = None
    except BudgetDenied as exc:
        raised = exc

    assert model.calls == []
    assert raised is not None
    assert raised.reason == "insufficient"


def test_an_unset_budget_denies_before_any_model_call() -> None:
    from pr_reviewer.reliability.budget import BudgetDenied, BudgetLimit
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    files = [_file()]
    model = _counting_model()
    unset_budget = BudgetLimit(max_tokens=None, max_cost_usd=None)

    try:
        review_pull_request(
            _snapshot(files),
            _packed(files),
            [],
            model,
            model_name=KNOWN_MODEL,
            budget=unset_budget,
        )
        raised = None
    except BudgetDenied as exc:
        raised = exc

    assert model.calls == []
    assert raised is not None
    assert raised.reason == "unset"


def test_an_estimate_within_the_cap_reaches_the_model_call() -> None:
    from pr_reviewer.reliability.budget import BudgetLimit
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    files = [_file()]
    model = _counting_model()
    generous_budget = BudgetLimit(max_tokens=1_000_000, max_cost_usd=Decimal("10"))

    review_pull_request(
        _snapshot(files),
        _packed(files),
        [],
        model,
        model_name=KNOWN_MODEL,
        budget=generous_budget,
    )

    assert len(model.calls) == 1


def test_no_budget_argument_preserves_the_existing_unbudgeted_behavior() -> None:
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    files = [_file()]
    model = _counting_model()

    review_pull_request(_snapshot(files), _packed(files), [], model, model_name=KNOWN_MODEL)

    assert len(model.calls) == 1


def test_require_within_budget_raises_insufficient_when_the_estimate_exceeds_the_cap() -> None:
    from pr_reviewer.reliability.budget import (
        BudgetDenied,
        BudgetLimit,
        CostEstimate,
        require_within_budget,
    )

    limit = BudgetLimit(max_tokens=100, max_cost_usd=Decimal("0.01"))
    estimate = CostEstimate(input_tokens=90, output_tokens=90, cost_usd=Decimal("0.001"))

    try:
        require_within_budget(limit, estimate)
        raised = None
    except BudgetDenied as exc:
        raised = exc

    assert raised is not None
    assert raised.reason == "insufficient"


def test_require_within_budget_returns_the_limit_when_the_estimate_fits() -> None:
    from pr_reviewer.reliability.budget import BudgetLimit, CostEstimate, require_within_budget

    limit = BudgetLimit(max_tokens=1000, max_cost_usd=Decimal("1"))
    estimate = CostEstimate(input_tokens=10, output_tokens=10, cost_usd=Decimal("0.001"))

    assert require_within_budget(limit, estimate) is limit
