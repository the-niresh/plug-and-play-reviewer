"""A bounded explorer: fires only when retrieval was not enough, never by default.

should_explore is a pure gate. Nothing in this module or elsewhere calls it
automatically; a caller must read its answer and decide to run the explorer. That
keeps "never by default" true by construction rather than by convention.

run_bounded_explorer drives a strict request/response loop against a cloned,
read-only checkout: on each turn the model returns exactly one JSON action, either one
of the three typed tools (reviewer.tools) or a finish action. Two independent caps
bound the loop -- a hard count of tool calls and a token estimate over their combined
output, using the same 4-chars-per-token heuristic reviewer/review_pull_request.py and
agent_surfaces/backend.py already use -- so a model that never finishes cannot run
forever or read without limit.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pr_reviewer.contracts.github import RepositoryIdentity
from pr_reviewer.contracts.review_context import ReviewContextItem
from pr_reviewer.models.provider import ModelProvider, ModelRequest
from pr_reviewer.reviewer.clone import CloneFetcher, cloned_pull_request_head
from pr_reviewer.reviewer.tools import (
    ClonedRepositoryTools,
    GrepArgs,
    ListDirArgs,
    ReadFileArgs,
    ToolCall,
    ToolResult,
    parse_tool_call,
)

EXPLORER_PROMPT_NAME = "bounded_explorer"
EXPLORER_PROMPT_VERSION = "v1"
EXPLORER_SCHEMA_NAME = "ExplorerAction"

DEFAULT_CONFIDENCE_THRESHOLD = 0.35
DEFAULT_SENSITIVITY_THRESHOLD = 0.7

StoppedReason = Literal[
    "finished",
    "tool_call_cap",
    "token_cap",
    "malformed_action",
]


class FinishArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: Literal["finish"] = "finish"
    summary: str = Field(default="")


ExplorerAction = ReadFileArgs | GrepArgs | ListDirArgs | FinishArgs


@dataclass(frozen=True)
class ExplorationBudget:
    """Hard caps. A model that never calls finish still stops here."""

    max_tool_calls: int = 6
    max_tokens: int = 4000


@dataclass(frozen=True)
class ExplorerOutcome:
    context_items: tuple[ReviewContextItem, ...]
    tool_calls_used: int
    stopped_reason: StoppedReason


DEFAULT_EXPLORATION_BUDGET = ExplorationBudget()


def should_explore(
    *,
    retrieval_confidence: float,
    sensitivity: float,
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    sensitivity_threshold: float = DEFAULT_SENSITIVITY_THRESHOLD,
) -> bool:
    """Fire only when retrieval was not enough or the file is sensitive enough to
    justify the extra cost. Neither branch fires on ordinary, well-retrieved changes.
    """
    return retrieval_confidence < confidence_threshold or sensitivity > sensitivity_threshold


def parse_explorer_action(raw: object) -> ExplorerAction:
    if not isinstance(raw, dict):
        raise ValueError("explorer action must be a JSON object")
    if raw.get("tool") == "finish":
        return FinishArgs.model_validate(raw)
    return parse_tool_call(raw)


def run_bounded_explorer(
    clone_root: Path,
    model: ModelProvider,
    *,
    model_name: str,
    task_prompt: str,
    budget: ExplorationBudget = DEFAULT_EXPLORATION_BUDGET,
) -> ExplorerOutcome:
    tools = ClonedRepositoryTools(clone_root)
    transcript: list[str] = []
    context_items: list[ReviewContextItem] = []
    tokens_used = 0
    tool_calls_used = 0

    while True:
        prompt_content = task_prompt + "\n\n" + "\n\n".join(transcript)
        response = model.complete_json(
            ModelRequest(
                model=model_name,
                prompt_name=EXPLORER_PROMPT_NAME,
                prompt_version=EXPLORER_PROMPT_VERSION,
                prompt_content=prompt_content,
                schema_name=EXPLORER_SCHEMA_NAME,
                untrusted_inputs=[],
                timeout_seconds=30.0,
                max_output_tokens=512,
            )
        )
        try:
            action = parse_explorer_action(response.parsed)
        except (ValueError, ValidationError):
            return _outcome(context_items, tool_calls_used, "malformed_action")
        if isinstance(action, FinishArgs):
            return _outcome(context_items, tool_calls_used, "finished")

        result = tools.run(action)
        tool_calls_used += 1
        transcript.append(f"tool_call: {action.model_dump()}\nresult: {result.output}")
        context_items.append(_context_item_from_result(action, result))
        tokens_used += _estimate_tokens(result.output)

        if tokens_used > budget.max_tokens:
            return _outcome(context_items, tool_calls_used, "token_cap")
        if tool_calls_used >= budget.max_tool_calls:
            return _outcome(context_items, tool_calls_used, "tool_call_cap")


def explore_pull_request(
    identity: RepositoryIdentity,
    head_sha: str,
    model: ModelProvider,
    *,
    model_name: str,
    task_prompt: str,
    budget: ExplorationBudget = DEFAULT_EXPLORATION_BUDGET,
    token: str | None = None,
    clone_timeout_seconds: float = 60.0,
    fetcher: CloneFetcher | None = None,
) -> ExplorerOutcome:
    """Clone, explore, and always clean up, via cloned_pull_request_head's finally."""
    with cloned_pull_request_head(
        identity,
        head_sha,
        token=token,
        timeout_seconds=clone_timeout_seconds,
        fetcher=fetcher,
    ) as clone_root:
        return run_bounded_explorer(
            clone_root, model, model_name=model_name, task_prompt=task_prompt, budget=budget
        )


def _context_item_from_result(action: ToolCall, result: ToolResult) -> ReviewContextItem:
    file_path = action.path if isinstance(action, ReadFileArgs | ListDirArgs) else "<grep>"
    content = result.output
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return ReviewContextItem(
        source_kind="diff_file",
        file_path=file_path,
        line_start=0,
        line_end=0,
        content=content,
        content_hash=digest,
    )


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _outcome(
    context_items: list[ReviewContextItem], tool_calls_used: int, reason: StoppedReason
) -> ExplorerOutcome:
    return ExplorerOutcome(
        context_items=tuple(context_items), tool_calls_used=tool_calls_used, stopped_reason=reason
    )
