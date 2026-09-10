"""Operator CLI for captured human review-comment feedback."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from pr_reviewer.control_plane.feedback_improvement import (
    build_feedback_improvement_report_from_hosted,
    render_feedback_improvement_report,
)
from pr_reviewer.db.client import close_pool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reviewer feedback",
        description=(
            "Read hosted review-comment feedback and print human-reviewable "
            "improvement candidates."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    candidates = subparsers.add_parser(
        "candidates",
        help="Print safe improvement candidates from captured feedback.",
    )
    candidates.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Print machine-readable JSON instead of the human report.",
    )
    return parser


def run(args: Sequence[str]) -> int:
    parser = build_parser()
    parsed = parser.parse_args(args)
    if parsed.command != "candidates":
        parser.print_help(sys.stderr)
        return 1

    report = build_feedback_improvement_report_from_hosted()
    if parsed.as_json:
        print(json.dumps(report.model_dump(mode="json"), indent=2))
        return 0

    _print_feedback_report(render_feedback_improvement_report(report))
    return 0


def _print_feedback_report(text: str) -> None:
    from pr_reviewer.runner.cli.style import heading, ok, warn

    for line in text.splitlines():
        if line.startswith("# ") or line.startswith("## "):
            print(heading(line, stream=sys.stdout))
        elif line.startswith("Duplicates skipped:"):
            count = line.split(":", 1)[1].strip()
            print(f"Duplicates skipped: {warn(count, stream=sys.stdout)}")
        elif line.startswith("Positive signals:"):
            count = line.split(":", 1)[1].strip()
            print(f"Positive signals: {ok(count, stream=sys.stdout)}")
        else:
            print(line)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run(sys.argv[1:] if argv is None else argv)
    finally:
        close_pool()


if __name__ == "__main__":
    raise SystemExit(main())
