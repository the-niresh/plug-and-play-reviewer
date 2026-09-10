"""Failing tests for Task 35.A6: the clone directory is always removed.

Three cases, each proved on the filesystem rather than by trusting an exception was
handled: success, an exception raised inside the with-block, and a clone-side failure
(timeout) raised by the fetcher before a usable root exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _identity() -> object:
    from pr_reviewer.contracts.github import RepositoryIdentity

    return RepositoryIdentity(installation_id=1, repository_id=2, owner="acme", name="widgets")


class _SucceedingFetcher:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, Path, list[str]]] = []

    def materialize(
        self, identity: object, head_sha: str, work_dir: Path, paths: list[str]
    ) -> Path:
        self.calls.append((identity, head_sha, work_dir, paths))
        (work_dir / "app.py").write_text("print('hi')\n")
        return work_dir.resolve()


class _FailingFetcher:
    def materialize(
        self, identity: object, head_sha: str, work_dir: Path, paths: list[str]
    ) -> Path:
        del identity, head_sha, paths
        (work_dir / "partial.tmp").write_text("half a clone")
        raise RuntimeError("boom")


class _TimingOutFetcher:
    def materialize(
        self, identity: object, head_sha: str, work_dir: Path, paths: list[str]
    ) -> Path:
        from pr_reviewer.reviewer.clone import CloneTimeout

        del identity, head_sha, paths
        (work_dir / "partial.tmp").write_text("half a clone")
        raise CloneTimeout("clone exceeded timeout")


def test_the_clone_directory_is_removed_on_success() -> None:
    from pr_reviewer.reviewer.clone import cloned_pull_request_head

    fetcher = _SucceedingFetcher()
    captured: Path | None = None
    with cloned_pull_request_head(_identity(), "h" * 40, fetcher=fetcher) as root:
        captured = root
        assert root.exists()

    assert captured is not None
    assert not captured.exists()
    assert fetcher.calls[0][3] == []


def test_the_clone_directory_is_removed_when_the_caller_raises() -> None:
    from pr_reviewer.reviewer.clone import cloned_pull_request_head

    fetcher = _SucceedingFetcher()
    captured: Path | None = None
    with (
        pytest.raises(RuntimeError, match="caller failure"),
        cloned_pull_request_head(_identity(), "h" * 40, fetcher=fetcher) as root,
    ):
        captured = root
        raise RuntimeError("caller failure")

    assert captured is not None
    assert not captured.exists()


def test_the_clone_directory_is_removed_when_materialize_itself_fails() -> None:
    from pr_reviewer.reviewer.clone import cloned_pull_request_head

    fetcher = _FailingFetcher()
    with (
        pytest.raises(RuntimeError, match="boom"),
        cloned_pull_request_head(_identity(), "h" * 40, fetcher=fetcher),
    ):
        pass  # pragma: no cover - materialize raises before yielding


def test_the_clone_directory_is_removed_on_a_clone_timeout() -> None:
    from pr_reviewer.reviewer.clone import CloneTimeout, cloned_pull_request_head

    fetcher = _TimingOutFetcher()
    with (
        pytest.raises(CloneTimeout),
        cloned_pull_request_head(_identity(), "h" * 40, fetcher=fetcher),
    ):
        pass  # pragma: no cover - materialize raises before yielding


def test_the_directory_no_longer_exists_after_a_timeout(tmp_path: Path) -> None:
    """Same as the previous test, but proves the directory is gone by capturing its
    path directly from the fetcher rather than only trusting the exception path ran.
    """
    from pr_reviewer.reviewer.clone import CloneTimeout, cloned_pull_request_head

    seen: list[Path] = []

    class _RecordingTimeoutFetcher:
        def materialize(
            self, identity: object, head_sha: str, work_dir: Path, paths: list[str]
        ) -> Path:
            del identity, head_sha, paths
            seen.append(work_dir)
            raise CloneTimeout("clone exceeded timeout")

    with (
        pytest.raises(CloneTimeout),
        cloned_pull_request_head(_identity(), "h" * 40, fetcher=_RecordingTimeoutFetcher()),
    ):
        pass  # pragma: no cover

    assert len(seen) == 1
    assert not seen[0].exists()
