"""Terminal colour for reviewer CLI surfaces (Task G)."""

from __future__ import annotations

import io
import json
from io import StringIO

import pytest

import pr_reviewer.runner.cli.review as review_module
from pr_reviewer.agent_surfaces.core import (
    AgentReviewRequest,
    GitHubConnectionState,
    RemediationPrompt,
    SurfaceFinding,
    SurfaceReview,
    remediation_prompt_for_finding,
)


class _TtyStdout(StringIO):
    def isatty(self) -> bool:
        return True


def test_style_emits_codes_on_tty_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("PR_REVIEWER_NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    from pr_reviewer.runner.cli.style import accent, color_enabled, ok

    stream = _TtyStdout()
    assert color_enabled(stream) is True
    assert "\x1b[" in ok("connected", stream=stream)
    assert "\x1b[" in accent("active", stream=stream)


def test_style_suppresses_codes_when_not_a_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    from pr_reviewer.runner.cli.style import error, ok

    stream = StringIO()
    assert ok("OK", stream=stream) == "OK"
    assert error("FAIL", stream=stream) == "FAIL"
    assert "\x1b" not in ok("OK", stream=stream)


def test_style_suppresses_codes_when_no_color_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "xterm-256color")

    from pr_reviewer.runner.cli.style import heading, warn

    stream = _TtyStdout()
    assert heading("Commands:", stream=stream) == "Commands:"
    assert "\x1b" not in warn("careful", stream=stream)


def test_style_suppresses_codes_when_term_is_dumb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")

    from pr_reviewer.runner.cli.style import heading

    stream = _TtyStdout()
    assert heading("Commands:", stream=stream) == "Commands:"
    assert "\x1b" not in heading("Commands:", stream=stream)


def test_force_color_enables_codes_without_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    from pr_reviewer.runner.cli.style import ok

    stream = StringIO()
    assert "\x1b[" in ok("connected", stream=stream)


def _finding(*, severity: str = "high") -> SurfaceFinding:
    return SurfaceFinding(
        id="finding-1",
        concern="correctness",
        severity=severity,
        category="null-check",
        file_path="app.py",
        line_start=12,
        line_end=12,
        title="Missing null check",
        rationale="value can be None before it is used.",
        evidence=("app.py:12",),
        confidence=0.82,
    )


class _FakeReviewBackend:
    def __init__(self, *, findings: tuple[SurfaceFinding, ...] = ()) -> None:
        self.findings = findings

    def github_connection_state(self) -> GitHubConnectionState:
        return GitHubConnectionState(connected=True, reason=None)

    def start_review(self, request: AgentReviewRequest) -> SurfaceReview:
        return SurfaceReview(
            review_id="review-1",
            owner=request.owner,
            repository=request.repository,
            pull_request=request.pull_request,
            head_sha="deadbeef00000000000000000000000000000000",
            status="complete",
            findings=self.findings,
            remediation_prompts=tuple(
                remediation_prompt_for_finding(f) for f in self.findings
            ),
        )

    def list_findings(self, review_id: str) -> tuple[SurfaceFinding, ...]:
        raise NotImplementedError

    def list_remediation_prompts(self, review_id: str) -> tuple[RemediationPrompt, ...]:
        raise NotImplementedError


def test_review_json_stays_valid_with_force_color(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr(
        review_module, "LiveAgentReviewBackend", lambda: _FakeReviewBackend(findings=(_finding(),))
    )

    stdout, stderr = StringIO(), StringIO()
    code = review_module.main(["acme/widgets#12", "--json"], stdout=stdout, stderr=stderr)

    assert code == review_module.EXIT_OK_FINDINGS
    assert stderr.getvalue() == ""
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["status"] == "ok"
    assert "\x1b" not in stdout.getvalue()


def test_setup_wizard_line_count_unchanged_with_colour(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pr_reviewer.cli.main import run_setup
    from pr_reviewer.runner.cli.setup_wizard import SetupConfig, save_setup_config
    from pr_reviewer.runner.secrets import FileSecretStore

    config_dir = tmp_path / "config"  # type: ignore[operator]
    config_dir.mkdir()
    secrets = FileSecretStore(config_dir)
    secrets.set("model_key", "sk-ant-already-set")
    save_setup_config(
        SetupConfig(
            provider_id="anthropic",
            model_id="claude-haiku-4-5-20251001",
            hosted_origin="https://control.example.test",
            prompt_name="diff_only_reviewer",
            prompt_version="1",
            custom_base_url=None,
            custom_model_id=None,
        ),
        config_dir=config_dir,
    )

    plain_out = io.StringIO()
    run_setup(
        secrets=secrets,
        read_secret=lambda _prompt: "",
        argv=["setup", "--quick"],
        stdin=io.StringIO(""),
        stdout=plain_out,
        config_dir=config_dir,
    )
    plain_lines = plain_out.getvalue().splitlines()

    monkeypatch.setenv("FORCE_COLOR", "1")
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    colour_out = _TtyStdout()
    run_setup(
        secrets=secrets,
        read_secret=lambda _prompt: "",
        argv=["setup", "--quick"],
        stdin=io.StringIO(""),
        stdout=colour_out,
        config_dir=config_dir,
    )
    colour_lines = colour_out.getvalue().splitlines()

    assert len(colour_lines) == len(plain_lines)


def test_reviewer_help_has_colour_on_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    from pr_reviewer.reviewer_entry import print_help

    stdout = _TtyStdout()
    print_help(stdout)
    assert "\x1b[" in stdout.getvalue()


def test_doctor_probe_lines_use_status_colour_on_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    from pr_reviewer.containers.runtime import ContainerProbe
    from pr_reviewer.runner.cli.doctor import _print_probe_report

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")

    probe = ContainerProbe(
        docker_cli_found=True,
        daemon_running=False,
        socket_accessible=True,
        image_pull_succeeded=True,
        runs_as_non_root=True,
        network_isolated=True,
        resource_limits_enforced=True,
        platform_supported=True,
        failures=("daemon not running",),
    )
    stdout = _TtyStdout()
    _print_probe_report(probe, stdout=stdout)
    text = stdout.getvalue()
    assert "\x1b[" in text
    assert "[OK]" in text
    assert "[FAIL]" in text
