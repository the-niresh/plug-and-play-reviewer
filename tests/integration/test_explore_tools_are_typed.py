"""Failing tests for Task 35.A6's three typed tools (reviewer/tools.py).

The trap named in the task: a tool that accepts ../ reaches the host filesystem. Every
path-accepting tool is tested explicitly against a canary file placed just outside the
clone root, and the test asserts the canary's content never appears in any output, not
just that some exception was raised.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

CANARY_SECRET = "host-filesystem-secret-should-never-be-read"


def _clone_root(tmp_path: Path) -> Path:
    root = tmp_path / "clone"
    root.mkdir()
    return root


def test_read_file_args_reject_unknown_fields() -> None:
    from pr_reviewer.reviewer.tools import ReadFileArgs

    with pytest.raises(ValidationError):
        ReadFileArgs.model_validate({"path": "a.py", "start": 1, "end": 2, "shell": "rm -rf /"})


def test_grep_args_reject_unknown_fields() -> None:
    from pr_reviewer.reviewer.tools import GrepArgs

    with pytest.raises(ValidationError):
        GrepArgs.model_validate({"pattern": "foo", "command": "grep -r foo /"})


def test_list_dir_args_reject_unknown_fields() -> None:
    from pr_reviewer.reviewer.tools import ListDirArgs

    with pytest.raises(ValidationError):
        ListDirArgs.model_validate({"path": ".", "recursive": True})


def test_parse_tool_call_rejects_an_unknown_tool_name() -> None:
    from pr_reviewer.reviewer.tools import parse_tool_call

    with pytest.raises(ValueError, match="unknown tool"):
        parse_tool_call({"tool": "shell", "command": "rm -rf /"})


def test_parse_tool_call_dispatches_read_file() -> None:
    from pr_reviewer.reviewer.tools import ReadFileArgs, parse_tool_call

    call = parse_tool_call({"tool": "read_file", "path": "a.py", "start": 1, "end": 3})
    assert isinstance(call, ReadFileArgs)
    assert call.path == "a.py"


def test_read_file_returns_the_requested_line_range(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, ReadFileArgs

    root = _clone_root(tmp_path)
    (root / "app.py").write_text("one\ntwo\nthree\nfour\nfive\n")
    tools = ClonedRepositoryTools(root)

    result = tools.run(ReadFileArgs(path="app.py", start=2, end=4))

    assert result.output == "two\nthree\nfour"
    assert result.error is None


def test_read_file_rejects_a_path_that_escapes_the_clone_root_with_dotdot(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, ReadFileArgs

    root = _clone_root(tmp_path)
    (root / "app.py").write_text("safe\n")
    canary = tmp_path / "secret.txt"
    canary.write_text(CANARY_SECRET)
    tools = ClonedRepositoryTools(root)

    result = tools.run(ReadFileArgs(path="../secret.txt", start=1, end=1))

    assert CANARY_SECRET not in result.output
    assert result.error is not None
    assert "escapes the clone root" in result.error


def test_read_file_rejects_an_absolute_path(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, ReadFileArgs

    root = _clone_root(tmp_path)
    canary = tmp_path / "secret.txt"
    canary.write_text(CANARY_SECRET)
    tools = ClonedRepositoryTools(root)

    result = tools.run(ReadFileArgs(path=str(canary), start=1, end=1))

    assert CANARY_SECRET not in result.output
    assert result.error is not None


def test_list_dir_rejects_a_path_that_escapes_the_clone_root(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, ListDirArgs

    root = _clone_root(tmp_path)
    (tmp_path / "outside_dir").mkdir()
    (tmp_path / "outside_dir" / "secret.txt").write_text(CANARY_SECRET)
    tools = ClonedRepositoryTools(root)

    result = tools.run(ListDirArgs(path="../outside_dir"))

    assert result.output == ""
    assert result.error is not None
    assert "escapes the clone root" in result.error


def test_list_dir_lists_entries_inside_the_root(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, ListDirArgs

    root = _clone_root(tmp_path)
    (root / "app.py").write_text("x")
    (root / "sub").mkdir()
    tools = ClonedRepositoryTools(root)

    result = tools.run(ListDirArgs(path="."))

    assert result.output == "app.py\nsub/"


def test_grep_finds_a_pattern_within_the_clone(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, GrepArgs

    root = _clone_root(tmp_path)
    (root / "app.py").write_text("def alpha():\n    return needle\n")
    tools = ClonedRepositoryTools(root)

    result = tools.run(GrepArgs(pattern="needle", glob="**/*.py"))

    assert "app.py:2:    return needle" in result.output


def test_grep_never_returns_matches_outside_the_clone_root(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, GrepArgs

    root = _clone_root(tmp_path)
    (root / "app.py").write_text("nothing interesting\n")
    outside = tmp_path / "secret.txt"
    outside.write_text(CANARY_SECRET)
    tools = ClonedRepositoryTools(root)

    result = tools.run(GrepArgs(pattern="secret", glob="../*"))

    assert CANARY_SECRET not in result.output


def test_grep_rejects_an_invalid_pattern_without_crashing(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, GrepArgs

    root = _clone_root(tmp_path)
    tools = ClonedRepositoryTools(root)

    result = tools.run(GrepArgs(pattern="(unclosed"))

    assert result.error is not None
    assert "invalid pattern" in result.error


def test_tool_output_is_bounded_and_marked_truncated(tmp_path: Path) -> None:
    from pr_reviewer.reviewer.tools import ClonedRepositoryTools, ReadFileArgs

    root = _clone_root(tmp_path)
    (root / "big.py").write_text("x" * 20)
    tools = ClonedRepositoryTools(root, max_output_chars=5)

    result = tools.run(ReadFileArgs(path="big.py", start=1, end=1))

    assert result.truncated is True
    assert len(result.output) == 5
