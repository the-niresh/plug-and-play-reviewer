"""Findings carry an optional suggested fix from the same generate call.

q5: describe it in the prompt, post it as a GitHub suggestion block, and drop
the suggestion (not the finding) when it cannot apply cleanly.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from test_post_review import FakeGitHub, _decision, _finding, _post
from test_review_pull_request import FORBIDDEN_FIELDS, _draft_dict, _file, _packed, _review


def test_finding_draft_carries_optional_suggested_fix() -> None:
    from pr_reviewer.contracts.finding_candidate import FindingDraft, candidate_from_draft

    draft = FindingDraft.model_validate(
        _draft_dict(suggested_fix="    return guarded(value)")
    )
    candidate = candidate_from_draft(draft)
    assert draft.suggested_fix == "    return guarded(value)"
    assert candidate.suggested_fix == "    return guarded(value)"

    omitted = FindingDraft.model_validate(_draft_dict())
    assert omitted.suggested_fix is None
    assert candidate_from_draft(omitted).suggested_fix is None


def test_suggested_fix_does_not_let_the_model_set_system_owned_fields() -> None:
    from pr_reviewer.contracts.finding_candidate import FindingDraft

    payload = _draft_dict(suggested_fix="    return 0")
    for field in (*FORBIDDEN_FIELDS, "allow_public_post"):
        with pytest.raises(ValidationError):
            FindingDraft.model_validate({**payload, field: True})


def test_prompt_describes_suggested_fix_the_same_way_as_other_fields() -> None:
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT
    from pr_reviewer.prompts.finding_schema import finding_draft_prompt_schema_section

    section = finding_draft_prompt_schema_section()
    assert "suggested_fix" in section
    assert "optional" in section.lower()
    assert "suggestion" in section.lower()
    assert '"suggested_fix"' in section
    assert "suggested_fix" in DIFF_ONLY_PROMPT.content


def test_review_keeps_suggested_fix_from_the_same_generate_call() -> None:
    packed = _packed([_file("app.py")])
    outcome, model = _review(
        packed,
        {
            "findings": [
                _draft_dict(suggested_fix="new and guarded"),
            ]
        },
    )
    assert len(outcome.candidates) == 1
    assert outcome.candidates[0].suggested_fix == "new and guarded"
    generate_calls = [call for call in model.calls if call.schema_name == "ReviewFindingsDraft"]
    assert len(generate_calls) == 1
    assert {call.schema_name for call in model.calls} <= {
        "ReviewFindingsDraft",
        "FindingReflectionScores",
    }


def test_posted_comment_renders_a_github_suggestion_block() -> None:
    github = FakeGitHub()
    finding = _finding(suggested_fix="    return 3")
    _post(github, [(finding, _decision())])
    body = github.submissions[0].comments[0].body
    assert "```suggestion" in body
    assert "    return 3" in body
    assert "Return value changed" in body


def test_unclean_suggestion_is_dropped_finding_is_kept_and_drop_is_counted() -> None:
    github = FakeGitHub()
    finding = _finding(
        line_start=3,
        line_end=99,
        suggested_fix="    return 3",
        title="Return value changed",
    )
    result = _post(github, [(finding, _decision())])
    comments = github.submissions[0].comments
    assert comments, "the finding must still post"
    body = comments[0].body
    assert "```suggestion" not in body
    assert "Return value changed" in body
    assert result.suggestion_dropped_count == 1


def test_fence_breaking_suggestion_is_dropped() -> None:
    github = FakeGitHub()
    finding = _finding(suggested_fix="oops\n```\nnot a suggestion")
    result = _post(github, [(finding, _decision())])
    body = github.submissions[0].comments[0].body
    assert "```suggestion" not in body
    assert "Return value changed" in body
    assert result.suggestion_dropped_count == 1


REVIEWER_UAT_PATCH = (
    "@@ -0,0 +1,10 @@\n"
    "+def risky():\n"
    "+    value = 0\n"
    "+    return 1 / value\n"
    "+    return None\n"
    "+    return 0\n"
    "+    return 1\n"
    "+    return 2\n"
    "+    return 3\n"
    "+    return 4\n"
    "+    return 5\n"
    "+    return 6\n"
)


def test_uat_shape_wide_span_single_line_suggestion_is_dropped() -> None:
    """Stranger UAT: finding span +1..+10 but suggested_fix replaces one line only."""
    from pr_reviewer.contracts.review_context import FilePatch

    github = FakeGitHub()
    finding = _finding(
        file_path="reviewer_uat_bug.py",
        line_start=1,
        line_end=10,
        title="Division by zero in risky()",
        suggested_fix="    return 1 / value if value else None",
    )
    patch = FilePatch(path="reviewer_uat_bug.py", patch=REVIEWER_UAT_PATCH, previous_path=None)
    result = _post(github, [(finding, _decision())], patches=[patch])
    comment = github.submissions[0].comments[0]
    assert comment.line == 1
    assert comment.start_line is None
    assert "```suggestion" not in comment.body
    assert "Division by zero" in comment.body
    assert result.suggestion_dropped_count == 1


def test_multi_line_suggestion_must_match_span_exactly() -> None:
    from pr_reviewer.contracts.review_context import FilePatch

    github = FakeGitHub()
    finding = _finding(
        file_path="reviewer_uat_bug.py",
        line_start=1,
        line_end=3,
        title="Guard the divide",
        suggested_fix="def risky():\n    value = 0\n    return 1 / value if value else None",
    )
    patch = FilePatch(path="reviewer_uat_bug.py", patch=REVIEWER_UAT_PATCH, previous_path=None)
    _post(github, [(finding, _decision())], patches=[patch])
    comment = github.submissions[0].comments[0]
    assert comment.start_line == 1
    assert comment.line == 3
    assert "```suggestion" in comment.body
    assert "return 1 / value if value else None" in comment.body
