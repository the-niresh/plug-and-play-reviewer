"""Failing tests for Task 35.A6: should_explore's gate, and the explorer's hard caps.

The tool-call-cap test matters most: a fake model that never returns "finish" must
still stop, and the model must never be called more times than the cap allows. Counted
on the fake, not inferred from a mock assertion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _model_response(parsed: dict[str, Any], model_name: str = "claude-3-5-haiku-latest") -> Any:
    from pr_reviewer.models.provider import ModelResponse

    return ModelResponse(
        parsed=parsed,
        output_hash="a" * 64,
        provider_request_id=None,
        provider="anthropic",
        model=model_name,
        prompt_name="bounded_explorer",
        prompt_version="v1",
        input_tokens=1,
        output_tokens=1,
        cost_usd="0",
        latency_ms=1,
    )


class _ScriptedModel:
    """Returns responses.pop(0) each call; asserting on .calls proves the count."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls: list[Any] = []

    def complete_json(self, request: Any) -> Any:
        self.calls.append(request)
        parsed = self._responses.pop(0) if self._responses else {"tool": "finish"}
        return _model_response(parsed, request.model)


class _RepeatingModel:
    """Always returns the same action. Used to prove a hard cap, not a lucky finish."""

    def __init__(self, parsed: dict[str, Any]) -> None:
        self._parsed = parsed
        self.calls: list[Any] = []

    def complete_json(self, request: Any) -> Any:
        self.calls.append(request)
        return _model_response(self._parsed, request.model)


def _clone_root(tmp_path: Path) -> Path:
    root = tmp_path / "clone"
    root.mkdir()
    (root / "app.py").write_text("one\ntwo\nthree\n" * 50)
    return root


def test_should_explore_fires_on_low_retrieval_confidence() -> None:
    from pr_reviewer.reviewer.explore import should_explore

    assert should_explore(retrieval_confidence=0.1, sensitivity=0.1) is True


def test_should_explore_fires_on_high_sensitivity() -> None:
    from pr_reviewer.reviewer.explore import should_explore

    assert should_explore(retrieval_confidence=0.9, sensitivity=0.95) is True


def test_should_explore_does_not_fire_by_default_on_an_ordinary_change() -> None:
    from pr_reviewer.reviewer.explore import should_explore

    assert should_explore(retrieval_confidence=0.9, sensitivity=0.1) is False


def test_should_explore_has_no_internal_caller() -> None:
    """'Never by default' means nothing in this module calls the gate for you.

    A caller must read should_explore's answer and choose to run the explorer; this
    scans the module's own source (not test code) so a future change that adds a
    silent auto-call inside explore.py itself is caught, not just a hand test that
    happens not to trigger one.
    """
    import ast
    import inspect

    import pr_reviewer.reviewer.explore as explore_module

    tree = ast.parse(inspect.getsource(explore_module))
    call_names = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "should_explore" not in call_names


def test_bounded_explorer_stops_when_the_model_finishes_immediately(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.explore import run_bounded_explorer

    model = _ScriptedModel([{"tool": "finish", "summary": "nothing more to see"}])

    outcome = run_bounded_explorer(
        _clone_root(tmp_path), model, model_name="claude-3-5-haiku-latest", task_prompt="look"
    )

    assert outcome.stopped_reason == "finished"
    assert outcome.tool_calls_used == 0
    assert len(model.calls) == 1


def test_bounded_explorer_runs_a_real_tool_call_before_finishing(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.explore import run_bounded_explorer

    model = _ScriptedModel(
        [
            {"tool": "read_file", "path": "app.py", "start": 1, "end": 2},
            {"tool": "finish"},
        ]
    )

    outcome = run_bounded_explorer(
        _clone_root(tmp_path), model, model_name="claude-3-5-haiku-latest", task_prompt="look"
    )

    assert outcome.stopped_reason == "finished"
    assert outcome.tool_calls_used == 1
    assert len(outcome.context_items) == 1
    assert "one" in outcome.context_items[0].content


def test_bounded_explorer_never_exceeds_the_tool_call_cap(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.explore import ExplorationBudget, run_bounded_explorer

    model = _RepeatingModel({"tool": "read_file", "path": "app.py", "start": 1, "end": 1})
    budget = ExplorationBudget(max_tool_calls=3, max_tokens=1_000_000)

    outcome = run_bounded_explorer(
        _clone_root(tmp_path),
        model,
        model_name="claude-3-5-haiku-latest",
        task_prompt="look",
        budget=budget,
    )

    assert outcome.stopped_reason == "tool_call_cap"
    assert outcome.tool_calls_used == 3
    assert len(model.calls) == 3


def test_bounded_explorer_stops_on_the_token_cap_before_the_call_cap(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.explore import ExplorationBudget, run_bounded_explorer

    model = _RepeatingModel({"tool": "read_file", "path": "app.py", "start": 1, "end": 50})
    budget = ExplorationBudget(max_tool_calls=100, max_tokens=1)

    outcome = run_bounded_explorer(
        _clone_root(tmp_path),
        model,
        model_name="claude-3-5-haiku-latest",
        task_prompt="look",
        budget=budget,
    )

    assert outcome.stopped_reason == "token_cap"
    assert outcome.tool_calls_used == 1
    assert len(model.calls) == 1


def test_bounded_explorer_stops_cleanly_on_a_malformed_action(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.explore import run_bounded_explorer

    model = _ScriptedModel([{"tool": "shell", "command": "rm -rf /"}])

    outcome = run_bounded_explorer(
        _clone_root(tmp_path), model, model_name="claude-3-5-haiku-latest", task_prompt="look"
    )

    assert outcome.stopped_reason == "malformed_action"
    assert outcome.tool_calls_used == 0
    assert len(model.calls) == 1


def test_explore_pull_request_cleans_up_the_clone_after_running(tmp_path: Path) -> None:
    from pr_reviewer.contracts.github import RepositoryIdentity
    from pr_reviewer.reviewer.explore import explore_pull_request

    seen: list[Path] = []

    class _FakeFetcher:
        def materialize(
            self, identity: object, head_sha: str, work_dir: Path, paths: list[str]
        ) -> Path:
            del identity, head_sha, paths
            (work_dir / "app.py").write_text("one\ntwo\n")
            seen.append(work_dir)
            return work_dir.resolve()

    model = _ScriptedModel([{"tool": "finish"}])
    identity = RepositoryIdentity(installation_id=1, repository_id=2, owner="acme", name="w")

    outcome = explore_pull_request(
        identity,
        "h" * 40,
        model,
        model_name="claude-3-5-haiku-latest",
        task_prompt="look",
        fetcher=_FakeFetcher(),
    )

    assert outcome.stopped_reason == "finished"
    assert len(seen) == 1
    assert not seen[0].exists()
