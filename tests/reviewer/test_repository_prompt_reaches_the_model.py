"""A saved repository prompt must reach the model.

The agent-prompts panel saved a version and said "Saved v1 for this repository." Nothing
read it back: get_active_repository_prompt had no callers outside its own module, and
review_pull_request sent DIFF_ONLY_PROMPT.content every time. The product reported
success and changed nothing, which is the failure this codebase keeps having to fix.
"""

from __future__ import annotations

import json
from typing import Any

from pr_reviewer.contracts.review_context import ContextBudget
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
from pr_reviewer.models.provider import ModelResponse
from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT
from pr_reviewer.reviewer.diff_budget import pack_diff
from pr_reviewer.reviewer.review_pull_request import review_pull_request

PATCH = "@@ -1,2 +1,3 @@\n from x import y\n+timeout = None\n more\n"


class _CapturingModel:
    """Records every prompt and returns no findings, so the test is about the prompt."""

    def __init__(self) -> None:
        self.seen: list[str] = []

    def complete_json(self, request: Any) -> ModelResponse:
        self.seen.append(request.prompt_content)
        if request.schema_name == "FindingReflectionScores":
            raw = next(
                item.content
                for item in request.untrusted_inputs
                if item.name == "candidate_findings"
            )
            parsed: dict[str, Any] = {
                "scores": [
                    {"index": index, "score": 1.0, "reason": "accepted"}
                    for index in range(len(json.loads(raw)))
                ]
            }
        else:
            parsed = {"findings": []}
        return ModelResponse(
            parsed=parsed,
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


def _sent(repository_prompt: str | None) -> str:
    snapshot = PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=12,
        base_sha="a" * 40,
        head_sha="b" * 40,
        title="Add widget",
        body="please review",
        files=[
            PullRequestFile.model_validate(
                {"path": "app.py", "status": "modified", "patch": PATCH}
            )
        ],
    )
    packed = pack_diff(snapshot, ContextBudget(tokens=10_000), lambda _text: 1)
    model = _CapturingModel()
    review_pull_request(
        snapshot,
        packed,
        [],
        model,  # type: ignore[arg-type]
        model_name="gpt-4o-mini",
        repository_prompt=repository_prompt,
    )
    return model.seen[0]


def test_the_repository_prompt_is_sent_and_marked_untrusted() -> None:
    sent = _sent("Always flag missing timeouts on http calls.")

    assert "Always flag missing timeouts on http calls." in sent
    # Wrapped like the diff and the PR body: a person typed it, so the model must not
    # read it as a system instruction.
    assert "repository_prompt" in sent
    # Added, not swapped. Replacing the built-in prompt would drop the output schema.
    assert DIFF_ONLY_PROMPT.content in sent


def test_no_repository_prompt_changes_nothing() -> None:
    sent = _sent(None)

    assert "repository_prompt" not in sent
    assert DIFF_ONLY_PROMPT.content in sent
