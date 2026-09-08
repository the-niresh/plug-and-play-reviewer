"""Failing tests for the diff-only one-agent baseline (master Task 11).

The model is parsed into FindingDraft, which has no system-owned fields. The
reviewer constructs FindingCandidate from that draft. Imports of new modules
stay inside test bodies.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from pr_reviewer.contracts.github import OmissionReason
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot

SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "pr_reviewer"
BASE_SHA = "a" * 40
HEAD_SHA = "b" * 40
SMALL_PATCH = "@@ -1,1 +1,1 @@\n-old\n+new\n"
# Modeled on flask-py-013 (dev): one hunk in src/flask/cli.py. NEW side is 858-863.
CLI_HUNK_PATCH = """\
@@ -858,7 +858,9 @@ class SeparatedPathType(click.Path):
         self, value: t.Any, param: click.Parameter | None, ctx: click.Context | None
     ) -> t.Any:
         items = self.split_envvar_value(value)
-        return [super().convert(item, param, ctx) for item in items]
+        # can't call no-arg super() inside list comprehension until Python 3.12
+        super_convert = super().convert
+        return [super_convert(item, param, ctx) for item in items]
"""
# Same file, two distant hunks. A late-hunk finding must not absorb the early hunk.
TWO_HUNK_PATCH = """\
@@ -286,3 +286,3 @@
 context
-old
+changed early
 more
@@ -603,3 +605,3 @@
 later
-old
+changed late
 more
"""
# Modeled on flask-py-001 (dev): definition hunk, then a later call-site hunk.
BLUEPRINT_DEF_AND_CALL_PATCH = """\
@@ -453,5 +453,6 @@ class Blueprint(Scaffold):
     def register(self, app, options):
         for blueprint, bp_options in self._blueprints:
-            bp_options = bp_options.copy()
+            bp_subdomain = bp_options.get("subdomain")
+            bp_options = bp_options.copy()
             if bp_url_prefix is None:
@@ -598,3 +600,3 @@
 later
-old
+            state = register(app, options)
 more
