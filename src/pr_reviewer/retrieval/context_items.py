"""Convert retrieved chunks into the reviewer's untrusted context items."""

from __future__ import annotations

from collections.abc import Sequence

from pr_reviewer.contracts.review_context import ReviewContextItem
from pr_reviewer.retrieval.hybrid_search import RetrievedChunk


def context_items_from_chunks(chunks: Sequence[RetrievedChunk]) -> list[ReviewContextItem]:
    return [
        ReviewContextItem(
            source_kind="diff_file",
            file_path=chunk.file_path,
            line_start=chunk.line_start,
            line_end=chunk.line_end,
            content=chunk.content,
            content_hash=chunk.content_hash,
        )
        for chunk in chunks
    ]
