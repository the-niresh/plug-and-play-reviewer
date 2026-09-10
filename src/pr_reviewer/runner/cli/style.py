"""ANSI styling for reviewer CLI surfaces."""

from __future__ import annotations

import os
import sys
from typing import TextIO

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_RED = "\x1b[31m"
_CYAN = "\x1b[36m"


def color_enabled(stream: TextIO | None = None) -> bool:
    if "NO_COLOR" in os.environ:
        return False
    if os.environ.get("PR_REVIEWER_NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    target = stream if stream is not None else sys.stdout
    if not getattr(target, "isatty", lambda: False)():
        return False
    term = os.environ.get("TERM")
    return bool(term and term != "dumb")


def _style(text: str, code: str, *, stream: TextIO | None = None) -> str:
    if not color_enabled(stream):
        return text
    return f"{code}{text}{_RESET}"


def heading(text: str, *, stream: TextIO | None = None) -> str:
    return _style(text, _BOLD, stream=stream)


def label(text: str, *, stream: TextIO | None = None) -> str:
    return _style(text, _BOLD, stream=stream)


def value(text: str, *, stream: TextIO | None = None) -> str:
    return text


def ok(text: str, *, stream: TextIO | None = None) -> str:
    return _style(text, _GREEN, stream=stream)


def warn(text: str, *, stream: TextIO | None = None) -> str:
    return _style(text, _YELLOW, stream=stream)


def error(text: str, *, stream: TextIO | None = None) -> str:
    return _style(text, _RED, stream=stream)


def dim(text: str, *, stream: TextIO | None = None) -> str:
    return _style(text, _DIM, stream=stream)


def accent(text: str, *, stream: TextIO | None = None) -> str:
    return _style(text, _CYAN, stream=stream)


def path(text: str, *, stream: TextIO | None = None) -> str:
    return dim(text, stream=stream)
