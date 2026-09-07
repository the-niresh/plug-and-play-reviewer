"""Clone the PR head to a scratch directory, read-only, always removed.

Reuses runner.repository_fallback.BoundedCloneFetcher for the clone itself and its
path-safety guard (assert_path_stays_inside) rather than writing a second definition
of "stays inside the sandbox." reviewer/ is a RUNNER_SIDE_PACKAGES member; that group's
only forbidden imports are pr_reviewer.db, control_plane and cli
(tests/test_package_boundaries.py), so importing runner.repository_fallback from here
is allowed, and repository_fallback itself imports nothing but contracts.github and the
standard library, so no forbidden module is reachable transitively either.

The temp directory is created here, before the fetcher ever runs, and removed in a
finally that always executes: on a clean exploration, on an exception raised by the
caller inside the with-block, and on a clone-side failure (timeout, size limit, or an
unsafe path) raised by the fetcher itself.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol

from pr_reviewer.contracts.github import RepositoryIdentity
from pr_reviewer.runner.repository_fallback import (
    BoundedCloneFetcher,
    CloneSizeLimit,
    CloneTimeout,
    UnsafeRepositoryPath,
)

__all__ = [
    "CloneFetcher",
    "CloneSizeLimit",
    "CloneTimeout",
    "UnsafeRepositoryPath",
    "cloned_pull_request_head",
]

CLONE_DIR_PREFIX = "pr-reviewer-explore-"
DEFAULT_CLONE_TIMEOUT_SECONDS = 60.0
DEFAULT_CLONE_SIZE_LIMIT_BYTES = 100 * 1024 * 1024


class CloneFetcher(Protocol):
    """Structural match for BoundedCloneFetcher.materialize, so tests can pass a fake
    without touching git or the network.
    """

    def materialize(
        self,
        identity: RepositoryIdentity,
        head_sha: str,
        work_dir: Path,
        paths: list[str],
    ) -> Path: ...


@contextmanager
def cloned_pull_request_head(
    identity: RepositoryIdentity,
    head_sha: str,
    *,
    token: str | None = None,
    timeout_seconds: float = DEFAULT_CLONE_TIMEOUT_SECONDS,
    size_limit_bytes: int = DEFAULT_CLONE_SIZE_LIMIT_BYTES,
    fetcher: CloneFetcher | None = None,
) -> Iterator[Path]:
    """Yield the resolved clone root for the duration of the with-block.

    The directory is deleted in the finally below no matter how the block exits:
    normally, via an exception raised inside the block, or via an exception raised by
    materialize() itself (CloneTimeout, CloneSizeLimit, UnsafeRepositoryPath, or any
    other failure the fetcher raises before a root is ever produced).
    """
    work_dir = Path(tempfile.mkdtemp(prefix=CLONE_DIR_PREFIX))
    try:
        active_fetcher: CloneFetcher = fetcher if fetcher is not None else BoundedCloneFetcher(
            token=token,
            timeout_seconds=timeout_seconds,
            size_limit_bytes=size_limit_bytes,
        )
        root = active_fetcher.materialize(identity, head_sha, work_dir, [])
        yield root
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
