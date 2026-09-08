"""Prompt text derived from ReflectionScore so the judge sees the real schema."""

from __future__ import annotations


def reflection_prompt_schema_section() -> str:
    """Build schema instructions for FindingReflectionScores responses."""
    return "\n".join(
        [
            'Return JSON {"scores": [...]} where each score object has exactly these fields:',
            "- index: non-negative integer, 0-based position of the input finding in the list",
            "- score: number from 0 to 1",
            "- reason: non-empty string explaining the score",
            "",
            "Index rule:",
            "- Score every input finding exactly once.",
            "- Indexes are 0-based, start at 0, and run through len(findings) - 1.",
            "- No index may be repeated or omitted.",
            "",
            "Example response for two input findings:",
            (
                '{"scores": [{"index": 0, "score": 1.0, "reason": "clear bug on a changed line"}, '
                '{"index": 1, "score": 0.0, "reason": "speculation with no visible failure path"}]}'
            ),
        ]
    )
