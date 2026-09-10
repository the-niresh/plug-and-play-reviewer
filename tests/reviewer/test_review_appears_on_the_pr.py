from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_runner_job_protocol import insert_installation, pair_runner_assigned_to_repo
from test_webhook import _post_webhook, _pull_request_payload

from pr_reviewer.contracts.finding_candidate import FindingCandidate
from pr_reviewer.contracts.review_context import ReviewOutcome
from pr_reviewer.contracts.runner import (
    GitHubJobToken,
    JobAcknowledgement,
    JobEnvelope,
    LeaseState,
    NoJob,
    RunnerAuthDenied,
)
from pr_reviewer.db.client import connection
from pr_reviewer.github.post_review import PostedReview, ReviewSubmission
from pr_reviewer.runner.secrets import FileSecretStore
from pr_reviewer.web.app import app

INSTALLATION_ID = 8701
REPOSITORY_ID = 97001
FIRST_DELIVERY = "delivery-c2-first"
SECOND_DELIVERY = "delivery-c2-redelivery"
PATCH = "@@ -1,2 +1,3 @@\n def foo():\n     return 1\n+    return 2\n"


class FakeGitHubReviews:
    def __init__(self) -> None:
        self.submissions: list[ReviewSubmission] = []
        self.reviews: list[PostedReview] = []

    def submit(self, submission: ReviewSubmission) -> PostedReview:
        self.submissions.append(submission)
        posted = PostedReview(
            github_review_id=f"rev-{len(self.submissions)}",
            comment_ids=tuple(f"c-{idx}" for idx, _ in enumerate(submission.comments, start=1)),
            response_status=201,
            body=submission.body,
            comments=submission.comments,
        )
        self.reviews.append(posted)
        return posted


class InProcessRunnerClient:
    def __init__(self, test_client: TestClient, credential: str) -> None:
        self._test_client = test_client
        self._credential = credential

    def set_credential(self, credential: str) -> None:
        self._credential = credential

    def claim(self) -> JobEnvelope | NoJob | RunnerAuthDenied:
        response = self._test_client.post(
            "/api/runner/jobs/claim",
            headers={"authorization": f"Bearer {self._credential}"},
        )
        if response.status_code == 401:
            detail = str(response.json().get("detail", "unknown_credential"))
            reason = "revoked_runner" if detail == "revoked_runner" else "unknown_credential"
            return RunnerAuthDenied(reason=reason)
        payload = response.json()
        if payload.get("status") == "no_job" or payload == {}:
            return NoJob()
        return JobEnvelope.model_validate(payload)

    def heartbeat(self, job_id: str, lease_token: str) -> LeaseState:
        response = self._test_client.post(
            f"/api/runner/jobs/{job_id}/heartbeat",
            headers={"authorization": f"Bearer {self._credential}"},
            json={"lease_token": lease_token},
        )
        return LeaseState.model_validate(response.json())

    def acknowledge(self, job_id: str, lease_token: str, result: JobAcknowledgement) -> None:
        response = self._test_client.post(
            f"/api/runner/jobs/{job_id}/ack",
            headers={"authorization": f"Bearer {self._credential}"},
            json={"lease_token": lease_token, "result": result.model_dump(mode="json")},
        )
        assert response.status_code == 200

    def issue_job_token(self, job_id: str, lease_token: str) -> GitHubJobToken:
        del job_id, lease_token
        return GitHubJobToken(
            token="test-installation-token",
            github_repository_id=REPOSITORY_ID,
            expires_at=datetime.now(UTC),
        )

    def issue_job_post_token(self, job_id: str, lease_token: str) -> GitHubJobToken:
        return self.issue_job_token(job_id, lease_token)


def _job_state_for(delivery_id: str) -> tuple[str | None, str | None]:
    with connection() as conn:
        row = conn.execute(
            "select status, last_error from review_jobs where delivery_id = %s",
            (delivery_id,),
        ).fetchone()
    if row is None:
        return None, None
    return str(row["status"]), None if row["last_error"] is None else str(row["last_error"])


def _wait_until(predicate: Any, *, timeout_seconds: float, error: str) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError(error)


