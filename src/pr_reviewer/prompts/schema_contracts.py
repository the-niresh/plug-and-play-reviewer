"""Registry of JSON-shaped model prompts and the pydantic models that validate them."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from pr_reviewer.contracts.finding_candidate import FindingDraft
from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT


@dataclass(frozen=True)
class JsonPromptContract:
    name: str
    prompt_text: Callable[[], str]
    item_model: type[BaseModel]
    skip_fields: frozenset[str] = frozenset()


def json_prompt_contracts() -> tuple[JsonPromptContract, ...]:
    from pr_reviewer.reviewer.reflect import ReflectionScore, reflection_prompt_text

    return (
        JsonPromptContract(
            name="diff_only_reviewer",
            prompt_text=lambda: DIFF_ONLY_PROMPT.content,
            item_model=FindingDraft,
            skip_fields=frozenset({"reflection_score", "reflection_reason"}),
        ),
        JsonPromptContract(
            name="finding_reflection",
            prompt_text=reflection_prompt_text,
            item_model=ReflectionScore,
        ),
    )
