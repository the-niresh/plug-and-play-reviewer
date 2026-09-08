"""Diff-only one-agent review. One model call. Heartbeat is synchronous and once."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from pydantic import ValidationError

from pr_reviewer.contracts.finding_candidate import (
    FindingCandidate,
    FindingDraft,
    candidate_from_draft,
)
from pr_reviewer.contracts.review_context import PackedDiff, ReviewContextItem, ReviewOutcome
from pr_reviewer.contracts.runner import LeaseState
from pr_reviewer.github.pull_request import PullRequestSnapshot
from pr_reviewer.models.catalogue import list_providers
from pr_reviewer.models.provider import (
    ModelProvider,
    ModelProviderFailure,
    ModelRequest,
    cost_usd_for,
)
from pr_reviewer.prompts.diff_only import DIFF_ONLY_PROMPT
from pr_reviewer.reliability.budget import BudgetLimit, CostEstimate, require_within_budget
from pr_reviewer.reviewer.diff_budget import omission_prompt_section
from pr_reviewer.reviewer.reflect import reflect_findings
from pr_reviewer.security.prompt_boundaries import UntrustedText, wrap_untrusted_review_inputs

MAX_FINDING_DRAFTS = 32
MAX_OUTPUT_TOKENS = 2048
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
    budget: BudgetLimit | None = None,
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
    if budget is not None:
        require_within_budget(budget, estimate_review_cost(prompt_content, model_name))
    response = model.complete_json(
        ModelRequest(
            model=model_name,
            prompt_name=DIFF_ONLY_PROMPT.name,
            prompt_version=DIFF_ONLY_PROMPT.version,
            prompt_content=prompt_content,
            schema_name="ReviewFindingsDraft",
            untrusted_inputs=[],
            timeout_seconds=60.0,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        )
    )
    parsed_candidates = _candidates_from_parsed(response.parsed, packed)
    reflected = reflect_findings(
        model=model,
        model_name=model_name,
        packed=packed,
        candidates=parsed_candidates.candidates,
    )
    total_cost_usd = float(response.cost_usd) + reflected.cost_usd
    total_latency_ms = response.latency_ms + reflected.latency_ms
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
        cost_usd=total_cost_usd,
        latency_ms=total_latency_ms,
    )


def estimate_review_cost(prompt_content: str, model_name: str) -> CostEstimate:
    """Estimate cost before spending, on the exact text that would be sent.

    Uses the same 4-chars-per-token heuristic agent_surfaces/backend.py already uses to
    decide what fits in the packer, not a second tokenizer. Output is estimated at the
    worst case, MAX_OUTPUT_TOKENS, so the estimate never understates what the call could
    cost. An unpriced model fails closed, matching cost_usd_for's own rule that cost can
    never go uncounted.
    """
    input_tokens = max(1, len(prompt_content) // 4)
    vendor = _vendor_for_model(model_name)
    if vendor is None:
        raise ModelProviderFailure(f"unknown model {model_name}")
    cost_usd = Decimal(cost_usd_for(vendor, model_name, input_tokens, MAX_OUTPUT_TOKENS))
    return CostEstimate(
        input_tokens=input_tokens, output_tokens=MAX_OUTPUT_TOKENS, cost_usd=cost_usd
    )


def _vendor_for_model(model_name: str) -> str | None:
    for provider in list_providers():
        if any(entry.model_id == model_name for entry in provider.models):
            return provider.provider_id
    return None


def _candidates_from_parsed(parsed: object, packed: PackedDiff) -> ParsedCandidates:
    if not isinstance(parsed, dict):
        return ParsedCandidates(candidates=())
    raw_findings = parsed.get("findings")
    if not isinstance(raw_findings, list):
        return ParsedCandidates(candidates=())
    lines_by_path = {item.file_path: _new_side_lines(item.content) for item in packed.items}
    hunks_by_path = {item.file_path: _new_side_hunk_ranges(item.content) for item in packed.items}
    packed_has_implementation = any(not _is_test_path(item.file_path) for item in packed.items)
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
        if packed_has_implementation and _is_test_path(draft.file_path):
            grounding_rejected += 1
            continue
        draft = _expand_draft_to_hunk(draft, hunks_by_path)
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


def _new_side_hunk_ranges(content: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    current: list[int] = []
    in_new = False
    for line in content.splitlines():
        if line.startswith("NEW "):
            if current:
                ranges.append((current[0], current[-1]))
                current = []
            in_new = True
            continue
        if line.startswith("OLD "):
            if current:
                ranges.append((current[0], current[-1]))
                current = []
            in_new = False
            continue
        if not in_new:
            continue
        match = _NEW_LINE.match(line)
        if match is not None:
            current.append(int(match.group(1)))
    if current:
        ranges.append((current[0], current[-1]))
    return ranges


def _expand_draft_to_hunk(
    draft: FindingDraft, hunks_by_path: dict[str, list[tuple[int, int]]]
) -> FindingDraft:
    for start, end in hunks_by_path.get(draft.file_path, ()):
        if start <= draft.line_start and draft.line_end <= end:
            if draft.line_start == start and draft.line_end == end:
                return draft
            return draft.model_copy(update={"line_start": start, "line_end": end})
    return draft


def _in_changed_diff(draft: FindingDraft, lines_by_path: dict[str, set[int]]) -> bool:
    numbers = lines_by_path.get(draft.file_path)
    if not numbers:
        return False
    return all(line in numbers for line in range(draft.line_start, draft.line_end + 1))


def _is_test_path(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    name = parts[-1].casefold()
    if name.startswith("test_") or name.endswith("_test.py") or name.endswith("_test.ts"):
        return True
    if ".test." in name or ".spec." in name:
        return True
    return any(part.casefold() in {"test", "tests", "__tests__"} for part in parts[:-1])
