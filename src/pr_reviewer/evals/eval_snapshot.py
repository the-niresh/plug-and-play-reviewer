"""Build review inputs from frozen EvalCase rows. No model calls."""

from __future__ import annotations

import re

from pr_reviewer.evals.types import EvalCase
from pr_reviewer.github.pull_request import GitHubFileStatus, PullRequestFile, PullRequestSnapshot

_HUNK_HEADER = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def files_from_eval_diff(diff: str) -> list[PullRequestFile]:
    """Split a unified diff into per-file patches for pack_diff."""
    if not diff.strip():
        return []
    chunks: list[str] = []
    if diff.startswith("diff --git "):
        parts = diff.split("\ndiff --git ")
        chunks = [parts[0]] + ["diff --git " + part for part in parts[1:]]
    else:
        chunks = [diff]
    files: list[PullRequestFile] = []
    for chunk in chunks:
        path = _path_from_diff_chunk(chunk)
        if path is None:
            continue
        patch = _patch_from_diff_chunk(chunk)
        if not patch.strip():
            continue
        is_added = any(line == "--- /dev/null" for line in chunk.splitlines())
        status: GitHubFileStatus = "added" if is_added else "modified"
        files.append(
            PullRequestFile(
                path=path,
                status=status,
                patch=patch,
            )
        )
    return files


def snapshot_from_eval_case(case: EvalCase) -> PullRequestSnapshot:
    owner, name = case.repository.split("/", 1)
    return PullRequestSnapshot(
        repo_owner=owner,
        repo_name=name,
        number=1,
        base_sha="0" * 40,
        head_sha=case.sha,
        title=case.source_evidence[0],
        body="",
        files=files_from_eval_diff(case.diff),
    )


def _path_from_diff_chunk(chunk: str) -> str | None:
    for line in chunk.splitlines():
        if line.startswith("+++ "):
            path = line[4:]
            if path.startswith("b/"):
                path = path[2:]
            if path == "/dev/null":
                return None
            return path
    return None


def _patch_from_diff_chunk(chunk: str) -> str:
    lines: list[str] = []
    in_patch = False
    for line in chunk.splitlines():
        if _HUNK_HEADER.match(line):
            in_patch = True
        if in_patch:
            lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")
