"""Offline hash embeddings for tests only.

These vectors carry no semantic similarity. Nearest-neighbour search over them is
effectively random. Use only with ``--offline-embeddings`` for wiring smoke tests.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from pr_reviewer.retrieval.embed import DETERMINISTIC_EMBEDDING_MODEL, V1_EMBEDDING_DIMENSIONS


class DeterministicEmbeddingProvider:
    model_name = DETERMINISTIC_EMBEDDING_MODEL
    dimensions = V1_EMBEDDING_DIMENSIONS

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [_vector_for(text) for text in texts]


def _vector_for(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [
        ((digest[index % len(digest)] / 255.0) - 0.5)
        for index in range(V1_EMBEDDING_DIMENSIONS)
    ]
    values[0] = float(len(text) % 97) / 97.0
    return values
