"""Write a reviewable candidate sheet and build a holdout only from judged rows.

The writer never fills verdict, split, auditor, or labels. The builder refuses
any row whose verdict is empty. It does not guess a split.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TextIO, get_args

from pr_reviewer.evals.mine_candidates import estimate_diff_tokens, mine_eval_candidates
from pr_reviewer.evals.types import (
    Concern,
    EvalCase,
    EvalLabel,
    EvalSplit,
    assign_time_split,
)

CONCERN_CHOICES: tuple[str, ...] = get_args(Concern)


class HoldoutUnjudged(Exception):
    """A sheet row has no verdict, or an include row is missing required fields."""


@dataclass(frozen=True)
class SheetStats:
    candidate_count: int
    skipped_count: int
    per_month: dict[str, int]


def write_candidate_sheet(
    repo: Path,
    dest: Path,
    max_cases: int = 40,
    *,
    id_prefix: str = "cand",
    since: date | None = None,
    until: date | None = None,
    per_window: int | None = None,
    message_grep: str | None = None,
) -> SheetStats:
    mined = mine_eval_candidates(
        repo,
        max_cases=max_cases,
        since=since,
        until=until,
        per_window=per_window,
        message_grep=message_grep,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for index, candidate in enumerate(mined.candidates, start=1):
        committed = ""
        if candidate.committed_at is not None:
            committed = candidate.committed_at.isoformat()
        row = {
            "id": f"{id_prefix}-{index:03d}",
            "sha": candidate.sha,
            "committed_at": committed,
            "subject": candidate.source_evidence[0] if candidate.source_evidence else "",
            "files": list(candidate.files),
            "token_count": estimate_diff_tokens(candidate.diff),
            "source_evidence": list(candidate.source_evidence),
            "diff": candidate.diff,
            "verdict": "",
            "human_auditor": "",
            "split": "",
            "labels": [],
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    dest.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    per_month: dict[str, int] = {}
    for candidate in mined.candidates:
        if candidate.committed_at is None:
            continue
        key = candidate.committed_at.strftime("%Y-%m")
        per_month[key] = per_month.get(key, 0) + 1
    return SheetStats(
        candidate_count=len(mined.candidates),
        skipped_count=len(mined.skipped),
        per_month=per_month,
    )


def _parse_committed_at(value: str) -> date:
    return date.fromisoformat(value)


def build_holdout(sheet: Path, dest: Path) -> int:
    rows = [
        json.loads(line)
        for line in sheet.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cases: list[EvalCase] = []
    for row in rows:
        row_id = str(row.get("id") or "")
        verdict = str(row.get("verdict") or "").strip()
        if verdict == "":
            raise HoldoutUnjudged(f"row {row_id or '<missing id>'} is unjudged")
        if verdict == "exclude":
            continue
        if verdict != "include":
            raise HoldoutUnjudged(f"row {row_id} has unknown verdict {verdict!r}")
        auditor = str(row.get("human_auditor") or "").strip()
        split_raw = str(row.get("split") or "").strip()
        labels_raw = row.get("labels") or []
        committed_raw = str(row.get("committed_at") or "").strip()
        diff = str(row.get("diff") or "")
        evidence = row.get("source_evidence") or []
        if not auditor or split_raw not in {"dev", "holdout"} or not labels_raw:
            raise HoldoutUnjudged(
                f"row {row_id} is include but missing auditor, split, or labels"
            )
        if not committed_raw or not diff or not evidence:
            raise HoldoutUnjudged(f"row {row_id} is include but missing case fields")
        split: EvalSplit = "holdout" if split_raw == "holdout" else "dev"
        labels = [EvalLabel.model_validate(item) for item in labels_raw]
        cases.append(
            EvalCase(
                id=row_id,
                split=split,
                diff=diff,
                expected_labels=labels,
                source_evidence=list(evidence),
                human_auditor=auditor,
                committed_at=_parse_committed_at(committed_raw),
            )
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        "".join(case.model_dump_json() + "\n" for case in cases),
        encoding="utf-8",
    )
    return len(cases)


DIFF_PAGE_LINES = 40
MORE_PROMPT = "-- more -- (enter=more, q=skip rest)\n"
COMMAND_MENU = "e/exclude  i/include  s/skip  q/quit\n"

# Pretty mode: the readable screen for a real terminal. Every existing test drives
# review_sheet through a plain StringIO, which is never a tty, so the plain code
# above stays byte-compatible. Pretty rendering only fires when stdout is a tty.
_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_GREEN = "\x1b[32m"
_RED = "\x1b[31m"


def _is_pretty(stream: TextIO) -> bool:
    return bool(getattr(stream, "isatty", lambda: False)())


def _color_enabled(stdout: TextIO) -> bool:
    return _is_pretty(stdout) and "NO_COLOR" not in os.environ


def _style(text: str, *codes: str, enabled: bool) -> str:
    if not enabled or not codes:
        return text
    return "".join(codes) + text + _RESET


def _terminal_size() -> os.terminal_size:
    return shutil.get_terminal_size(fallback=(80, 24))


def _hrule(width: int) -> str:
    return "\u2500" * max(width, 10)


def _two_col(left: str, right: str, width: int, *, gap: int = 3) -> str:
    space = max(width - len(left) - len(right), gap)
    return f"{left}{' ' * space}{right}"


def _render_row_header_pretty(
    stdout: TextIO,
    row: dict[str, object],
    *,
    index: int,
    total: int,
    include_count: int,
    exclude_count: int,
    color: bool,
) -> None:
    width = _terminal_size().columns
    rule = _hrule(width)
    counts = f"{include_count} include   {exclude_count} exclude"
    stdout.write("\n")
    stdout.write(rule + "\n")
    stdout.write(" " + _two_col(f"row {index}/{total}", counts, width - 1) + "\n")
    stdout.write(rule + "\n")
    stdout.write("\n")
    committed_at = str(row.get("committed_at") or "")
    stdout.write(" " + _two_col(str(row.get("id") or ""), committed_at, width - 1) + "\n")
    subject = str(row.get("subject") or "")
    stdout.write(" " + _style(subject, _BOLD, enabled=color) + "\n")
    stdout.write("\n")
    files = row.get("files") or []
    if isinstance(files, list | tuple):
        for path in files:
            stdout.write(f" {path}\n")
    stdout.write("\n")


def _render_menu_pretty(
    stdout: TextIO, *, color: bool, page: int, total: int, has_more: bool
) -> None:
    width = _terminal_size().columns
    rule = _hrule(width)
    if has_more:
        left = " i include   e exclude   s skip   enter more   q skip diff"
    else:
        left = " i include   e exclude   s skip   q quit"
    line = _two_col(left, f"{page}/{total}", width - 1)
    stdout.write("\n")
    stdout.write(rule + "\n")
    stdout.write(_style(line, _BOLD, enabled=color) + "\n")
    stdout.write(rule + "\n")


@dataclass(frozen=True)
class _DiffLine:
    kind: str  # "file", "context", "add", "remove"
    text: str
    number: str = ""


_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def _parse_diff_lines(diff: str) -> list[_DiffLine]:
    parsed: list[_DiffLine] = []
    old_line = 0
    new_line = 0
    current_file: str | None = None
    for raw in diff.splitlines():
        if raw.startswith("diff --git") or raw.startswith("index "):
            continue
        if raw.startswith("--- "):
            continue
        if raw.startswith("+++ "):
            path = raw[4:]
            if path.startswith("b/"):
                path = path[2:]
            if path not in ("/dev/null", current_file):
                current_file = path
                parsed.append(_DiffLine(kind="file", text=current_file))
            continue
        match = _HUNK_HEADER_RE.match(raw)
        if match:
            old_line = int(match.group(1))
            new_line = int(match.group(2))
            continue
        if raw.startswith("+"):
            parsed.append(_DiffLine(kind="add", text=raw[1:], number=str(new_line)))
            new_line += 1
        elif raw.startswith("-"):
            parsed.append(_DiffLine(kind="remove", text=raw[1:], number=str(old_line)))
            old_line += 1
        else:
            content = raw[1:] if raw.startswith(" ") else raw
            parsed.append(_DiffLine(kind="context", text=content, number=str(new_line)))
            old_line += 1
            new_line += 1
    return parsed


def _render_diff_line(line: _DiffLine, *, number_width: int, color: bool) -> str:
    if line.kind == "file":
        header = f"\u2500\u2500 {line.text} " + "\u2500" * 10
        return _style(header, _BOLD, enabled=color)
    marker = {"add": "+", "remove": "-", "context": ""}[line.kind]
    label = (marker or line.number).rjust(number_width)
    rendered = f" {label}   {line.text}"
    if line.kind == "add":
        return _style(rendered, _GREEN, enabled=color)
    if line.kind == "remove":
        return _style(rendered, _RED, enabled=color)
    return _style(rendered, _DIM, enabled=color)


def _diff_page_size(file_count: int) -> int:
    # Reserve exactly what _render_row_header_pretty and _render_menu_pretty write,
    # so header + diff slice + menu always fit in one terminal height together.
    header_lines = 9 + file_count
    menu_lines = 4
    return max(_terminal_size().lines - header_lines - menu_lines, 5)


def _run_pretty_row(
    stdin: TextIO,
    stdout: TextIO,
    row: dict[str, object],
    *,
    index: int,
    total: int,
    include_count: int,
    exclude_count: int,
    color: bool,
) -> str | None:
    """Render one row (header, diff, menu) and read commands until the auditor
    picks a real action. The menu (with the page position) is printed after
    every page, including the first, and i/e/s/q are honoured immediately -
    the auditor never has to page to the end before acting on a row."""
    files = row.get("files") or []
    file_count = len(files) if isinstance(files, list | tuple) else 0
    _render_row_header_pretty(
        stdout,
        row,
        index=index,
        total=total,
        include_count=include_count,
        exclude_count=exclude_count,
        color=color,
    )
    diff_lines = _parse_diff_lines(str(row.get("diff") or "")) or [
        _DiffLine(kind="context", text="")
    ]
    number_width = max((len(dl.number) for dl in diff_lines if dl.kind != "file"), default=3)
    rendered = [_render_diff_line(dl, number_width=number_width, color=color) for dl in diff_lines]
    page_size = _diff_page_size(file_count)
    pages = [rendered[start : start + page_size] for start in range(0, len(rendered), page_size)]
    if not pages:
        pages = [[]]
    total_pages = len(pages)
    page_index = 0
    skipped = False
    stdout.write("\n".join(pages[page_index]) + "\n")
    while True:
        has_more = (not skipped) and page_index < total_pages - 1
        shown_page = total_pages if skipped else page_index + 1
        _render_menu_pretty(
            stdout, color=color, page=shown_page, total=total_pages, has_more=has_more
        )
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        token = raw.strip().lower()
        if token in {"i", "include", "e", "exclude", "s", "skip"}:
            return token
        if token == "":
            if has_more:
                page_index += 1
                stdout.write("\n".join(pages[page_index]) + "\n")
            continue
        if token in {"q", "quit"}:
            if has_more:
                # Skip the rest of THIS diff (jump to the final menu state).
                # A distinct second q, now labelled "quit", exits the review.
                skipped = True
                continue
            return "q"
        continue


def _reprompt_pretty_command(stdin: TextIO, stdout: TextIO, *, color: bool) -> str | None:
    """Re-ask for a command on a row whose diff was already fully shown, without
    redrawing it (mirrors the plain path's re-prompt on an invalid or blocked
    command)."""
    while True:
        _render_menu_pretty(stdout, color=color, page=1, total=1, has_more=False)
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        token = raw.strip().lower()
        if token in {"i", "include", "e", "exclude", "s", "skip", "q", "quit"}:
            return token
        continue


def _load_sheet_rows(sheet: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in sheet.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _atomic_write_rows(sheet: Path, rows: list[dict[str, object]]) -> None:
    tmp = sheet.with_name(sheet.name + ".tmp")
    tmp.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
    tmp.replace(sheet)


def _verdict_counts(rows: list[dict[str, object]]) -> tuple[int, int]:
    include = sum(1 for row in rows if str(row.get("verdict") or "").strip() == "include")
    exclude = sum(1 for row in rows if str(row.get("verdict") or "").strip() == "exclude")
    return include, exclude


def _read_line(stdin: TextIO) -> str | None:
    line = stdin.readline()
    if line == "":
        return None
    return line.rstrip("\n")


def _show_diff(diff: str, *, stdin: TextIO, stdout: TextIO) -> None:
    lines = diff.splitlines() or [""]
    page = DIFF_PAGE_LINES
    tty = bool(getattr(stdin, "isatty", lambda: False)())
    if not tty or len(lines) <= page:
        stdout.write(diff if diff.endswith("\n") or diff == "" else diff + "\n")
        return
    start = 0
    while start < len(lines):
        chunk = lines[start : start + page]
        stdout.write("\n".join(chunk) + "\n")
        start += page
        if start >= len(lines):
            return
        while True:
            stdout.write(MORE_PROMPT)
            stdout.flush()
            raw = _read_line(stdin)
            if raw is None:
                return
            token = raw.strip().lower()
            if token in {"q", "quit"}:
                return
            if token == "":
                break


def _pick_numbered(raw: str, options: Sequence[str]) -> str | None:
    try:
        index = int(raw.strip())
    except ValueError:
        return None
    if index < 1 or index > len(options):
        return None
    return options[index - 1]


def _parse_line_range(raw: str) -> tuple[int, int] | None:
    text = raw.strip()
    if not text:
        return None
    if "-" in text:
        left, _sep, right = text.partition("-")
        if not right or "-" in right:
            return None
        try:
            start = int(left.strip())
            end = int(right.strip())
        except ValueError:
            return None
    else:
        try:
            start = end = int(text)
        except ValueError:
            return None
    if start < 1 or end < start:
        return None
    return start, end


def _parse_json_labels(raw: str) -> list[dict[str, object]] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or not parsed:
        return None
    try:
        labels = [EvalLabel.model_validate(item) for item in parsed]
    except Exception:
        return None
    return [label.model_dump() for label in labels]


def _prompt_concern(
    stdin: TextIO,
    stdout: TextIO,
    *,
    allow_json: bool,
    pretty: bool = False,
    color: bool = False,
) -> str | list[dict[str, object]] | None:
    while True:
        if pretty:
            stdout.write("\n" + _style("concern", _BOLD, enabled=color) + "\n\n")
            for index, name in enumerate(CONCERN_CHOICES, start=1):
                stdout.write(f"  {index}. {name}\n")
            stdout.write("\n")
        else:
            stdout.write("concern (1-5, or a labels JSON array starting with [):\n")
            for index, name in enumerate(CONCERN_CHOICES, start=1):
                stdout.write(f"{index}. {name}\n")
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        stripped = raw.strip()
        if allow_json and stripped.startswith("["):
            parsed = _parse_json_labels(stripped)
            if parsed is None:
                continue
            return parsed
        picked = _pick_numbered(stripped, CONCERN_CHOICES)
        if picked is None:
            continue
        return picked


def _prompt_category(
    stdin: TextIO, stdout: TextIO, *, pretty: bool = False, color: bool = False
) -> str | None:
    while True:
        if pretty:
            stdout.write("\n" + _style("category", _BOLD, enabled=color) + "\n\n")
        else:
            stdout.write("category:\n")
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        value = raw.strip()
        if value:
            return value


def _prompt_file_path(
    stdin: TextIO,
    stdout: TextIO,
    *,
    files: Sequence[str],
    pretty: bool = False,
    color: bool = False,
) -> str | None:
    paths = tuple(path for path in files if path.strip())
    while True:
        if pretty:
            stdout.write("\n" + _style("file", _BOLD, enabled=color) + "\n\n")
            for index, path in enumerate(paths, start=1):
                stdout.write(f"  {index}. {path}\n")
            stdout.write("\n")
        else:
            stdout.write("file:\n")
            for index, path in enumerate(paths, start=1):
                stdout.write(f"{index}. {path}\n")
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        if not paths:
            continue
        picked = _pick_numbered(raw.strip(), paths)
        if picked is None:
            continue
        return picked


def _prompt_line_range(
    stdin: TextIO, stdout: TextIO, *, pretty: bool = False, color: bool = False
) -> tuple[int, int] | None:
    while True:
        if pretty:
            stdout.write("\n" + _style("line", _BOLD, enabled=color) + " (14 or 14-20)\n\n")
        else:
            stdout.write("line (14 or 14-20):\n")
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        parsed = _parse_line_range(raw)
        if parsed is None:
            continue
        return parsed


def _prompt_one_label(
    stdin: TextIO,
    stdout: TextIO,
    *,
    files: Sequence[str],
    allow_json: bool,
    pretty: bool = False,
    color: bool = False,
    existing: Sequence[str] = (),
) -> dict[str, object] | list[dict[str, object]] | None:
    if pretty and existing:
        stdout.write("\n" + _style("labels so far:", _BOLD, enabled=color) + "\n")
        for summary in existing:
            stdout.write(f"  - {summary}\n")
    concern = _prompt_concern(stdin, stdout, allow_json=allow_json, pretty=pretty, color=color)
    if concern is None:
        return None
    if isinstance(concern, list):
        return concern
    category = _prompt_category(stdin, stdout, pretty=pretty, color=color)
    if category is None:
        return None
    file_path = _prompt_file_path(stdin, stdout, files=files, pretty=pretty, color=color)
    if file_path is None:
        return None
    lines = _prompt_line_range(stdin, stdout, pretty=pretty, color=color)
    if lines is None:
        return None
    label = EvalLabel(
        concern=concern,  # type: ignore[arg-type]
        category=category,
        file_path=file_path,
        line_start=lines[0],
        line_end=lines[1],
    )
    return label.model_dump()


def _prompt_add_another(
    stdin: TextIO, stdout: TextIO, *, pretty: bool = False, color: bool = False
) -> bool | None:
    while True:
        if pretty:
            stdout.write("\n" + _style("add another label?", _BOLD, enabled=color) + " (y/n)\n\n")
        else:
            stdout.write("add another label? (y/n):\n")
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        token = raw.strip().lower()
        if token in {"y", "yes"}:
            return True
        if token in {"n", "no"}:
            return False


def _prompt_labels(
    stdin: TextIO,
    stdout: TextIO,
    *,
    files: Sequence[str],
    pretty: bool = False,
    color: bool = False,
) -> list[dict[str, object]] | None:
    labels: list[dict[str, object]] = []
    summaries: list[str] = []
    while True:
        one = _prompt_one_label(
            stdin,
            stdout,
            files=files,
            allow_json=not labels,
            pretty=pretty,
            color=color,
            existing=tuple(summaries),
        )
        if one is None:
            return None
        if isinstance(one, list):
            return one
        labels.append(one)
        summaries.append(
            f"{one['concern']}/{one['category']} "
            f"{one['file_path']}:{one['line_start']}-{one['line_end']}"
        )
        add_another = _prompt_add_another(stdin, stdout, pretty=pretty, color=color)
        if add_another is None:
            return None
        if not add_another:
            return labels


def _prompt_split(
    stdin: TextIO, stdout: TextIO, *, pretty: bool = False, color: bool = False
) -> EvalSplit | None:
    while True:
        if pretty:
            stdout.write("\n" + _style("split", _BOLD, enabled=color) + "\n\n")
            stdout.write("  1. dev\n  2. holdout\n\n")
        else:
            stdout.write("split (dev|holdout):\n")
        stdout.flush()
        raw = _read_line(stdin)
        if raw is None:
            return None
        value = raw.strip()
        if pretty:
            picked = _pick_numbered(value, ("dev", "holdout"))
            if picked is not None:
                return picked  # type: ignore[return-value]
        if value in {"dev", "holdout"}:
            return value  # type: ignore[return-value]
        # Empty and unknown values are rejected. No default.


def _split_from_committed_at(committed_at: date, holdout_after: date) -> EvalSplit:
    stub = EvalCase(
        id="derive-split",
        split="dev",
        diff="placeholder",
        expected_labels=[
            EvalLabel(
                concern="correctness",
                category="derive",
                file_path="derive.py",
                line_start=1,
                line_end=1,
            )
        ],
        source_evidence=["derive"],
        human_auditor="derive",
        committed_at=committed_at,
    )
    return assign_time_split([stub], holdout_after=holdout_after)[0].split


def review_sheet(
    sheet: Path,
    *,
    auditor: str,
    split_after: date | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> int:
    if not auditor.strip():
        raise ValueError("auditor is required")
    rows = _load_sheet_rows(sheet)
    pretty = _is_pretty(stdout)
    color = _color_enabled(stdout)
    index = 0
    shown_index: int | None = None
    while index < len(rows):
        row = rows[index]
        if str(row.get("verdict") or "").strip():
            index += 1
            continue
        if pretty:
            if shown_index != index:
                include_count, exclude_count = _verdict_counts(rows)
                command = _run_pretty_row(
                    stdin,
                    stdout,
                    row,
                    index=index + 1,
                    total=len(rows),
                    include_count=include_count,
                    exclude_count=exclude_count,
                    color=color,
                )
                shown_index = index
            else:
                command = _reprompt_pretty_command(stdin, stdout, color=color)
            if command is None:
                return 0
        else:
            if shown_index != index:
                include_count, exclude_count = _verdict_counts(rows)
                stdout.write(
                    f"row {index + 1} of {len(rows)}, "
                    f"{include_count} include, {exclude_count} exclude\n"
                )
                stdout.write(f"id: {row.get('id')}\n")
                stdout.write(f"sha: {row.get('sha')}\n")
                stdout.write(f"committed_at: {row.get('committed_at')}\n")
                stdout.write(f"subject: {row.get('subject')}\n")
                files = row.get("files") or []
                stdout.write(f"files: {files}\n")
                stdout.write("diff:\n")
                _show_diff(str(row.get("diff") or ""), stdin=stdin, stdout=stdout)
                shown_index = index
            stdout.write(COMMAND_MENU)
            stdout.flush()
            command = _read_line(stdin)
            if command is None:
                return 0
        token = command.strip().lower()
        if token in {"q", "quit"}:
            return 0
        if token in {"s", "skip"}:
            index += 1
            continue
        if token in {"e", "exclude"}:
            row["verdict"] = "exclude"
            _atomic_write_rows(sheet, rows)
            index += 1
            continue
        if token in {"i", "include"}:
            files_raw = row.get("files") or []
            file_paths = (
                tuple(str(path) for path in files_raw)
                if isinstance(files_raw, list | tuple)
                else ()
            )
            labels = _prompt_labels(stdin, stdout, files=file_paths, pretty=pretty, color=color)
            if labels is None:
                return 0
            if split_after is not None:
                committed_raw = str(row.get("committed_at") or "").strip()
                if not committed_raw:
                    stdout.write("committed_at missing; cannot derive split\n")
                    continue
                chosen_split = _split_from_committed_at(
                    date.fromisoformat(committed_raw), split_after
                )
            else:
                prompted_split = _prompt_split(stdin, stdout, pretty=pretty, color=color)
                if prompted_split is None:
                    return 0
                chosen_split = prompted_split
            row["verdict"] = "include"
            row["human_auditor"] = auditor.strip()
            row["split"] = chosen_split
            row["labels"] = labels
            _atomic_write_rows(sheet, rows)
            index += 1
            continue
        # Unknown or empty command: re-prompt this row. No default verdict.
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pr-reviewer-holdout")
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write-sheet", help="mine a repo into an unjudged JSONL sheet")
    write.add_argument("--repo", type=Path, required=True)
    write.add_argument("--out", type=Path, required=True)
    write.add_argument("--max-cases", type=int, default=40)
    write.add_argument("--id-prefix", default="cand")
    write.add_argument("--since", type=date.fromisoformat, default=None)
    write.add_argument("--until", type=date.fromisoformat, default=None)
    write.add_argument("--per-window", type=int, default=None)
    write.add_argument(
        "--grep",
        default=None,
        help="only mine commits whose message matches this extended regex (case-insensitive)",
    )
    build = sub.add_parser(
        "build-holdout", help="write judged include rows to an EvalCase JSONL"
    )
    build.add_argument("--sheet", type=Path, required=True)
    build.add_argument("--out", type=Path, required=True)
    review = sub.add_parser("review", help="judge unjudged sheet rows from a terminal")
    review.add_argument("--sheet", type=Path, required=True)
    review.add_argument("--auditor", required=True)
    review.add_argument("--split-after", type=date.fromisoformat, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "write-sheet":
            stats = write_candidate_sheet(
                args.repo,
                args.out,
                max_cases=args.max_cases,
                id_prefix=args.id_prefix,
                since=args.since,
                until=args.until,
                per_window=args.per_window,
                message_grep=args.grep,
            )
            months = ",".join(
                f"{month}:{count}" for month, count in sorted(stats.per_month.items())
            )
            print(
                f"candidates={stats.candidate_count} skipped={stats.skipped_count} "
                f"months={months} out={args.out}"
            )
            return 0
        if args.command == "review":
            return review_sheet(
                args.sheet, auditor=args.auditor, split_after=args.split_after
            )
        written = build_holdout(args.sheet, args.out)
        print(f"holdout_cases={written} out={args.out}")
        return 0
    except HoldoutUnjudged as exc:
        print(f"HoldoutUnjudged: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
