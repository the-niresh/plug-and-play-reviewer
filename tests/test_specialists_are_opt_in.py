"""Specialist reviewers are off until the user turns them on per repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.contracts.github import RepositoryIdentity
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot

BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SMALL_PATCH = "@@ -1,1 +1,1 @@\n-old\n+new\n"


def _snapshot(files: list[PullRequestFile]) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=12,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        title="Add widget",
        body="please review",
        files=files,
    )


def _file(path: str, patch: str | None = SMALL_PATCH, **kwargs: object) -> PullRequestFile:
    fields: dict[str, object] = {"path": path, "status": "modified", "patch": patch}
    fields.update(kwargs)
    return PullRequestFile.model_validate(fields)


def _packed(files: list[PullRequestFile]) -> Any:
    from pr_reviewer.contracts.review_context import ContextBudget
    from pr_reviewer.reviewer.diff_budget import pack_diff

    return pack_diff(_snapshot(files), ContextBudget(tokens=10_000), lambda _text: 1)


def _candidate(concern: str, **overrides: object) -> FindingCandidate:
    fields: dict[str, object] = {
        "concern": concern,
        "severity": "high",
        "category": f"{concern}-issue",
        "file_path": "app.py",
        "line_start": 1,
        "line_end": 1,
        "title": f"{concern} finding",
        "rationale": f"{concern} rationale",
        "evidence": ["app.py:1"],
        "confidence": 0.8,
    }
    fields.update(overrides)
    return FindingCandidate.model_validate(fields)


def _reviewer(concern: str, *, calls: dict[str, int] | None = None) -> Any:
    def review(_snapshot: Any, _packed: Any, _context: Any) -> list[FindingCandidate]:
        if calls is not None:
            calls[concern] = calls.get(concern, 0) + 1
        return [_candidate(concern)]

    return review


def test_repository_with_no_specialists_runs_none(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.specialists import (
        get_enabled_specialists,
        run_specialists,
    )
    from pr_reviewer.security.instruction_sources import default_review_policy

    config_path = tmp_path / "repo_config.json"
    assert get_enabled_specialists(config_path, 101) == ()

    calls: dict[str, int] = {}
    reviewers = {
        "security": _reviewer("security", calls=calls),
        "correctness": _reviewer("correctness", calls=calls),
    }
    result = run_specialists(
        _snapshot([_file("app.py")]),
        _packed([_file("app.py")]),
        [],
        reviewers,
        policy=default_review_policy(),
        enabled_concerns=get_enabled_specialists(config_path, 101),
    )
    assert result.candidates == ()
    assert calls == {}


def test_repository_with_one_specialist_runs_exactly_that_one(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.specialists import (
        get_enabled_specialists,
        run_specialists,
        set_enabled_specialists,
    )
    from pr_reviewer.security.instruction_sources import default_review_policy

    config_path = tmp_path / "repo_config.json"
    set_enabled_specialists(config_path, 202, ("security",))

    enabled = get_enabled_specialists(config_path, 202)
    assert enabled == ("security",)

    calls: dict[str, int] = {}
    reviewers = {
        "security": _reviewer("security", calls=calls),
        "correctness": _reviewer("correctness", calls=calls),
        "tests": _reviewer("tests", calls=calls),
        "docs": _reviewer("docs", calls=calls),
    }
    result = run_specialists(
        _snapshot([_file("app.py")]),
        _packed([_file("app.py")]),
        [],
        reviewers,
        policy=default_review_policy(),
        enabled_concerns=enabled,
    )
    assert calls == {"security": 1}
    assert {item.concern for item in result.candidates} == {"security"}


def test_enabling_a_specialist_for_repo_a_does_not_enable_it_for_repo_b(
    tmp_path: Path,
) -> None:
    from pr_reviewer.reviewer.specialists import (
        get_enabled_specialists,
        set_enabled_specialists,
    )

    config_path = tmp_path / "repo_config.json"
    set_enabled_specialists(config_path, 301, ("docs",))

    assert get_enabled_specialists(config_path, 301) == ("docs",)
    assert get_enabled_specialists(config_path, 302) == ()


def test_onboarding_surfaces_specialist_cost_when_one_is_enabled(tmp_path: Path) -> None:
    from pr_reviewer.tui.onboarding import OnboardingPanel

    panel = OnboardingPanel(
        repositories=("acme/alpha",),
        config_dir=tmp_path,
        repository_ids={"acme/alpha": 401},
        repo_config_path=tmp_path / "repo_config.json",
    )
    assert panel.try_advance({"provider": "openai"})
    assert panel.try_advance({"key": "sk-test"})
    assert panel.try_advance({"project_description": "Widget service."})
    assert panel.try_advance({"repository": "acme/alpha", "index_requested": True})
    assert panel.try_advance({"signed_in": True, "selected_repository_ids": [401]})
    assert panel.try_advance({"run_location": "local"})

    assert panel.in_specialist_selection
    notice = panel.toggle_specialist("security")
    assert "$" in notice
    assert "per review" in notice.lower()
    assert panel.finish_specialist_selection()

    from pr_reviewer.reviewer.specialists import get_enabled_specialists

    assert get_enabled_specialists(tmp_path / "repo_config.json", 401) == ("security",)


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
                provider="openai",
                model=request.model,
                prompt_name=request.prompt_name,
                prompt_version=request.prompt_version,
                input_tokens=1,
                output_tokens=1,
                cost_usd="0",
                latency_ms=1,
            )

    return CapturingModel()


def _snapshot_for_repo(github_repository_id: int) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=12,
        base_sha=BASE_SHA,
        head_sha=HEAD_SHA,
        title="Add widget",
        body="please review",
        files=[_file("app.py")],
        identity=RepositoryIdentity(
            installation_id=1,
            repository_id=github_repository_id,
            owner="acme",
            name="widgets",
        ),
    )


def _start_backend_review(
    monkeypatch: Any,
    *,
    repo_config_path: Path,
    github_repository_id: int,
    model: Any,
) -> Any:
    from pr_reviewer.agent_surfaces import backend
    from pr_reviewer.agent_surfaces.core import AgentReviewRequest

    def fake_fetch_pull_request(*args: Any, **kwargs: Any) -> Any:
        del args, kwargs
        return _snapshot_for_repo(github_repository_id)

    def fake_pack_diff(snapshot: Any, budget: Any, count_tokens: Any) -> Any:
        del count_tokens
        del budget
        return _packed(snapshot.files)

    monkeypatch.setenv(backend.GITHUB_TOKEN_ENV, "gh-token")
    monkeypatch.setattr(backend, "resolve_model_provider", lambda: ("openai", model))
    monkeypatch.setattr(backend, "fetch_pull_request", fake_fetch_pull_request)
    monkeypatch.setattr(backend, "pack_diff", fake_pack_diff)
    return backend.LiveAgentReviewBackend(
        retrieval=backend.NullRetrievalExecutor(),
        repo_config_path=repo_config_path,
    ).start_review(
        AgentReviewRequest(owner="acme", repository="widgets", pull_request=12)
    )


def _specialist_prompt_names(model: Any) -> list[str]:
    from pr_reviewer.reviewer.specialists import SPECIALIST_CONCERNS

    return [
        call.prompt_name
        for call in model.calls
        if call.prompt_name in SPECIALIST_CONCERNS
        or str(call.prompt_name).startswith("specialist_")
    ]


def test_live_review_with_one_enabled_specialist_runs_exactly_that_one(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from pr_reviewer.reviewer.specialists import set_enabled_specialists

    config_path = tmp_path / "repo_config.json"
    set_enabled_specialists(config_path, 202, ("security",))
    model = _capturing_model()
    review = _start_backend_review(
        monkeypatch,
        repo_config_path=config_path,
        github_repository_id=202,
        model=model,
    )
    assert review.status == "complete"
    names = _specialist_prompt_names(model)
    assert names == ["specialist_security"]


def test_live_review_with_no_specialists_enabled_runs_none(
    tmp_path: Path, monkeypatch: Any
) -> None:
    model = _capturing_model()
    review = _start_backend_review(
        monkeypatch,
        repo_config_path=tmp_path / "repo_config.json",
        github_repository_id=101,
        model=model,
    )
    assert review.status == "complete"
    assert _specialist_prompt_names(model) == []


def test_live_review_specialist_for_repo_a_does_not_run_for_repo_b(
    tmp_path: Path, monkeypatch: Any
) -> None:
    from pr_reviewer.reviewer.specialists import set_enabled_specialists

    config_path = tmp_path / "repo_config.json"
    set_enabled_specialists(config_path, 301, ("docs",))
    model = _capturing_model()
    review = _start_backend_review(
        monkeypatch,
        repo_config_path=config_path,
        github_repository_id=302,
        model=model,
    )
    assert review.status == "complete"
    assert _specialist_prompt_names(model) == []
