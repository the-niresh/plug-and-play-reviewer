"""Mining must be able to target bug-fix commits by message, not just a date window.

A later commit fixing a bug an earlier commit introduced is the defensible label this
track needs. The message is still evidence, not ground truth: a human judges the sheet.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def _init_git_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "eval@test.example"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Eval Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def _commit_file(repo: Path, relative: str, content: str, message: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "--", relative], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True)


def test_message_grep_keeps_only_bugfix_commits(tmp_path: Path) -> None:
    from pr_reviewer.evals.mine_candidates import mine_eval_candidates

    repo = _init_git_repo(tmp_path)
    _commit_file(repo, "src/widget.py", "WIDGET = 1\n", "add widget helper")
    _commit_file(repo, "src/widget.py", "WIDGET = 2\n", "Fix crash when widget is None")
    _commit_file(repo, "src/beta.py", "BETA = 1\n", "document beta flag")
    _commit_file(repo, "src/gamma.py", "GAMMA = 1\n", "fix off-by-one bug in gamma loop")

    mined = mine_eval_candidates(repo, max_cases=10, message_grep="fix|bug").candidates
    subjects = {item.source_evidence[0] for item in mined}

    assert subjects == {
        "Fix crash when widget is None",
        "fix off-by-one bug in gamma loop",
    }


def test_message_grep_none_keeps_every_commit(tmp_path: Path) -> None:
    from pr_reviewer.evals.mine_candidates import mine_eval_candidates

    repo = _init_git_repo(tmp_path)
    _commit_file(repo, "src/widget.py", "WIDGET = 1\n", "add widget helper")
    _commit_file(repo, "src/beta.py", "BETA = 1\n", "document beta flag")

    mined = mine_eval_candidates(repo, max_cases=10).candidates
    assert len(mined) == 2


def test_write_candidate_sheet_accepts_grep_and_cli_exposes_it(tmp_path: Path) -> None:
    from pr_reviewer.evals.holdout_sheet import main, write_candidate_sheet

    repo = _init_git_repo(tmp_path)
    _commit_file(repo, "src/widget.py", "WIDGET = 1\n", "add widget helper")
    _commit_file(repo, "src/widget.py", "WIDGET = 2\n", "fix null check in widget")

    sheet = tmp_path / "sheet.jsonl"
    stats = write_candidate_sheet(repo, sheet, max_cases=10, message_grep="fix")
    assert stats.candidate_count == 1

    cli_sheet = tmp_path / "cli_sheet.jsonl"
    code = main(
        [
            "write-sheet",
            "--repo",
            str(repo),
            "--out",
            str(cli_sheet),
            "--grep",
            "fix",
        ]
    )
    assert code == 0
    lines = [line for line in cli_sheet.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