"""
FORBIDDEN_FIELDS = (
    "id",
    "review_job_id",
    "verified",
    "verification_method",
    "public_safe",
    "status",
)


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


def _draft_dict(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "concern": "correctness",
        "severity": "high",
        "category": "null-check",
        "file_path": "app.py",
        "line_start": 1,
        "line_end": 1,
        "title": "Missing null check",
        "rationale": "value can be None",
        "evidence": ["app.py:1"],
        "confidence": 0.8,
    }
    fields.update(overrides)
    return fields


def _packed(files: list[PullRequestFile]) -> Any:
    from pr_reviewer.contracts.review_context import ContextBudget
    from pr_reviewer.reviewer.diff_budget import pack_diff

    return pack_diff(_snapshot(files), ContextBudget(tokens=10_000), lambda _text: 1)


def _fake_model(parsed: dict[str, Any]) -> Any:
    from pr_reviewer.models.provider import ModelResponse

    first_parsed = parsed

    class FakeModel:
        def __init__(self) -> None:
            self.calls: list[Any] = []

        def complete_json(self, request: Any) -> Any:
            self.calls.append(request)
            if request.schema_name == "FindingReflectionScores":
                raw_candidates = next(
                    item.content
                    for item in request.untrusted_inputs
                    if item.name == "candidate_findings"
                )
                candidate_count = len(json.loads(raw_candidates))
                response_parsed = {
                    "scores": [
                        {"index": index, "score": 1.0, "reason": "accepted"}
                        for index in range(candidate_count)
                    ]
                }
            else:
                response_parsed = first_parsed
            return ModelResponse(
                parsed=response_parsed,
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

    return FakeModel()


def _review(
    packed: Any,
    parsed: dict[str, Any],
    *,
    files: list[PullRequestFile] | None = None,
    context: list[Any] | None = None,
    heartbeat: Any = None,
    model_name: str = "gpt-4o-mini",
) -> tuple[Any, Any]:
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    model = _fake_model(parsed)
    snapshot = _snapshot(files or [_file("app.py")])
    outcome = review_pull_request(
        snapshot,
        packed,
        context if context is not None else [],
        model,
        model_name=model_name,
        heartbeat=heartbeat,
    )
    return outcome, model


def test_finding_draft_has_none_of_the_system_owned_fields() -> None:
    from pr_reviewer.contracts.finding_candidate import FindingDraft, candidate_from_draft

    for field in FORBIDDEN_FIELDS:
        assert field not in FindingDraft.model_fields
        with pytest.raises(ValidationError):
            FindingDraft.model_validate({**_draft_dict(), field: "nope"})

    draft = FindingDraft.model_validate(_draft_dict())
    candidate = candidate_from_draft(draft)
    for field in FORBIDDEN_FIELDS:
        assert field not in type(candidate).model_fields


def test_prototype_pollution_draft_is_security_even_when_model_says_correctness() -> None:
    from pr_reviewer.contracts.finding_candidate import FindingDraft, candidate_from_draft

    draft = FindingDraft.model_validate(
        _draft_dict(
            concern="correctness",
            category="prototype-pollution",
            title="Path key writes through to Object.prototype",
            rationale="A path segment can assign an inherited object key.",
            evidence=['12| curr["__proto__"] = value'],
        )
    )
    candidate = candidate_from_draft(draft)
    assert candidate.concern == "security"


def test_ordinary_correctness_draft_keeps_correctness() -> None:
    from pr_reviewer.contracts.finding_candidate import FindingDraft, candidate_from_draft

    draft = FindingDraft.model_validate(_draft_dict())
    candidate = candidate_from_draft(draft)
    assert candidate.concern == "correctness"


def test_signing_key_order_draft_is_security_even_when_model_says_correctness() -> None:
    # Modeled on flask-py-020 (dev): the live gpt-4.1 draft named a signing key.
    from pr_reviewer.contracts.finding_candidate import FindingDraft, candidate_from_draft

    draft = FindingDraft.model_validate(
        _draft_dict(
            concern="correctness",
            category="incorrect key order",
            title="Signing key selection order was incorrect; now fixed",
            rationale=(
                "The changed lines correct the order of keys so that the current "
                "secret key is in the expected position, ensuring that new sessions "
                "are signed with the current key."
            ),
            evidence=["326|         keys.append(app.secret_key)"],
        )
    )
    candidate = candidate_from_draft(draft)
    assert candidate.concern == "security"


def test_regex_hyphen_draft_stays_correctness_without_a_security_class_name() -> None:
    # Modeled on zod-ts-005 (dev): hyphen / character-class text is not a security class.
    from pr_reviewer.contracts.finding_candidate import FindingDraft, candidate_from_draft

    draft = FindingDraft.model_validate(
        _draft_dict(
            concern="correctness",
            category="regex-escape",
            title="Potential regex escape issue for hyphen",
            rationale=(
                "Hyphens are unescaped in the regex character class which may "
                "lead to unexpected matching behavior."
            ),
            evidence=["595|   [A-Z0-9_'+\\-\\.] [A-Z0-9_+-]"],
        )
    )
    candidate = candidate_from_draft(draft)
    assert candidate.concern == "correctness"


def test_model_output_with_system_owned_fields_is_dropped() -> None:
    packed = _packed([_file("app.py")])
    outcome, _model = _review(
        packed,
        {
            "findings": [
                _draft_dict(verified=True, title="injected verified"),
                _draft_dict(),
            ]
        },
    )
    assert [item.title for item in outcome.candidates] == ["Missing null check"]


def test_malformed_findings_are_dropped() -> None:
    packed = _packed([_file("app.py")])
    outcome, _model = _review(
        packed,
        {"findings": [{"title": "nope"}, _draft_dict()]},
    )
    assert len(outcome.candidates) == 1
    assert outcome.candidates[0].title == "Missing null check"


def test_lines_outside_the_changed_diff_are_dropped() -> None:
    packed = _packed([_file("app.py")])
    outcome, _model = _review(
        packed,
        {"findings": [_draft_dict(line_start=99, line_end=99, title="outside")]},
    )
    assert outcome.candidates == ()


def test_test_file_finding_is_dropped_when_implementation_file_is_packed() -> None:
    packed = _packed([_file("src/flask/cli.py"), _file("tests/test_cli.py")])
    outcome, _model = _review(
        packed,
        {
            "findings": [
                _draft_dict(
                    file_path="tests/test_cli.py",
                    title="test-only finding",
                ),
                _draft_dict(
                    file_path="src/flask/cli.py",
                    title="implementation finding",
                ),
            ]
        },
    )
    assert [item.title for item in outcome.candidates] == ["implementation finding"]
    assert outcome.grounding_rejected_findings == 1


def test_test_file_finding_is_kept_when_only_tests_changed() -> None:
    packed = _packed([_file("tests/test_cli.py")])
    outcome, _model = _review(
        packed,
        {"findings": [_draft_dict(file_path="tests/test_cli.py", title="test-only pr")]},
    )
    assert [item.title for item in outcome.candidates] == ["test-only pr"]


def test_finding_in_later_hunk_lines_expands_to_the_full_new_side_hunk() -> None:
    packed = _packed([_file("src/flask/cli.py", patch=CLI_HUNK_PATCH)])
    outcome, _model = _review(
        packed,
        {
            "findings": [
                _draft_dict(
                    file_path="src/flask/cli.py",
                    line_start=863,
                    line_end=863,
                    title="super in comprehension",
                )
            ]
        },
    )
    assert len(outcome.candidates) == 1
    assert (outcome.candidates[0].line_start, outcome.candidates[0].line_end) == (858, 863)


def test_finding_does_not_expand_into_a_distant_hunk() -> None:
    packed = _packed([_file("src/flask/cli.py", patch=TWO_HUNK_PATCH)])
    outcome, _model = _review(
        packed,
        {
            "findings": [
                _draft_dict(
                    file_path="src/flask/cli.py",
                    line_start=606,
                    line_end=606,
                    title="late hunk only",
                )
            ]
        },
    )
    assert len(outcome.candidates) == 1
    assert (outcome.candidates[0].line_start, outcome.candidates[0].line_end) == (605, 607)


def test_finding_on_a_call_site_moves_to_the_named_definition_hunk() -> None:
    packed = _packed([_file("src/flask/blueprints.py", patch=BLUEPRINT_DEF_AND_CALL_PATCH)])
    outcome, _model = _review(
        packed,
        {
            "findings": [
                _draft_dict(
                    file_path="src/flask/blueprints.py",
                    line_start=601,
                    line_end=601,
                    title="register copies options too late",
                    category="register",
                    rationale="The change in how register is used could drop subdomain.",
                )
            ]
        },
    )
    assert len(outcome.candidates) == 1
    assert (outcome.candidates[0].line_start, outcome.candidates[0].line_end) == (453, 457)


def test_empty_evidence_is_dropped() -> None:
    packed = _packed([_file("app.py")])
    outcome, _model = _review(
        packed,
        {"findings": [_draft_dict(evidence=[], title="no evidence")]},
    )
    assert outcome.candidates == ()


def test_duplicate_candidates_are_collapsed() -> None:
    packed = _packed([_file("app.py")])
    outcome, _model = _review(
        packed,
        {"findings": [_draft_dict(), _draft_dict()]},
    )
    assert len(outcome.candidates) == 1


def test_overlong_output_is_capped() -> None:
    from pr_reviewer.reviewer.review_pull_request import MAX_FINDING_DRAFTS

    packed = _packed([_file("app.py")])
    findings = [_draft_dict(title=f"finding-{index}") for index in range(MAX_FINDING_DRAFTS + 20)]
    outcome, _model = _review(packed, {"findings": findings})
    assert len(outcome.candidates) == MAX_FINDING_DRAFTS


def test_closed_pr_before_the_model_call_records_cancelled_not_a_dead_lease() -> None:
    from pr_reviewer.contracts.runner import LeaseState

    packed = _packed([_file("app.py")])
    events: list[str] = []

    def heartbeat() -> LeaseState:
        events.append("heartbeat")
        return LeaseState(status="cancelled")

    model = _fake_model({"findings": [_draft_dict()]})
    original_complete = model.complete_json

    def complete_json(request: Any) -> Any:
        events.append("model")
        return original_complete(request)

    model.complete_json = complete_json
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    outcome = review_pull_request(
        _snapshot([_file("app.py")]),
        packed,
        [],
        model,
        model_name="gpt-4o-mini",
        heartbeat=heartbeat,
    )
    assert events == ["heartbeat"]
    assert model.calls == []
    assert outcome.cancelled is True
    assert outcome.candidates == ()
    assert outcome.is_complete() is False


def test_active_heartbeat_runs_once_then_the_model_calls() -> None:
    from pr_reviewer.contracts.runner import LeaseState

    packed = _packed([_file("app.py")])
    events: list[str] = []

    def heartbeat() -> LeaseState:
        events.append("heartbeat")
        return LeaseState(status="active")

    model = _fake_model({"findings": [_draft_dict()]})
    original_complete = model.complete_json

    def complete_json(request: Any) -> Any:
        events.append("model")
        return original_complete(request)

    model.complete_json = complete_json
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    review_pull_request(
        _snapshot([_file("app.py")]),
        packed,
        [],
        model,
        model_name="gpt-4o-mini",
        heartbeat=heartbeat,
    )
    assert events == ["heartbeat", "model", "model"]


def test_prompt_states_omitted_files_and_partial_coverage_is_never_complete() -> None:
    from pr_reviewer.contracts.review_context import PACKING_STRATEGY_VERSION

    files = [_file("app.py"), _file("logo.png", patch=None, binary=True)]
    packed = _packed(files)
    outcome, model = _review(
        packed,
        {"findings": [_draft_dict()]},
        files=files,
    )
    assert packed.covers_all_changed_files is False
    assert outcome.covers_all_changed_files is False
    assert outcome.packing_strategy_version == PACKING_STRATEGY_VERSION
    assert outcome.is_complete() is False
    assert any(item.path == "logo.png" for item in outcome.omitted_files)
    prompt = model.calls[0].prompt_content
    assert "logo.png" in prompt
    assert OmissionReason.BINARY.value in prompt


def test_full_coverage_review_is_complete() -> None:
    packed = _packed([_file("app.py")])
    outcome, _model = _review(packed, {"findings": [_draft_dict()]})
    assert outcome.covers_all_changed_files is True
    assert outcome.cancelled is False
    assert outcome.is_complete() is True
    assert len(outcome.candidates) == 1


def test_review_inputs_reach_the_prompt_through_wrap_untrusted() -> None:
    from pr_reviewer.security.prompt_boundaries import UNTRUSTED_BEGIN

    packed = _packed([_file("app.py")])
    _outcome, model = _review(packed, {"findings": [_draft_dict()]})
    prompt = model.calls[0].prompt_content
    assert UNTRUSTED_BEGIN in prompt
    for label in ("diff", "pr_title", "pr_body"):
        assert f"name: {label}" in prompt
    assert "Add widget" in prompt
    assert "please review" in prompt


def test_review_pull_request_calls_wrap_untrusted_review_inputs() -> None:
    source_path = SRC_ROOT / "reviewer" / "review_pull_request.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    assert "wrap_untrusted_review_inputs" in names
    assert "UntrustedText" in source_path.read_text(encoding="utf-8")


def _scripted_generate_model(
    generate_parsed: list[dict[str, Any]],
    *,
    costs: list[str] | None = None,
) -> Any:
    from pr_reviewer.models.provider import ModelResponse

    generate_costs = costs or ["0"] * len(generate_parsed)

    class ScriptedModel:
        def __init__(self) -> None:
            self.calls: list[Any] = []
            self._generate_index = 0

        def complete_json(self, request: Any) -> Any:
            self.calls.append(request)
            if request.schema_name == "FindingReflectionScores":
                raw_candidates = next(
                    item.content
                    for item in request.untrusted_inputs
                    if item.name == "candidate_findings"
                )
                candidate_count = len(json.loads(raw_candidates))
                response_parsed = {
                    "scores": [
                        {"index": index, "score": 1.0, "reason": "accepted"}
                        for index in range(candidate_count)
                    ]
                }
                cost_usd = "0"
            else:
                response_parsed = generate_parsed[self._generate_index]
                cost_usd = generate_costs[self._generate_index]
                self._generate_index += 1
            return ModelResponse(
                parsed=response_parsed,
                output_hash="a" * 64,
                provider_request_id=None,
                provider="openai",
                model=request.model,
                prompt_name=request.prompt_name,
                prompt_version=request.prompt_version,
                input_tokens=1,
                output_tokens=1,
                cost_usd=cost_usd,
                latency_ms=1,
            )

    return ScriptedModel()


def _generate_models(model: Any) -> list[str]:
    return [call.model for call in model.calls if call.schema_name == "ReviewFindingsDraft"]


def test_empty_generate_retry_is_off_by_default() -> None:
    from pr_reviewer.reviewer import review_pull_request as review_mod

    packed = _packed([_file("app.py")])
    model = _scripted_generate_model([{"findings": []}], costs=["0.001"])

    outcome = review_mod.review_pull_request(
        _snapshot([_file("app.py")]),
        packed,
        [],
        model,
        model_name="gpt-4o-mini",
    )

    assert review_mod.EMPTY_GENERATE_RETRY_ENABLED is False
    assert _generate_models(model) == ["gpt-4o-mini"]
    assert outcome.candidates == ()
    assert outcome.cost_usd == pytest.approx(0.001)


def test_empty_mini_review_retries_once_with_gpt_4_1_and_sums_both_costs(
    monkeypatch: Any,
) -> None:
    from pr_reviewer.reviewer import review_pull_request as review_mod

    monkeypatch.setattr(review_mod, "EMPTY_GENERATE_RETRY_ENABLED", True)
    packed = _packed([_file("app.py")])
    model = _scripted_generate_model(
        [
            {"findings": []},
            {"findings": [_draft_dict(title="Nested option was not copied")]},
        ],
        costs=["0.001", "0.008"],
    )

    outcome = review_mod.review_pull_request(
        _snapshot([_file("app.py")]),
        packed,
        [],
        model,
        model_name="gpt-4o-mini",
    )

    assert _generate_models(model) == ["gpt-4o-mini", "gpt-4.1"]
    assert [item.title for item in outcome.candidates] == ["Nested option was not copied"]
    assert outcome.cost_usd == pytest.approx(0.009)


def test_accepted_mini_finding_does_not_call_gpt_4_1() -> None:
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    packed = _packed([_file("app.py")])
    model = _scripted_generate_model(
        [{"findings": [_draft_dict()]}],
        costs=["0.002"],
    )

    outcome = review_pull_request(
        _snapshot([_file("app.py")]),
        packed,
        [],
        model,
        model_name="gpt-4o-mini",
    )

    assert _generate_models(model) == ["gpt-4o-mini"]
    assert [item.title for item in outcome.candidates] == ["Missing null check"]
    assert outcome.cost_usd == pytest.approx(0.002)


def test_role_models_generate_stays_gpt_4o_mini() -> None:
    from pr_reviewer.models.routing import RoleModels

    assert RoleModels().generate == "gpt-4o-mini"
    assert RoleModels.generate == "gpt-4o-mini"


def test_local_candidate_schema_cannot_store_system_owned_fields() -> None:
    matches = sorted(
        (SRC_ROOT / "local_store" / "postgres_migrations").glob(
            "*_finding_candidates_and_verification.sql"
        )
    )
    assert matches, "local migration *_finding_candidates_and_verification.sql is missing"
    sql = matches[0].read_text(encoding="utf-8").lower()
    assert "create table" in sql and "finding_candidates" in sql
    for field in ("verified", "verification_method", "public_safe", "status"):
        assert field not in sql