def test_redelivered_webhook_does_not_post_a_second_comment(
    make_verified_installation_access: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from pr_reviewer.containers.runtime import ContainerProbe
    from pr_reviewer.github.pull_request import PullRequestFile, PullRequestSnapshot
    from pr_reviewer.runner.cli import service

    insert_installation(INSTALLATION_ID)
    credential = pair_runner_assigned_to_repo(
        INSTALLATION_ID,
        REPOSITORY_ID,
        make_verified_installation_access,
        device_name="c2-webhook-device",
    )
    secrets = FileSecretStore(tmp_path / "secrets")
    secrets.set("runner_credential", credential.credential)
    secrets.set("model_key", "model-key-for-c2")

    hosted = TestClient(app)
    fake_github = FakeGitHubReviews()
    payload = _pull_request_payload(
        action="opened",
        installation_id=INSTALLATION_ID,
        repository_id=REPOSITORY_ID,
    )
    snapshot = PullRequestSnapshot(
        repo_owner="acme",
        repo_name="widgets",
        number=int(payload["pull_request"]["number"]),
        base_sha=str(payload["pull_request"]["base"]["sha"]),
        head_sha=str(payload["pull_request"]["head"]["sha"]),
        title="Fix widget",
        body="Synthetic PR body",
        files=[PullRequestFile(path="app.py", status="modified", patch=PATCH, previous_path=None)],
    )

    # Drive the claim loop fast. The production interval is 10s so a single runner does
    # not hammer the control plane; this test asserts behaviour, not pacing, and would
    # otherwise just wait out its own deadline.
    monkeypatch.setattr(service, "_RUNNER_POLL_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(service, "default_config_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "get_secret_store", lambda **_kwargs: secrets)
    monkeypatch.setattr(
        service,
        "RunnerClient",
        lambda _base_url, runner_credential: InProcessRunnerClient(hosted, runner_credential),
    )
    monkeypatch.setattr(service, "fetch_job_snapshot", lambda _job, _token: snapshot)
    monkeypatch.setattr(
        service,
        "incremental_review_pull_request",
        lambda *_args, **_kwargs: ReviewOutcome(
            candidates=(
                FindingCandidate(
                    concern="correctness",
                    severity="medium",
                    category="null-check",
                    file_path="app.py",
                    line_start=3,
                    line_end=3,
                    title="Return value changed",
                    rationale="foo now returns 2.",
                    evidence=["app.py:3"],
                    confidence=0.8,
                ),
            ),
            packing_strategy_version="v1",
            covers_all_changed_files=True,
            omitted_files=(),
            cancelled=False,
        ),
    )
    monkeypatch.setattr(
        service,
        "submit_review_to_github",
        lambda _ref, submission, _token: fake_github.submit(submission),
    )
    monkeypatch.setattr(
        service,
        "list_pull_request_reviews",
        lambda _ref, _token: tuple(fake_github.reviews),
    )
    monkeypatch.setattr(
        service,
        "_probe",
        lambda: ContainerProbe(
            docker_cli_found=True,
            daemon_running=True,
            socket_accessible=True,
            image_pull_succeeded=True,
            runs_as_non_root=True,
            network_isolated=True,
            resource_limits_enforced=True,
            platform_supported=True,
            failures=(),
        ),
    )

    def fake_run_server(_onboarding_app: object, *, host: str, port: int) -> None:
        del _onboarding_app, host, port
        first = _post_webhook(hosted, FIRST_DELIVERY, payload)
        assert first.status_code == 202
        _wait_until(
            lambda: _job_state_for(FIRST_DELIVERY)[0] in {"succeeded", "failed"},
            timeout_seconds=1.5,
            error="expected first webhook delivery to finish",
        )
        first_status, first_error = _job_state_for(FIRST_DELIVERY)
        assert first_status == "succeeded", first_error
        assert len(fake_github.submissions) == 1

        second = _post_webhook(hosted, SECOND_DELIVERY, payload)
        assert second.status_code == 202
        _wait_until(
            lambda: _job_state_for(SECOND_DELIVERY)[0] in {"succeeded", "failed"},
            timeout_seconds=1.5,
            error="expected redelivered webhook job to complete",
        )
        second_status, second_error = _job_state_for(SECOND_DELIVERY)
        assert second_status == "succeeded", second_error
        assert len(fake_github.submissions) == 1
        assert "<!-- pr-reviewer:post:" in fake_github.submissions[0].body

    monkeypatch.setattr(service, "_uvicorn_run", fake_run_server)

    exit_code = service.main(
        [
            "start",
            "--host",
            "127.0.0.1",
            "--port",
            "8741",
            "--hosted-origin",
            "https://control.example.test",
        ]
    )
    assert exit_code == 0
