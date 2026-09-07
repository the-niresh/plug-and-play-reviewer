"""Reciprocal rank fusion. k defaults to 60.

An optional per-ranking weight scales that ranking's contribution. Defaults to 1.0
for every ranking, so existing callers see no change.
"""

from __future__ import annotations


def reciprocal_rank_fusion(
    rankings: list[list[str]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[str]:
    scores: dict[str, float] = {}
    first_seen: dict[str, int] = {}
    order = 0
    for list_index, ranking in enumerate(rankings):
        weight = weights[list_index] if weights is not None else 1.0
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + weight / (k + rank)
            if item not in first_seen:
                first_seen[item] = order
                order += 1
    return sorted(scores, key=lambda item: (-scores[item], first_seen[item]))
