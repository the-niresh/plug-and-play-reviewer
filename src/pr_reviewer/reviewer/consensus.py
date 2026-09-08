"""Multi-model generate-stage consensus. Off by default."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor

from pr_reviewer.contracts.finding_candidate import (
    ConsensusFinding,
    FindingCandidate,
    ModelReasoning,
)
from pr_reviewer.evals.match_findings import match_findings
from pr_reviewer.evals.types import EvalLabel

MULTI_MODEL_GENERATE_ENABLED = False
DEFAULT_GENERATE_MODELS: tuple[str, ...] = (
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "claude-3-5-haiku-latest",
)
_CONSENSUS_THREAD_PREFIX = "pr-reviewer-consensus"


def _candidate_to_label(candidate: FindingCandidate) -> EvalLabel:
    return EvalLabel(
        concern=candidate.concern,
        category=candidate.category,
        file_path=candidate.file_path,
        line_start=candidate.line_start,
        line_end=candidate.line_end,
    )


def _structurally_match(left: FindingCandidate, right: FindingCandidate) -> bool:
    result = match_findings([_candidate_to_label(left)], [right])
    return bool(result.matched)


def _near_miss(left: FindingCandidate, right: FindingCandidate) -> bool:
    result = match_findings([_candidate_to_label(left)], [right])
    return result.needs_human_match


def rank_findings_by_agreement(
    findings_by_model: Mapping[str, Sequence[FindingCandidate]],
) -> list[ConsensusFinding]:
    clusters: list[list[tuple[str, FindingCandidate]]] = []
    for model, findings in findings_by_model.items():
        for finding in findings:
            placed = False
            for cluster in clusters:
                representative = cluster[0][1]
                if _structurally_match(representative, finding):
                    cluster.append((model, finding))
                    placed = True
                    break
            if not placed:
                clusters.append([(model, finding)])

    ranked: list[ConsensusFinding] = []
    for cluster in clusters:
        representative = max(cluster, key=lambda item: item[1].confidence)[1]
        models = {model for model, _finding in cluster}
        model_reasoning = tuple(
            ModelReasoning(model=model, rationale=finding.rationale)
            for model, finding in cluster
        )
        needs_human = any(
            _near_miss(left_finding, right_finding)
            for _left_model, left_finding in cluster
            for _right_model, right_finding in cluster
            if left_finding is not right_finding
        )
        evidence = tuple(
            sorted({entry for _model, finding in cluster for entry in finding.evidence})
        )
        ranked.append(
            ConsensusFinding(
                concern=representative.concern,
                severity=representative.severity,
                category=representative.category,
                file_path=representative.file_path,
                line_start=min(finding.line_start for _model, finding in cluster),
                line_end=max(finding.line_end for _model, finding in cluster),
                title=representative.title,
                rationale=representative.rationale,
                evidence=list(evidence),
                confidence=max(finding.confidence for _model, finding in cluster),
                agreement_count=len(models),
                model_reasoning=model_reasoning,
                needs_human_match=needs_human,
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.agreement_count,
            -item.confidence,
            item.file_path,
            item.line_start,
            item.title,
        )
    )
    return ranked


def fan_out_generate_findings(
    *,
    generate_models: Sequence[str],
    generate_one: Callable[[str], Sequence[FindingCandidate]],
    max_workers: int,
    future_timeout_seconds: float,
) -> dict[str, Sequence[FindingCandidate]]:
    pool = ThreadPoolExecutor(
        max_workers=max_workers,
        thread_name_prefix=_CONSENSUS_THREAD_PREFIX,
    )
    futures: dict[str, Future[Sequence[FindingCandidate]]] = {}
    try:
        for model_name in generate_models:
            futures[model_name] = pool.submit(generate_one, model_name)
        results: dict[str, Sequence[FindingCandidate]] = {}
        for model_name, future in futures.items():
            findings = future.result(timeout=future_timeout_seconds)
            results[model_name] = tuple(findings)
        return results
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
