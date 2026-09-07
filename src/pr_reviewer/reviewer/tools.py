"""Three typed tools over a cloned, read-only repository. Our code runs them.

Each tool's arguments are a frozen pydantic model with extra="forbid", the same
guarantee SandboxJob (verification/docker_sandbox.py) uses to make an unconstructable
shell string impossible rather than merely rejected at runtime. The model can request
a tool by name with a JSON object; it never supplies a command string, and nothing
here calls a shell or a subprocess.

Every path argument is validated against the clone root with
runner.repository_fallback.assert_path_stays_inside before any filesystem access. That
function is reused, not reimplemented, so there is exactly one definition in this
codebase of what "stays inside the sandbox" means.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pr_reviewer.runner.repository_fallback import UnsafeRepositoryPath, assert_path_stays_inside

DEFAULT_MAX_OUTPUT_CHARS = 4000
DEFAULT_MAX_GREP_MATCHES = 200


class ReadFileArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: Literal["read_file"] = "read_file"
    path: str = Field(min_length=1)
    start: int = Field(ge=1)
    end: int = Field(ge=1)


class GrepArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: Literal["grep"] = "grep"
    pattern: str = Field(min_length=1)
    glob: str = Field(default="**/*", min_length=1)


class ListDirArgs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: Literal["list_dir"] = "list_dir"
    path: str = Field(default=".", min_length=1)


ToolCall = ReadFileArgs | GrepArgs | ListDirArgs
_TOOL_MODELS: dict[str, type[ReadFileArgs] | type[GrepArgs] | type[ListDirArgs]] = {
    "read_file": ReadFileArgs,
    "grep": GrepArgs,
    "list_dir": ListDirArgs,
}


def parse_tool_call(raw: object) -> ToolCall:
    """Validate untyped model JSON into exactly one of the three typed tool calls.

    extra="forbid" on each model means a field the human did not define cannot survive
    validation; an unknown "tool" value is rejected here, before any model is tried.
    """
    if not isinstance(raw, dict):
        raise ValueError("tool call must be a JSON object")
    tool = raw.get("tool")
    model = _TOOL_MODELS.get(tool) if isinstance(tool, str) else None
    if model is None:
        raise ValueError(f"unknown tool: {tool!r}")
    return model.model_validate(raw)


class ToolResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tool: str
    output: str
    truncated: bool = False
    error: str | None = None


class ClonedRepositoryTools:
    """Executes typed tool calls against files under a cloned, read-only root."""

    def __init__(
        self,
        root: Path,
        *,
        max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
        max_grep_matches: int = DEFAULT_MAX_GREP_MATCHES,
    ) -> None:
        self._root = root.resolve()
        self._max_output_chars = max_output_chars
        self._max_grep_matches = max_grep_matches

    def run(self, call: ToolCall) -> ToolResult:
        if isinstance(call, ReadFileArgs):
            return self._read_file(call)
        if isinstance(call, GrepArgs):
            return self._grep(call)
        return self._list_dir(call)

    def _read_file(self, args: ReadFileArgs) -> ToolResult:
        try:
            target = assert_path_stays_inside(self._root, args.path)
        except UnsafeRepositoryPath:
            return ToolResult(
                tool="read_file", output="", error=f"path escapes the clone root: {args.path}"
            )
        if not target.is_file():
            return ToolResult(tool="read_file", output="", error=f"not a file: {args.path}")
        lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        selected = lines[max(args.start - 1, 0) : args.end]
        return self._bounded("read_file", "\n".join(selected))

    def _grep(self, args: GrepArgs) -> ToolResult:
        try:
            pattern = re.compile(args.pattern)
        except re.error as exc:
            return ToolResult(tool="grep", output="", error=f"invalid pattern: {exc}")
        matches: list[str] = []
        for candidate in sorted(self._root.rglob(args.glob)):
            if len(matches) >= self._max_grep_matches:
                break
            if not candidate.is_file() or not _is_inside(self._root, candidate.resolve()):
                continue
            try:
                text = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            relative = candidate.relative_to(self._root)
            for line_number, line in enumerate(text.splitlines(), start=1):
                if pattern.search(line):
                    matches.append(f"{relative}:{line_number}:{line}")
                    if len(matches) >= self._max_grep_matches:
                        break
        return self._bounded("grep", "\n".join(matches))

    def _list_dir(self, args: ListDirArgs) -> ToolResult:
        try:
            target = assert_path_stays_inside(self._root, args.path)
        except UnsafeRepositoryPath:
            return ToolResult(
                tool="list_dir", output="", error=f"path escapes the clone root: {args.path}"
            )
        if not target.is_dir():
            return ToolResult(tool="list_dir", output="", error=f"not a directory: {args.path}")
        entries = sorted(entry.name + ("/" if entry.is_dir() else "") for entry in target.iterdir())
        return self._bounded("list_dir", "\n".join(entries))

    def _bounded(self, tool: str, text: str) -> ToolResult:
        if len(text) > self._max_output_chars:
            return ToolResult(tool=tool, output=text[: self._max_output_chars], truncated=True)
        return ToolResult(tool=tool, output=text)


def _is_inside(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True
