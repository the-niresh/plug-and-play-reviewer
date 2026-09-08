"""Diff-only prompt must describe the FindingDraft schema the model must emit."""

from __future__ import annotations

from typing import get_args

from pr_reviewer.contracts.finding_candidate import Concern, FindingDraft, Severity


def test_diff_only_prompt_lists_every_finding_draft_field_and_enum_value() -> None:
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT

    prompt = DIFF_ONLY_PROMPT.content.lower()
    for field_name in FindingDraft.model_fields:
        if field_name in {"reflection_score", "reflection_reason"}:
            continue
        assert field_name in prompt
    for value in get_args(Concern):
        assert value in prompt
    for value in get_args(Severity):
        assert value in prompt
    assert "line_end >=" in DIFF_ONLY_PROMPT.content
    assert "0 to 1" in DIFF_ONLY_PROMPT.content
