from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from test_webhook import _post_webhook, _pull_request_payload

from pr_reviewer.contracts.runner import (
    JobAcknowledgement,
    JobEnvelope,
    LeaseState,
    NoJob,
    RunnerAuthDenied,
)
from pr_reviewer.runner.secrets import FileSecretStore
from pr_reviewer.web.app import app

INSTALLATION_ID = 8601
REPOSITORY_ID = 96001
DELIVERY_ID = "delivery-c1-webhook-starts-review"


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


class RecordingReview:
    def __init__(self) -> None:
        self.reviewed_job_ids: list[str] = []

    def review(self, job: JobEnvelope) -> JobAcknowledgement:
        self.reviewed_job_ids.append(str(job.job_id))
        return JobAcknowledgement(
            terminal_state="succeeded",
            error_class=None,
            input_tokens=0,
            output_tokens=0,
            cost_usd=Decimal("0"),
            latency_ms=1,
            local_result_hash="f" * 64,
        )


def _status_for(delivery_id: str) -> str | None:
    from pr_reviewer.db.client import connection

    with connection() as conn:
        row = conn.execute(
            "select status from review_jobs where delivery_id = %s",
            (delivery_id,),
        ).fetchone()
    return None if row is None else str(row["status"])


def test_reviewer_start_turns_a_webhook_into_a_run_review(
    make_verified_installation_access: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    from test_runner_job_protocol import insert_installation, pair_runner_assigned_to_repo

    from pr_reviewer.containers.runtime import ContainerProbe
    from pr_reviewer.runner.cli import service

    insert_installation(INSTALLATION_ID)
    credential = pair_runner_assigned_to_repo(
        INSTALLATION_ID,
        REPOSITORY_ID,
        make_verified_installation_access,
        device_name="c1-webhook-device",
    )
    secrets = FileSecretStore(tmp_path / "secrets")
    secrets.set("runner_credential", credential.credential)
    hosted = TestClient(app)
    review = RecordingReview()
    claim_check = hosted.post(
        "/api/runner/jobs/claim",
        headers={"authorization": f"Bearer {credential.credential}"},
    )
    assert claim_check.status_code == 200
    assert claim_check.json() == {"status": "no_job"}

    monkeypatch.setattr(service, "default_config_dir", lambda: tmp_path)
    monkeypatch.setattr(service, "get_secret_store", lambda **kwargs: secrets)
    monkeypatch.setattr(
        service,
        "RunnerClient",
        lambda base_url, runner_credential: InProcessRunnerClient(hosted, runner_credential),
        raising=False,
    )
    monkeypatch.setattr(
        service, "build_review_executor", lambda *_args, **_kwargs: review, raising=False
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
        response = _post_webhook(
            hosted,
            DELIVERY_ID,
            _pull_request_payload(
                action="opened",
                installation_id=INSTALLATION_ID,
                repository_id=REPOSITORY_ID,
            ),
        )
        assert response.status_code == 202
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            if review.reviewed_job_ids and _status_for(DELIVERY_ID) == "succeeded":
                return
            time.sleep(0.02)
        raise AssertionError(
            "expected reviewer start to run the review and acknowledge the webhook-enqueued job"
        )

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
    assert len(review.reviewed_job_ids) == 1
