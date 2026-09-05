"""Diff-only one-agent review. One model call. Heartbeat is synchronous and once."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import ValidationError

from pr_reviewer.contracts.finding_candidate import (
    FindingCandidate,
    FindingDraft,
    candidate_from_draft,
)
from pr_reviewer.contracts.review_context import PackedDiff, ReviewContextItem, ReviewOutcome
from pr_reviewer.contracts.runner import LeaseState
from pr_reviewer.github.pull_request import PullRequestSnapshot
from pr_reviewer.models.provider import ModelProvider, ModelRequest
from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT
from pr_reviewer.reviewer.diff_budget import omission_prompt_section
from pr_reviewer.reviewer.reflect import reflect_findings
from pr_reviewer.security.prompt_boundaries import UntrustedText, wrap_untrusted_review_inputs

MAX_FINDING_DRAFTS = 32
DIFF_ONLY_PROMPT_NAME = DIFF_ONLY_PROMPT.name
DIFF_ONLY_PROMPT_VERSION = DIFF_ONLY_PROMPT.version
_NEW_LINE = re.compile(r"^(\d+)\| ")
_SYSTEM_PROMPT = DIFF_ONLY_PROMPT.content


@dataclass(frozen=True)
class ParsedCandidates:
    candidates: tuple[FindingCandidate, ...]
    schema_rejected_findings: int = 0
    grounding_rejected_findings: int = 0
    duplicate_rejected_findings: int = 0


def review_pull_request(
    snapshot: PullRequestSnapshot,
    packed: PackedDiff,
    context: list[ReviewContextItem],
    model: ModelProvider,
    *,
    model_name: str,
    heartbeat: Callable[[], LeaseState] | None = None,
) -> ReviewOutcome:
    if heartbeat is not None:
        lease = heartbeat()
        if lease.status == "cancelled":
            return ReviewOutcome(
                candidates=(),
                packing_strategy_version=packed.packing_strategy_version,
                covers_all_changed_files=packed.covers_all_changed_files,
                omitted_files=packed.omitted_files,
                cancelled=True,
            )
        if lease.status != "active":
            raise RuntimeError(f"review job lease is {lease.status}")

    diff_text = "\n".join(item.content for item in packed.items)
    sections = wrap_untrusted_review_inputs(
        diff=UntrustedText(diff_text),
        title=UntrustedText(snapshot.title),
        body=UntrustedText(snapshot.body),
        commit_messages=(),
        review_comments=(),
        retrieved_chunks=tuple(UntrustedText(item.content) for item in context),
    )
    prompt_content = (
        DIFF_ONLY_PROMPT.content
        + "\n"
        + omission_prompt_section(packed)
        + "\n\n"
        + "\n\n".join(sections)
    )
    response = model.complete_json(
        ModelRequest(
            model=model_name,
            prompt_name=DIFF_ONLY_PROMPT.name,
            prompt_version=DIFF_ONLY_PROMPT.version,
            prompt_content=prompt_content,
            schema_name="ReviewFindingsDraft",
            untrusted_inputs=[],
            timeout_seconds=60.0,
            max_output_tokens=2048,
        )
    )
    parsed_candidates = _candidates_from_parsed(response.parsed, packed)
    reflected = reflect_findings(
        model=model,
        model_name=model_name,
        packed=packed,
        candidates=parsed_candidates.candidates,
    )
    return ReviewOutcome(
        candidates=reflected.accepted,
        suppressed_candidates=reflected.suppressed,
        packing_strategy_version=packed.packing_strategy_version,
        covers_all_changed_files=packed.covers_all_changed_files,
        omitted_files=packed.omitted_files,
        cancelled=False,
        schema_rejected_findings=parsed_candidates.schema_rejected_findings,
        grounding_rejected_findings=parsed_candidates.grounding_rejected_findings,
        duplicate_rejected_findings=parsed_candidates.duplicate_rejected_findings,
    )


def _candidates_from_parsed(parsed: object, packed: PackedDiff) -> ParsedCandidates:
    if not isinstance(parsed, dict):
        return ParsedCandidates(candidates=())
    raw_findings = parsed.get("findings")
    if not isinstance(raw_findings, list):
        return ParsedCandidates(candidates=())
    lines_by_path = {item.file_path: _new_side_lines(item.content) for item in packed.items}
    accepted: list[FindingCandidate] = []
    seen: set[tuple[str, int, int, str]] = set()
    schema_rejected = 0
    grounding_rejected = 0
    duplicate_rejected = 0
    for item in raw_findings:
        try:
            draft = FindingDraft.model_validate(item)
        except ValidationError:
            schema_rejected += 1
            continue
        if not _in_changed_diff(draft, lines_by_path):
            grounding_rejected += 1
            continue
        key = (draft.file_path, draft.line_start, draft.line_end, draft.title)
        if key in seen:
            duplicate_rejected += 1
            continue
        seen.add(key)
        accepted.append(candidate_from_draft(draft))
        if len(accepted) >= MAX_FINDING_DRAFTS:
            break
    return ParsedCandidates(
        candidates=tuple(accepted),
        schema_rejected_findings=schema_rejected,
        grounding_rejected_findings=grounding_rejected,
        duplicate_rejected_findings=duplicate_rejected,
    )


def _new_side_lines(content: str) -> set[int]:
    in_new = False
    lines: set[int] = set()
    for line in content.splitlines():
        if line.startswith("NEW "):
            in_new = True
            continue
        if line.startswith("OLD "):
            in_new = False
            continue
        if not in_new:
            continue
        match = _NEW_LINE.match(line)
        if match is not None:
            lines.add(int(match.group(1)))
    return lines


def _in_changed_diff(draft: FindingDraft, lines_by_path: dict[str, set[int]]) -> bool:
    numbers = lines_by_path.get(draft.file_path)
    if not numbers:
        return False
    return all(line in numbers for line in range(draft.line_start, draft.line_end + 1))
