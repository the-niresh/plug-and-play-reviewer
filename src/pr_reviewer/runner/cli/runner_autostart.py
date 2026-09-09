"""Install the local runner to start at login (Windows Scheduled Task first).

Secrets stay in the user's existing secret store. The autostart command only passes
the hosted origin and loopback bind flags to `reviewer start`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from pr_reviewer.runner.cli.service import (
    _DEFAULT_PORT,
    LocalServiceError,
    install_user_service,
    stop_local_service,
)

WINDOWS_TASK_NAME = "PR Reviewer"
FORBIDDEN_TASK_SECRET_MARKERS = (
    "model_key",
    "runner_credential",
    "OPENAI_",
    "ANTHROPIC_",
    "sk-",
    "ghp_",
    "gho_",
)

CommandRunner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class AutostartConfig:
    hosted_origin: str
    host: str = "127.0.0.1"
    port: int = _DEFAULT_PORT
    reviewer_executable: str = "reviewer"


def detect_platform() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith("linux"):
        return "linux"
    return sys.platform


def resolve_reviewer_executable() -> str:
    found = shutil.which("reviewer")
    if found:
        return found
    return "reviewer"


def build_windows_task_command(config: AutostartConfig) -> str:
    """Build the schtasks /TR string. Must never embed secrets."""
    exe = config.reviewer_executable
    if " " in exe and not (exe.startswith('"') and exe.endswith('"')):
        exe = f'"{exe}"'
    return (
        f"{exe} start "
        f"--hosted-origin {config.hosted_origin} "
        f"--host {config.host} "
        f"--port {config.port}"
    )


def build_windows_schtasks_create_argv(config: AutostartConfig) -> list[str]:
    return [
        "schtasks",
        "/Create",
        "/TN",
        WINDOWS_TASK_NAME,
        "/TR",
        build_windows_task_command(config),
        "/SC",
        "ONLOGON",
        "/RL",
        "LIMITED",
        "/F",
    ]


def build_windows_schtasks_run_argv() -> list[str]:
    return ["schtasks", "/Run", "/TN", WINDOWS_TASK_NAME]


def build_windows_schtasks_delete_argv() -> list[str]:
    return ["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"]


def build_windows_schtasks_end_argv() -> list[str]:
    return ["schtasks", "/End", "/TN", WINDOWS_TASK_NAME]


def install_autostart(
    config: AutostartConfig,
    *,
    platform: str,
    home: Path | None = None,
    run_command: CommandRunner | None = None,
) -> None:
    runner = run_command if run_command is not None else _default_run_command
    if platform == "windows":
        argv = build_windows_schtasks_create_argv(config)
        _assert_task_has_no_secrets(argv)
        _run_checked(runner, argv)
        return
    if platform in {"linux", "darwin"}:
        install_user_service(platform=platform, home=home or Path.home())
        return
    raise LocalServiceError(
        f"reviewer service install is not supported on {platform!r}; "
        "use Windows, Linux, or macOS"
    )


def start_autostart(
    *,
    platform: str,
    run_command: CommandRunner | None = None,
) -> None:
    runner = run_command if run_command is not None else _default_run_command
    if platform == "windows":
        _run_checked(runner, build_windows_schtasks_run_argv())
        return
    if platform == "linux":
        _run_checked(
            runner,
            ["systemctl", "--user", "start", "pr-reviewer.service"],
        )
        return
    if platform == "darwin":
        _run_checked(
            runner,
            ["launchctl", "kickstart", "-k", "gui/$(id -u)/com.pr-reviewer"],
        )
        return
    raise LocalServiceError(
        f"reviewer service start is not supported on {platform!r}; "
        "use Windows, Linux, or macOS"
    )


def stop_autostart(
    *,
    platform: str,
    run_command: CommandRunner | None = None,
) -> int:
    runner = run_command if run_command is not None else _default_run_command
    if platform == "windows":
        runner(build_windows_schtasks_end_argv())
        return stop_local_service()
    if platform == "linux":
        _run_checked(runner, ["systemctl", "--user", "stop", "pr-reviewer.service"])
        return stop_local_service()
    if platform == "darwin":
        _run_checked(runner, ["launchctl", "bootout", "gui/$(id -u)", "com.pr-reviewer"])
        return stop_local_service()
    raise LocalServiceError(
        f"reviewer service stop is not supported on {platform!r}; "
        "use Windows, Linux, or macOS"
    )


def uninstall_autostart(
    *,
    platform: str,
    home: Path | None = None,
    run_command: CommandRunner | None = None,
) -> None:
    runner = run_command if run_command is not None else _default_run_command
    if platform == "windows":
        _run_checked(runner, build_windows_schtasks_delete_argv())
        return
    if platform == "linux":
        unit = (home or Path.home()) / ".config" / "systemd" / "user" / "pr-reviewer.service"
        _run_checked(
            runner,
            ["systemctl", "--user", "disable", "--now", "pr-reviewer.service"],
        )
        unit.unlink(missing_ok=True)
        return
    if platform == "darwin":
        plist = (home or Path.home()) / "Library" / "LaunchAgents" / "com.pr-reviewer.plist"
        _run_checked(runner, ["launchctl", "bootout", "gui/$(id -u)", "com.pr-reviewer"])
        plist.unlink(missing_ok=True)
        return
    raise LocalServiceError(
        f"reviewer service uninstall is not supported on {platform!r}; "
        "use Windows, Linux, or macOS"
    )


def _assert_task_has_no_secrets(argv: Sequence[str]) -> None:
    blob = " ".join(argv).lower()
    for marker in FORBIDDEN_TASK_SECRET_MARKERS:
        if marker.lower() in blob:
            raise LocalServiceError(
                f"refusing to create a scheduled task that contains {marker!r}"
            )


def _run_checked(runner: CommandRunner, argv: Sequence[str]) -> None:
    result = runner(list(argv))
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise LocalServiceError(
            f"command failed ({result.returncode}): {' '.join(argv)}"
            + (f": {detail}" if detail else "")
        )


def _default_run_command(argv: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=True,
    )


def _parse_config(rest: Sequence[str]) -> AutostartConfig:
    parser = argparse.ArgumentParser(prog="reviewer service")
    parser.add_argument(
        "--hosted-origin",
        default=os.environ.get("PR_REVIEWER_HOSTED_ORIGIN", ""),
        help="Hosted control plane origin, for example https://reviewer.niresh.tech.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host for reviewer start.")
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT, help="Loopback port.")
    parsed = parser.parse_args(list(rest))
    if not parsed.hosted_origin:
        raise LocalServiceError(
            "PR_REVIEWER_HOSTED_ORIGIN or --hosted-origin is required"
        )
    if parsed.host != "127.0.0.1":
        raise LocalServiceError(f"onboarding binds 127.0.0.1 only, not {parsed.host!r}")
    return AutostartConfig(
        hosted_origin=parsed.hosted_origin,
        host=parsed.host,
        port=parsed.port,
        reviewer_executable=resolve_reviewer_executable(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print(_HELP, file=sys.stderr if args else sys.stdout)
        return 0 if args else 1
    command, rest = args[0], args[1:]
    platform = detect_platform()
    try:
        if command == "install":
            config = _parse_config(rest)
            install_autostart(config, platform=platform)
            print(f"installed autostart on {platform}")
            return 0
        if command == "start":
            if rest and rest[0].startswith("-"):
                _parse_config(rest)
            start_autostart(platform=platform)
            print("started")
            return 0
        if command == "stop":
            if rest and rest[0].startswith("-"):
                _parse_config(rest)
            stop_autostart(platform=platform)
            print("stopped")
            return 0
        if command == "uninstall":
            if rest and rest[0].startswith("-"):
                _parse_config(rest)
            uninstall_autostart(platform=platform)
            print("uninstalled autostart")
            return 0
    except LocalServiceError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"reviewer service: unknown command {command!r}\n{_HELP}", file=sys.stderr)
    return 1


_HELP = """\
usage: reviewer service <install|start|stop|uninstall> [options]

Install the local runner to start after login without storing secrets in the task.

  install     Create or update the platform autostart entry (Windows Scheduled Task).
  start       Start the autostart runner now.
  stop        Stop the running runner and end the scheduled task session when possible.
  uninstall   Remove the autostart entry.

Options (install requires --hosted-origin or PR_REVIEWER_HOSTED_ORIGIN):
  --hosted-origin URL   Hosted control plane origin.
  --host 127.0.0.1      Loopback bind address (127.0.0.1 only).
  --port PORT           Loopback port (default 8741).

Windows uses a per-user Scheduled Task (/RL LIMITED, no administrator rights).
Linux writes ~/.config/systemd/user/pr-reviewer.service.
macOS writes ~/Library/LaunchAgents/com.pr-reviewer.plist.
"""
