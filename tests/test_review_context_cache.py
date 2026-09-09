"""Incremental re-review skips unchanged work and budgets prior findings."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from test_review_pull_request import _draft_dict, _fake_model, _file

from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
from pr_reviewer.reliability.budget import BudgetLimit

BASE_SHA = "a" * 40
HEAD_ONE = "b" * 40
HEAD_TWO = "c" * 40
INSTALLATION_ID = 11
REPOSITORY_ID = 22
PR_NUMBER = 12
KEEP_PATCH = "@@ -1,1 +1,1 @@\n-keep-old\n+keep-new\n"
CHANGE_PATCH_ONE = "@@ -1,1 +1,1 @@\n-change-old\n+change-one\n"
CHANGE_PATCH_TWO = "@@ -1,1 +1,1 @@\n-change-one\n+change-two\n"


def _snapshot(
    files: list[PullRequestFile],
    *,
    head_sha: str = HEAD_ONE,
    number: int = PR_NUMBER,
) -> PullRequestSnapshot:
    return PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=number,
        base_sha=BASE_SHA,
        head_sha=head_sha,
        title="Add widget",
        body="please review",
        files=files,
    )


def _candidate(**overrides: Any) -> Any:
    from pr_reviewer.contracts.finding_candidate import FindingCandidate

    fields: dict[str, Any] = {
        "concern": "correctness",
        "severity": "high",
        "category": "null-check",
        "file_path": "keep.py",
        "line_start": 1,
        "line_end": 1,
        "title": "Missing null check",
        "rationale": "value can be None",
        "evidence": ["keep.py:1"],
        "confidence": 0.8,
    }
    fields.update(overrides)
    return FindingCandidate.model_validate(fields)


def test_unchanged_file_is_not_sent_to_the_model() -> None:
    from pr_reviewer.reviewer.incremental import incremental_review_pull_request
    from pr_reviewer.reviewer.review_cache import MemoryReviewCache

    cache = MemoryReviewCache()
    first_files = [
        _file("keep.py", KEEP_PATCH),
        _file("change.py", CHANGE_PATCH_ONE),
    ]
    first_model = _fake_model({"findings": [_draft_dict(file_path="keep.py")]})
    incremental_review_pull_request(
        _snapshot(first_files, head_sha=HEAD_ONE),
        first_model,
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )

    second_model = _fake_model({"findings": [_draft_dict(file_path="change.py")]})
    incremental_review_pull_request(
        _snapshot(
            [_file("keep.py", KEEP_PATCH), _file("change.py", CHANGE_PATCH_TWO)],
            head_sha=HEAD_TWO,
        ),
        second_model,
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    generate = [call for call in second_model.calls if call.schema_name == "ReviewFindingsDraft"]
    assert generate
    assert "keep.py" not in generate[0].prompt_content
    assert "change.py" in generate[0].prompt_content


def test_changed_hunk_is_sent_to_the_model() -> None:
    from pr_reviewer.reviewer.incremental import incremental_review_pull_request
    from pr_reviewer.reviewer.review_cache import MemoryReviewCache

    cache = MemoryReviewCache()
    incremental_review_pull_request(
        _snapshot([_file("change.py", CHANGE_PATCH_ONE)], head_sha=HEAD_ONE),
        _fake_model({"findings": []}),
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    second = _fake_model({"findings": [_draft_dict(file_path="change.py")]})
    incremental_review_pull_request(
        _snapshot([_file("change.py", CHANGE_PATCH_TWO)], head_sha=HEAD_TWO),
        second,
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    generate = [call for call in second.calls if call.schema_name == "ReviewFindingsDraft"]
    assert generate
    assert "change-two" in generate[0].prompt_content


def test_prior_finding_on_untouched_file_is_carried_forward() -> None:
    from pr_reviewer.reviewer.incremental import incremental_review_pull_request
    from pr_reviewer.reviewer.review_cache import MemoryReviewCache

    cache = MemoryReviewCache()
    incremental_review_pull_request(
        _snapshot(
            [_file("keep.py", KEEP_PATCH), _file("change.py", CHANGE_PATCH_ONE)],
            head_sha=HEAD_ONE,
        ),
        _fake_model({"findings": [_draft_dict(file_path="keep.py")]}),
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    outcome = incremental_review_pull_request(
        _snapshot(
            [_file("keep.py", KEEP_PATCH), _file("change.py", CHANGE_PATCH_TWO)],
            head_sha=HEAD_TWO,
        ),
        _fake_model({"findings": []}),
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    assert any(item.file_path == "keep.py" for item in outcome.candidates)


def test_prior_finding_overlapping_changed_lines_is_rechecked_not_carried() -> None:
    from pr_reviewer.reviewer.incremental import incremental_review_pull_request
    from pr_reviewer.reviewer.review_cache import MemoryReviewCache

    cache = MemoryReviewCache()
    incremental_review_pull_request(
        _snapshot([_file("change.py", CHANGE_PATCH_ONE)], head_sha=HEAD_ONE),
        _fake_model({"findings": [_draft_dict(file_path="change.py")]}),
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    second = _fake_model({"findings": []})
    outcome = incremental_review_pull_request(
        _snapshot([_file("change.py", CHANGE_PATCH_TWO)], head_sha=HEAD_TWO),
        second,
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    generate = [call for call in second.calls if call.schema_name == "ReviewFindingsDraft"]
    assert generate
    assert "prior_finding" in generate[0].prompt_content
    assert "Missing null check" in generate[0].prompt_content
    assert all(item.file_path != "change.py" for item in outcome.candidates)


def test_prior_findings_in_the_prompt_stay_under_budget() -> None:
    from pr_reviewer.reviewer.incremental import (
        PRIOR_FINDING_TOKEN_BUDGET,
        incremental_review_pull_request,
    )
    from pr_reviewer.reviewer.review_cache import MemoryReviewCache, seed_cache

    cache = MemoryReviewCache()
    seed_cache(
        cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
        pull_request_number=PR_NUMBER,
        head_sha=HEAD_ONE,
        files=[_file("change.py", CHANGE_PATCH_ONE)],
        findings=[
            _candidate(
                file_path="change.py",
                title=f"finding-{index}",
                rationale="x" * 400,
                evidence=[f"change.py:{index}"],
            )
            for index in range(20)
        ],
    )
    model = _fake_model({"findings": []})
    incremental_review_pull_request(
        _snapshot([_file("change.py", CHANGE_PATCH_TWO)], head_sha=HEAD_TWO),
        model,
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    generate = [call for call in model.calls if call.schema_name == "ReviewFindingsDraft"]
    assert generate
    prior = generate[0].prompt_content.split("name: prior_finding")
    prior_text = "name: prior_finding".join(prior[1:]) if len(prior) > 1 else ""
    assert max(1, len(prior_text) // 4) <= PRIOR_FINDING_TOKEN_BUDGET


def test_hosted_schema_has_no_review_cache_table() -> None:
    from pr_reviewer.db.client import connection

    with connection() as conn:
        rows = conn.execute(
            """
            select table_name from information_schema.tables
            where table_schema = 'public' and table_name like '%review_cache%'
            """
        ).fetchall()
    assert rows == []


def test_review_cache_round_trips_on_the_local_store(tmp_path: Any) -> None:
    from pr_reviewer.local_store.sqlite import open_local_store
    from pr_reviewer.reviewer.review_cache import LocalReviewCache, record_from_review

    store = open_local_store(tmp_path / "local_state.sqlite3")
    cache = LocalReviewCache(store)
    record = record_from_review(
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
        snapshot=_snapshot([_file("keep.py", KEEP_PATCH)], head_sha=HEAD_ONE),
        findings=(_candidate(),),
        cost_usd=Decimal("0.01"),
    )
    cache.save(record)
    loaded = cache.load_previous(INSTALLATION_ID, REPOSITORY_ID, PR_NUMBER)
    assert loaded is not None
    assert loaded.head_sha == HEAD_ONE
    assert "keep.py" in loaded.reviewed_files
    assert loaded.findings[0].title == "Missing null check"
    store.close()


def test_untouched_file_is_reviewed_when_retrieval_points_at_it() -> None:
    from pr_reviewer.reviewer.incremental import incremental_review_pull_request
    from pr_reviewer.reviewer.review_cache import MemoryReviewCache

    cache = MemoryReviewCache()
    incremental_review_pull_request(
        _snapshot(
            [_file("keep.py", KEEP_PATCH), _file("change.py", CHANGE_PATCH_ONE)],
            head_sha=HEAD_ONE,
        ),
        _fake_model({"findings": []}),
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    second = _fake_model({"findings": []})
    incremental_review_pull_request(
        _snapshot(
            [_file("keep.py", KEEP_PATCH), _file("change.py", CHANGE_PATCH_TWO)],
            head_sha=HEAD_TWO,
        ),
        second,
        model_name="gpt-4o-mini",
        cache=cache,
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
        related_paths=frozenset({"keep.py"}),
    )
    generate = [call for call in second.calls if call.schema_name == "ReviewFindingsDraft"]
    assert generate
    assert "keep.py" in generate[0].prompt_content


def test_over_budget_estimate_stops_before_a_model_call() -> None:
    import pytest

    from pr_reviewer.reliability.budget import BudgetDenied
    from pr_reviewer.reviewer.incremental import incremental_review_pull_request
    from pr_reviewer.reviewer.review_cache import MemoryReviewCache

    model = _fake_model({"findings": []})
    with pytest.raises(BudgetDenied):
        incremental_review_pull_request(
            _snapshot([_file("change.py", CHANGE_PATCH_ONE)], head_sha=HEAD_ONE),
            model,
            model_name="gpt-4o-mini",
            cache=MemoryReviewCache(),
            installation_id=INSTALLATION_ID,
            repository_id=REPOSITORY_ID,
            budget=BudgetLimit(max_tokens=1, max_cost_usd=Decimal("0.000001")),
        )
    assert model.calls == []


def test_incremental_review_does_not_embed() -> None:
    import ast
    from pathlib import Path

    source = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "pr_reviewer"
        / "reviewer"
        / "incremental.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "embed" not in node.module
            assert not node.module.startswith("pr_reviewer.models")
