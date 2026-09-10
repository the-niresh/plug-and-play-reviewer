"""Windows runner autostart via Scheduled Task (runner/cli/runner_autostart.py)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pr_reviewer.runner.cli.runner_autostart import (
    FORBIDDEN_TASK_SECRET_MARKERS,
    AutostartConfig,
    build_windows_schtasks_create_argv,
    build_windows_schtasks_delete_argv,
    build_windows_schtasks_end_argv,
    build_windows_schtasks_run_argv,
    install_autostart,
    start_autostart,
    stop_autostart,
    uninstall_autostart,
)
from pr_reviewer.runner.cli.runner_autostart import (
    main as autostart_main,
)


def _config(**overrides: object) -> AutostartConfig:
    payload: dict[str, object] = {
        "hosted_origin": "https://reviewer.niresh.tech",
        "host": "127.0.0.1",
        "port": 8799,
        "reviewer_executable": r"C:\Users\test\AppData\Local\uv\reviewer.exe",
    }
    payload.update(overrides)
    return AutostartConfig(**payload)


def test_scheduled_task_command_has_no_model_key_or_secret_markers() -> None:
    argv = build_windows_schtasks_create_argv(_config())
    blob = " ".join(argv)
    for marker in FORBIDDEN_TASK_SECRET_MARKERS:
        assert marker.lower() not in blob.lower()
    tr_index = argv.index("/TR")
    command = argv[tr_index + 1]
    assert "reviewer.niresh.tech" in command
    assert "--hosted-origin https://reviewer.niresh.tech" in command
    assert "--host 127.0.0.1" in command
    assert "--port 8799" in command
    assert "model_key" not in command
    assert "sk-" not in command


def test_windows_install_start_stop_uninstall_are_routed(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(
        "pr_reviewer.runner.cli.runner_autostart.detect_platform",
        lambda: "windows",
    )

    install_autostart(_config(), platform="windows", run_command=fake_run)
    start_autostart(platform="windows", run_command=fake_run)
    stop_autostart(platform="windows", run_command=fake_run)
    uninstall_autostart(platform="windows", run_command=fake_run)

    assert calls[0][0:3] == ["schtasks", "/Create", "/TN"]
    assert "/RL" in calls[0]
    assert "LIMITED" in calls[0]
    assert "/F" in calls[0]
    assert calls[1] == build_windows_schtasks_run_argv()
    assert calls[2] == build_windows_schtasks_end_argv()
    assert calls[3] == build_windows_schtasks_delete_argv()


def test_windows_install_is_idempotent_with_force_flag() -> None:
    argv = build_windows_schtasks_create_argv(_config())
    assert "/F" in argv


def test_non_windows_platform_returns_clear_unsupported_message(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "pr_reviewer.runner.cli.runner_autostart.detect_platform",
        lambda: "freebsd",
    )
    exit_code = autostart_main(
        ["install", "--hosted-origin", "https://reviewer.niresh.tech"]
    )
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "not supported" in err.lower()
    assert "freebsd" in err


def test_install_requires_hosted_origin(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "pr_reviewer.runner.cli.runner_autostart.detect_platform",
        lambda: "windows",
    )
    monkeypatch.delenv("PR_REVIEWER_HOSTED_ORIGIN", raising=False)
    exit_code = autostart_main(["install"])
    assert exit_code == 1
    assert "hosted-origin" in capsys.readouterr().err.lower()


def test_linux_service_install_still_writes_user_unit(tmp_path: Path) -> None:
    install_autostart(
        _config(port=8741),
        platform="linux",
        home=tmp_path,
    )
    unit = tmp_path / ".config" / "systemd" / "user" / "pr-reviewer.service"
    assert unit.is_file()
