"""Prompt text derived from FindingDraft so the model sees the real schema."""

from __future__ import annotations

from typing import get_args

from pr_reviewer.contracts.finding_candidate import Concern, FindingDraft, Severity

_PROMPT_FIELD_HELP: dict[str, str] = {
    "concern": "one of {concerns}",
    "severity": "one of {severities}",
    "category": "string naming the issue type",
    "file_path": "repository-relative path to the changed file",
    "line_start": "positive integer line number on the new side of the diff",
    "line_end": "positive integer line number with line_end >= line_start",
    "title": "short summary of the issue",
    "rationale": "why this matters on the changed lines",
    "evidence": "non-empty list of strings quoting the changed lines",
    "confidence": "number from 0 to 1",
}


def finding_draft_prompt_schema_section() -> str:
    """Build schema instructions from FindingDraft, including enum values."""
    concerns = ", ".join(f'"{value}"' for value in get_args(Concern))
    severities = ", ".join(f'"{value}"' for value in get_args(Severity))
    field_lines: list[str] = []
    for name in FindingDraft.model_fields:
        if name in {"reflection_score", "reflection_reason"}:
            continue
        help_text = _PROMPT_FIELD_HELP[name]
        if "{concerns}" in help_text or "{severities}" in help_text:
            help_text = help_text.format(concerns=concerns, severities=severities)
        field_lines.append(f"- {name}: {help_text}")
    return "\n".join(
        [
            'Return JSON {"findings": [...]} where each finding object has exactly these fields:',
            *field_lines,
            "",
            "Example finding:",
            (
                '{"concern": "correctness", "severity": "high", "category": "null-check", '
                '"file_path": "src/app.py", "line_start": 12, "line_end": 12, '
                '"title": "Missing null guard", '
                '"rationale": "value can be None before it is used", '
                '"evidence": ["12|    return value.upper()"], "confidence": 0.85}'
            ),
        ]
    )
