"""Local user service and reviewer start|stop|status|open (Runtime Task 8).

Installs a systemd --user unit on Linux or a LaunchAgent on macOS, both under the user's home
directory. A destination that would need administrator rights is refused with a clear error
instead of silently calling sudo.

reviewer start binds the loopback onboarding app with uvicorn so the user unit can actually
restart it after login. reviewer open prints the loopback URL when no graphical browser exists.
A headless VPS is a normal install target.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import secrets as secrets_lib
import signal
import socket
import sys
import threading
import time
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal, cast

from pr_reviewer.agent_surfaces.backend import resolve_model_provider
from pr_reviewer.containers.runtime import ContainerProbe
from pr_reviewer.context_budget import context_budget_for_model
from pr_reviewer.contracts.finding import Finding
from pr_reviewer.contracts.github import PullRequestRef
from pr_reviewer.contracts.review_context import FilePatch, ReviewOutcome
from pr_reviewer.contracts.runner import JobAcknowledgement, JobEnvelope, LeaseState
from pr_reviewer.github.post_review import (
    PostedReview,
    RouteDecision,
    StalePullRequestHead,
    list_pull_request_reviews,
    post_review,
    posting_idempotency_key,
    submit_review_to_github,
)
from pr_reviewer.github.pull_request import PullRequestSnapshot
from pr_reviewer.local_store.repo_config import RepoConfigStore, default_repo_config_path
from pr_reviewer.local_store.sqlite import LocalStore
from pr_reviewer.reviewer.diff_budget import pack_diff
from pr_reviewer.reviewer.hunk_format import render_hunks
from pr_reviewer.reviewer.incremental import incremental_review_pull_request
from pr_reviewer.reviewer.review_cache import LocalReviewCache
from pr_reviewer.reviewer.specialists import (
    BuiltinSpecialistReviewers,
    apply_enabled_specialists,
    get_enabled_specialists,
)
from pr_reviewer.runner.client import RunnerClient
from pr_reviewer.runner.daemon import ReviewExecutor, RunnerDaemon, open_or_recover_local_store
from pr_reviewer.runner.github_access import fetch_job_snapshot
from pr_reviewer.runner.modes import RuntimeMode
from pr_reviewer.runner.secrets import SecretStore, default_config_dir, get_secret_store

LINUX_UNIT_RELATIVE = Path(".config") / "systemd" / "user" / "pr-reviewer.service"
DARWIN_PLIST_RELATIVE = Path("Library") / "LaunchAgents" / "com.pr-reviewer.plist"
_DEFAULT_PORT = 8741
_SESSION_SECRET_NAME = "local_session_secret"
_RUNNER_CREDENTIAL_SECRET = "runner_credential"
_LOCAL_STATE_DB_NAME = "local_state.sqlite3"
_RUNNER_STOP_DEADLINE_SECONDS = 1.0
_RUNNER_POLL_INTERVAL_SECONDS = 0.1

logger = logging.getLogger(__name__)


class LocalServiceError(RuntimeError):
    """The user service cannot be installed or the requested destination needs elevation."""


@dataclass(frozen=True)
class ServiceStatus:
    running: bool
    bound_host: str
    url: str


def install_user_service(
    *,
    platform: str,
    home: Path,
    destination: Path | None = None,
) -> Path:
    target = destination if destination is not None else _default_destination(platform, home)
    _refuse_system_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if platform == "linux":
        target.write_text(_linux_unit(), encoding="utf-8")
    elif platform == "darwin":
        target.write_text(_darwin_plist(), encoding="utf-8")
    else:
        raise LocalServiceError(f"unsupported platform {platform!r}")
    return target


def local_service_status(*, host: str, port: int) -> ServiceStatus:
    running = _port_open(host, port)
    return ServiceStatus(
        running=running,
        bound_host=host,
        url=f"http://{host}:{port}/onboarding",
    )


def open_local_ui(
    *,
    url: str,
    browser_open: Callable[[str], bool] | None = None,
) -> int:
    opener = browser_open if browser_open is not None else webbrowser.open
    opened = False
    try:
        opened = bool(opener(url))
    except OSError:
        opened = False
    if not opened:
        print(url)
    return 0


def start_local_onboarding(
    *,
    host: str,
    port: int,
    hosted_origin: str,
    probe: ContainerProbe | None = None,
    secrets: SecretStore | None = None,
    run_server: Callable[..., None] | None = None,
    requested_mode: RuntimeMode = "full",
    start_runner_daemon: bool = False,
) -> None:
    from pr_reviewer.runner.web.local_auth import PendingPairingClient, create_local_onboarding_app

    if host != "127.0.0.1":
        raise LocalServiceError(f"onboarding binds 127.0.0.1 only, not {host!r}")

    active_probe = probe if probe is not None else _probe()
    store = secrets if secrets is not None else get_secret_store(
        file_fallback_directory=default_config_dir()
    )
    session_secret = store.get(_SESSION_SECRET_NAME)
    if not session_secret:
        session_secret = secrets_lib.token_urlsafe(32)
        store.set(_SESSION_SECRET_NAME, session_secret)

    app = create_local_onboarding_app(
        host=host,
        session_secret=session_secret,
        secrets=store,
        pairing_client=PendingPairingClient(hosted_origin),
        probe=active_probe,
        requested_mode=requested_mode,
        hosted_origin=hosted_origin,
    )
    pid_path = _data_dir() / "onboarding.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    runner_stop_event = threading.Event()
    runner_thread: threading.Thread | None = None
    if start_runner_daemon:
        runner_thread = threading.Thread(
            target=_run_runner_daemon_until_stopped,
            kwargs={
                "hosted_origin": hosted_origin,
                "secrets": store,
                "stop_event": runner_stop_event,
            },
            daemon=True,
        )
        runner_thread.start()
    runner = run_server if run_server is not None else _uvicorn_run
    try:
        runner(app, host=host, port=port)
    finally:
        if runner_thread is not None:
            runner_stop_event.set()
            runner_thread.join(timeout=_RUNNER_STOP_DEADLINE_SECONDS)
        pid_path.unlink(missing_ok=True)


def stop_local_service() -> int:
    pid_path = _data_dir() / "onboarding.pid"
    if not pid_path.is_file():
        print("not running")
        return 0
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except ValueError:
        pid_path.unlink(missing_ok=True)
        print("not running")
        return 0
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pid_path.unlink(missing_ok=True)
        print("not running")
        return 0
    print("stopped")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: reviewer <start|stop|status|open> [args...]", file=sys.stderr)
        return 1
    command, rest = args[0], args[1:]
    parser = argparse.ArgumentParser(
        prog=f"reviewer {command}",
        description=f"Run the local onboarding service command `{command}`.",
        epilog=_service_epilog(command),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--port", type=int, default=_DEFAULT_PORT, help="Loopback port.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback host.")
    parser.add_argument(
        "--hosted-origin",
        default=os.environ.get("PR_REVIEWER_HOSTED_ORIGIN", ""),
        help="Hosted control plane origin, for example https://reviewer.niresh.tech.",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "analysis_only"],
        default="full",
        help="Requested local review mode.",
    )
    parsed = parser.parse_args(rest)
    url = f"http://127.0.0.1:{parsed.port}/onboarding"

    if command == "status":
        status = local_service_status(host=parsed.host, port=parsed.port)
        print("running" if status.running else "not running")
        return 0 if status.running else 1
    if command == "open":
        return open_local_ui(url=url)
    if command == "start":
        from pr_reviewer.runner.web.local_auth import LocalAuthError

        if parsed.host != "127.0.0.1":
            print(f"onboarding binds 127.0.0.1 only, not {parsed.host!r}", file=sys.stderr)
            return 1
        if not parsed.hosted_origin:
            print(
                "PR_REVIEWER_HOSTED_ORIGIN or --hosted-origin is required",
                file=sys.stderr,
            )
            return 1
        try:
            start_local_onboarding(
                host=parsed.host,
                port=parsed.port,
                hosted_origin=parsed.hosted_origin,
                requested_mode=cast(RuntimeMode, parsed.mode),
                start_runner_daemon=True,
            )
        except (LocalServiceError, LocalAuthError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0
    if command == "stop":
        return stop_local_service()
    print(f"reviewer: unknown service command {command!r}", file=sys.stderr)
    return 1


def _service_epilog(command: str) -> str:
    outputs = {
        "start": "Output: uvicorn logs on stderr and stdout while the server runs.",
        "stop": "Output: `stopped` or `not running`.",
        "status": "Output: `running` or `not running`.",
        "open": "Output: opens the local URL, or prints it if no browser is available.",
    }
    output = outputs.get(command, "Output: command-specific human text.")
    return (
        f"{output}\n\n"
        "exit codes:\n"
        "  0  command succeeded\n"
        "  1  command failed or required state is missing\n"
    )


def _probe() -> ContainerProbe:
    from pr_reviewer.containers.docker import DockerRuntime

    return DockerRuntime().probe()


def _uvicorn_run(app: object, *, host: str, port: int) -> None:
    import uvicorn
    from fastapi import FastAPI

    if not isinstance(app, FastAPI):
        raise TypeError("onboarding server requires a FastAPI app")
    uvicorn.run(app, host=host, port=port)


class DiffOnlyRunnerReviewExecutor:
    def __init__(self, *, runner_client: RunnerClient, secrets: SecretStore) -> None:
        self._runner_client = runner_client
        self._secrets = secrets
        self._posted_reviews: dict[str, PostedReview] = {}

    def review(self, job: JobEnvelope) -> JobAcknowledgement:
        started = time.monotonic()
        model_key = self._secrets.get("model_key")
        if not model_key:
            return _failed_ack(job=job, started=started, error_class="missing_model_key")

        try:
            token = self._runner_client.issue_job_token(str(job.job_id), job.lease_token)
            snapshot = fetch_job_snapshot(job, token)
            resolved = resolve_model_provider(self._secrets)
            if resolved is None:
                return _failed_ack(job=job, started=started, error_class="missing_model_key")
            _provider_name, model = resolved
            choice = RepoConfigStore(default_repo_config_path()).get_model_choice(
                job.repository_id
            )
            model_name = choice.model_id
            packed = pack_diff(snapshot, context_budget_for_model(model_name), _count_tokens)
            store = open_or_recover_local_store(default_config_dir() / _LOCAL_STATE_DB_NAME)
            outcome = incremental_review_pull_request(
                snapshot,
                model,
                model_name=model_name,
                cache=LocalReviewCache(store),
                installation_id=job.installation_id,
                repository_id=job.repository_id,
                heartbeat=lambda: self._heartbeat(job),
            )
            config_path = default_repo_config_path()
            if get_enabled_specialists(config_path, job.repository_id):
                tracker = BuiltinSpecialistReviewers(model, model_name)
                outcome = apply_enabled_specialists(
                    outcome,
                    snapshot,
                    packed,
                    [],
                    config_path=config_path,
                    github_repository_id=job.repository_id,
                    reviewers=tracker.reviewers,
                    cost_tracker=tracker,
                )
            if outcome.cancelled:
                return _failed_ack(job=job, started=started, error_class="cancelled")
            post_token = self._runner_client.issue_job_post_token(
                str(job.job_id), job.lease_token
            )
            self._post_review_outcome(
                job=job,
                snapshot=snapshot,
                token=post_token.token,
                outcome=outcome,
            )
        except Exception as exc:  # noqa: BLE001
            return _failed_ack(job=job, started=started, error_class=type(exc).__name__)

        digest = hashlib.sha256(
            f"{job.job_id}:{job.head_sha}:{len(outcome.candidates)}".encode()
        ).hexdigest()
        latency_ms = int((time.monotonic() - started) * 1000)
        return JobAcknowledgement(
            terminal_state="succeeded",
            error_class=None,
            input_tokens=0,
            output_tokens=0,
            cost_usd=Decimal("0"),
            latency_ms=max(latency_ms, 0),
            local_result_hash=digest,
        )

    def _heartbeat(self, job: JobEnvelope) -> LeaseState:
        return self._runner_client.heartbeat(str(job.job_id), job.lease_token)

    def _post_review_outcome(
        self,
        *,
        job: JobEnvelope,
        snapshot: PullRequestSnapshot,
        token: str,
        outcome: ReviewOutcome,
    ) -> None:
        findings = _findings_with_route_decisions(job=job, outcome=outcome)
        if not findings:
            return
        ref = PullRequestRef(
            owner=snapshot.repo_owner,
            repository=snapshot.repo_name,
            number=snapshot.number,
        )
        idempotency_key = posting_idempotency_key(ref, snapshot.head_sha, job.policy_version)
        patches = tuple(
            FilePatch(path=file.path, patch=file.patch or "", previous_path=file.previous_path)
            for file in snapshot.files
        )
        try:
            post_review(
                ref,
                snapshot.head_sha,
                findings,
                idempotency_key,
                patches=patches,
                current_head_sha=lambda: fetch_job_snapshot(
                    job,
                    self._runner_client.issue_job_token(str(job.job_id), job.lease_token),
                ).head_sha,
                submit=lambda submission: submit_review_to_github(ref, submission, token),
                list_reviews=lambda target_ref: list_pull_request_reviews(target_ref, token),
                render_hunks=render_hunks,
                lookup=self._posted_reviews.get,
                record_post=lambda posted: self._posted_reviews.__setitem__(
                    posted.idempotency_key, posted
                ),
            )
        except StalePullRequestHead:
            return


def build_review_executor(
    *,
    local_store: LocalStore,
    runner_client: RunnerClient,
    secrets: SecretStore,
) -> ReviewExecutor:
    del local_store
    return DiffOnlyRunnerReviewExecutor(runner_client=runner_client, secrets=secrets)


def _build_runner_daemon(*, hosted_origin: str, secrets: SecretStore) -> RunnerDaemon:
    config_dir = default_config_dir()
    credential = secrets.get(_RUNNER_CREDENTIAL_SECRET) or ""
    runner_client = RunnerClient(hosted_origin, credential)
    local_store = open_or_recover_local_store(config_dir / _LOCAL_STATE_DB_NAME)
    review = build_review_executor(
        local_store=local_store, runner_client=runner_client, secrets=secrets
    )
    return RunnerDaemon(
        runner_client=runner_client,
        local_store=local_store,
        secret_store=secrets,
        review=review,
        poll_interval_seconds=_RUNNER_POLL_INTERVAL_SECONDS,
    )


def _run_runner_daemon_until_stopped(
    *,
    hosted_origin: str,
    secrets: SecretStore,
    stop_event: threading.Event,
) -> None:
    daemon = _build_runner_daemon(hosted_origin=hosted_origin, secrets=secrets)
    daemon.recover()
    daemon.replay_pending_acknowledgements()
    while not stop_event.is_set():
        try:
            daemon.process_once()
        except Exception as exc:  # noqa: BLE001
            logger.warning("runner daemon loop error: %s", exc)
        stop_event.wait(_RUNNER_POLL_INTERVAL_SECONDS)


def _count_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _failed_ack(
    *,
    job: JobEnvelope,
    started: float,
    error_class: str,
) -> JobAcknowledgement:
    digest = hashlib.sha256(
        f"{job.job_id}:{job.head_sha}:{error_class}".encode()
    ).hexdigest()
    latency_ms = int((time.monotonic() - started) * 1000)
    return JobAcknowledgement(
        terminal_state="failed",
        error_class=error_class,
        input_tokens=0,
        output_tokens=0,
        cost_usd=Decimal("0"),
        latency_ms=max(latency_ms, 0),
        local_result_hash=digest,
    )


def _findings_with_route_decisions(
    *,
    job: JobEnvelope,
    outcome: ReviewOutcome,
) -> tuple[tuple[Finding, RouteDecision], ...]:
    mapped: list[tuple[Finding, RouteDecision]] = []
    for index, candidate in enumerate(outcome.candidates):
        allow_public_post = candidate.concern != "security"
        confidentiality: Literal["ordinary", "restricted"] = (
            "ordinary" if allow_public_post else "restricted"
        )
        finding = Finding(
            id=f"{job.job_id}:{index + 1}",
            review_job_id=str(job.job_id),
            concern=candidate.concern,
            severity=candidate.severity,
            category=candidate.category,
            file_path=candidate.file_path,
            line_start=candidate.line_start,
            line_end=candidate.line_end,
            title=candidate.title,
            rationale=candidate.rationale,
            evidence=list(candidate.evidence),
            confidence=candidate.confidence,
            verified=True,
            verification_method="static",
            public_safe=allow_public_post,
            status="draft",
            suggested_fix=candidate.suggested_fix,
        )
        mapped.append(
            (
                finding,
                RouteDecision(
                    allow_public_post=allow_public_post,
                    confidentiality=confidentiality,
                ),
            )
        )
    return tuple(mapped)


def _data_dir() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "pr-reviewer"
    return Path.home() / ".local" / "share" / "pr-reviewer"


def _default_destination(platform: str, home: Path) -> Path:
    if platform == "linux":
        return home / LINUX_UNIT_RELATIVE
    if platform == "darwin":
        return home / DARWIN_PLIST_RELATIVE
    raise LocalServiceError(f"unsupported platform {platform!r}")


def _refuse_system_path(destination: Path) -> None:
    text = str(destination)
    if text.startswith("/etc/") or "/Library/LaunchDaemons/" in text:
        raise LocalServiceError(
            "refusing a system path that needs administrator elevation; "
            "install the user unit under the home directory instead"
        )


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _linux_unit() -> str:
    return (
        "[Unit]\n"
        "Description=PR Reviewer local runner\n"
        "\n"
        "[Service]\n"
        "ExecStart=reviewer start\n"
        "Restart=on-failure\n"
        "\n"
        "[Install]\n"
        "WantedBy=default.target\n"
    )


def _darwin_plist() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.pr-reviewer</string>
  <key>ProgramArguments</key>
  <array>
    <string>reviewer</string>
    <string>start</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
</dict>
</plist>
"""
