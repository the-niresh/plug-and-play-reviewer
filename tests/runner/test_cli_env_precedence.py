"""A project .env in the working directory must not repoint the runner.

`reviewer` calls load_dotenv() to pick up development settings, and load_dotenv
searches upward from the current working directory. Any repository with its own .env
therefore used to override the runner's configured control plane, so `reviewer setup`
wrote the right value and `reviewer start` still polled the old host. Nothing said so.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RUNNER_ORIGIN = "https://runner-config.example.test"
PROJECT_ORIGIN = "https://project-dotenv.example.test"

READ_BACK = (
    "import os;"
    "from pr_reviewer.reviewer_entry import main;"
    "main(['--help']);"
    "print('RESOLVED=' + os.environ.get('PR_REVIEWER_HOSTED_ORIGIN', ''))"
)


def _run(cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        [sys.executable, "-c", READ_BACK],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    line = next(x for x in result.stdout.splitlines() if x.startswith("RESOLVED="))
    return line.removeprefix("RESOLVED=")


def test_the_runner_config_beats_a_dotenv_in_the_working_directory(tmp_path: Path) -> None:
    config_home = tmp_path / "config"
    (config_home / "pr-reviewer").mkdir(parents=True)
    (config_home / "pr-reviewer" / ".env").write_text(
        f"PR_REVIEWER_HOSTED_ORIGIN={RUNNER_ORIGIN}\n", encoding="utf-8"
    )

    project = tmp_path / "some-other-project"
    project.mkdir()
    (project / ".env").write_text(
        f"PR_REVIEWER_HOSTED_ORIGIN={PROJECT_ORIGIN}\n", encoding="utf-8"
    )

    env = {
        key: value
        for key, value in os.environ.items()
        if key != "PR_REVIEWER_HOSTED_ORIGIN"
    }
    env["XDG_CONFIG_HOME"] = str(config_home)

    assert _run(project, env) == RUNNER_ORIGIN


def test_a_project_dotenv_still_fills_a_value_the_runner_config_does_not_set(
    tmp_path: Path,
) -> None:
    """The development convenience still works; it only lost its ability to override."""
    config_home = tmp_path / "config"
    (config_home / "pr-reviewer").mkdir(parents=True)

    project = tmp_path / "some-other-project"
    project.mkdir()
    (project / ".env").write_text(
        f"PR_REVIEWER_HOSTED_ORIGIN={PROJECT_ORIGIN}\n", encoding="utf-8"
    )

    env = {
        key: value
        for key, value in os.environ.items()
        if key != "PR_REVIEWER_HOSTED_ORIGIN"
    }
    env["XDG_CONFIG_HOME"] = str(config_home)

    assert _run(project, env) == PROJECT_ORIGIN
