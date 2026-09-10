"""Failing tests for Task 35.A4: triage keeps trivial pull requests off the expensive path.

Lockfiles, generated files, docs-only changes and dependency-version bumps do not need a
model call. These tests count calls with a fake model, because asserting that a triage
function was merely called proves nothing about whether the expensive call happened.
"""

from __future__ import annotations

from typing import Any

from pr_reviewer.contracts.review_context import ContextBudget
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
from pr_reviewer.reviewer.diff_budget import pack_diff

LOCKFILE_PATCH = '@@ -1,3 +1,3 @@\n {\n-  "a": 1\n+  "a": 2\n }\n'
DOCS_PATCH = "@@ -1,2 +1,2 @@\n-Old line.\n+New line.\n"
DEPENDENCY_BUMP_PATCH = (
    '@@ -1,3 +1,3 @@\n {\n-  "version": "1.0.0",\n+  "version": "1.0.1",\n }\n'
)
REQUIREMENTS_BUMP_PATCH = "@@ -1 +1 @@\n-requests==2.28.0\n+requests==2.28.1\n"
REAL_CODE_PATCH = "@@ -1,2 +1,2 @@\n-def foo():\n-    return 1\n+def foo():\n+    return 2\n"


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


def _snapshot(files: list[PullRequestFile]) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=12,
        base_sha="b" * 40,
        head_sha="h" * 40,
        title="Bump things",
        body="",
        files=files,
    )


def _packed(files: list[PullRequestFile]) -> Any:
    return pack_diff(_snapshot(files), ContextBudget(tokens=10_000), lambda _text: 1)


def _file(path: str, patch: str) -> PullRequestFile:
    return PullRequestFile.model_validate(
        {"path": path, "status": "modified", "patch": patch}
    )


def test_lockfile_only_pr_never_reaches_the_expensive_call() -> None:
    from pr_reviewer.reviewer.triage import review_with_triage

    files = [_file("package-lock.json", LOCKFILE_PATCH)]
    model = _counting_model()

    result = review_with_triage(
        _snapshot(files), _packed(files), [], model, model_name="claude-3-5-haiku-latest"
    )

    assert model.calls == []
    assert result.decision.skip_expensive_review is True
    assert result.outcome.candidates == ()


def test_docs_only_pr_never_reaches_the_expensive_call() -> None:
    from pr_reviewer.reviewer.triage import review_with_triage

    files = [_file("docs/guide.md", DOCS_PATCH), _file("README.md", DOCS_PATCH)]
    model = _counting_model()

    result = review_with_triage(
        _snapshot(files), _packed(files), [], model, model_name="claude-3-5-haiku-latest"
    )

    assert model.calls == []
    assert result.decision.skip_expensive_review is True


def test_dependency_version_bump_only_pr_never_reaches_the_expensive_call() -> None:
    from pr_reviewer.reviewer.triage import review_with_triage

    files = [
        _file("package.json", DEPENDENCY_BUMP_PATCH),
        _file("requirements.txt", REQUIREMENTS_BUMP_PATCH),
    ]
    model = _counting_model()

    result = review_with_triage(
        _snapshot(files), _packed(files), [], model, model_name="claude-3-5-haiku-latest"
    )

    assert model.calls == []
    assert result.decision.skip_expensive_review is True


def test_a_real_code_change_still_reaches_the_expensive_call() -> None:
    from pr_reviewer.reviewer.triage import review_with_triage

    files = [_file("app.py", REAL_CODE_PATCH)]
    model = _counting_model()

    result = review_with_triage(
        _snapshot(files), _packed(files), [], model, model_name="claude-3-5-haiku-latest"
    )

    assert len(model.calls) == 1
    assert result.decision.skip_expensive_review is False


def test_one_real_file_among_trivial_ones_still_reaches_the_expensive_call() -> None:
    from pr_reviewer.reviewer.triage import review_with_triage

    files = [
        _file("package-lock.json", LOCKFILE_PATCH),
        _file("app.py", REAL_CODE_PATCH),
    ]
    model = _counting_model()

    result = review_with_triage(
        _snapshot(files), _packed(files), [], model, model_name="claude-3-5-haiku-latest"
    )

    assert len(model.calls) == 1
    assert result.decision.skip_expensive_review is False


def test_the_decision_records_the_reason_per_file_not_just_a_bare_skip() -> None:
    from pr_reviewer.contracts.github import OmissionReason
    from pr_reviewer.reviewer.triage import triage_pull_request

    files = [
        _file("package-lock.json", LOCKFILE_PATCH),
        _file("docs/guide.md", DOCS_PATCH),
    ]

    decision = triage_pull_request(_snapshot(files))

    assert decision.skip_expensive_review is True
    assert decision.reason
    assert isinstance(decision.reason, str)
    file_reasons = dict(decision.file_reasons)
    assert file_reasons["package-lock.json"] == OmissionReason.GENERATED
    assert file_reasons["docs/guide.md"] == OmissionReason.IGNORED_PATH


def test_a_silent_skip_is_never_produced_without_a_reason() -> None:
    from pr_reviewer.reviewer.triage import triage_pull_request

    decision = triage_pull_request(_snapshot([]))

    assert decision.skip_expensive_review is True
    assert decision.reason
