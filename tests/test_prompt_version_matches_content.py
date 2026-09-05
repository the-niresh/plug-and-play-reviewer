from __future__ import annotations

from typing import Any

from pr_reviewer.contracts.review_context import (
    PACKING_STRATEGY_VERSION,
    PackedDiff,
    ReviewContextItem,
)
from pr_reviewer.github.pull_request import PullRequestSnapshot


def test_diff_only_prompt_version_is_derived_from_its_content() -> None:
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT, prompt_content_version

    assert DIFF_ONLY_PROMPT.version == prompt_content_version(DIFF_ONLY_PROMPT.content)


def test_review_uses_one_prompt_object_for_content_name_and_version() -> None:
    from pr_reviewer.models.provider import ModelResponse
    from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT
    from pr_reviewer.reviewer.review_pull_request import review_pull_request

    class CapturingModel:
        def __init__(self) -> None:
            self.calls: list[Any] = []

        def complete_json(self, request: Any) -> Any:
            self.calls.append(request)
            return ModelResponse(
                parsed={"findings": []},
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

    packed = PackedDiff(
        packing_strategy_version=PACKING_STRATEGY_VERSION,
        items=(
            ReviewContextItem(
                source_kind="diff_file",
                file_path="app.py",
                line_start=1,
                line_end=1,
                content="NEW app.py\n1| value = None\n",
                content_hash="b" * 64,
            ),
        ),
        included_files=("app.py",),
        omitted_files=(),
        prompt_tokens=1,
        covers_all_changed_files=True,
    )
    snapshot = PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=12,
        base_sha="a" * 40,
        head_sha="b" * 40,
        title="Add widget",
        body="please review",
        files=(),
    )
    model = CapturingModel()

    review_pull_request(snapshot, packed, [], model, model_name="gpt-4o-mini")

    request = model.calls[0]
    assert request.prompt_name == DIFF_ONLY_PROMPT.name
    assert request.prompt_version == DIFF_ONLY_PROMPT.version
    assert request.prompt_content.startswith(DIFF_ONLY_PROMPT.content)
