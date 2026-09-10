"""Runner presence timestamps and dashboard status."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_idle_claim_updates_last_heartbeat_at(
    make_verified_installation_access,
) -> None:
    from test_runner_job_protocol import (
        authenticate,
        insert_installation,
        pair_runner_assigned_to_repo,
    )

    from pr_reviewer.contracts.runner import NoJob
    from pr_reviewer.control_plane.runner_jobs import claim_job
    from pr_reviewer.db.client import connection

    installation_id = 91001
    github_repository_id = 92001
    insert_installation(installation_id)
    credential = pair_runner_assigned_to_repo(
        installation_id,
        github_repository_id,
        make_verified_installation_access,
    )
    runner = authenticate(credential.credential)
    result = claim_job(runner)
    assert isinstance(result, NoJob)
    with connection() as conn:
        row = conn.execute(
            "select last_heartbeat_at from runners where id = %s",
            (str(runner.runner_id),),
        ).fetchone()
    assert row is not None
    assert row["last_heartbeat_at"] is not None


def test_job_heartbeat_also_updates_last_heartbeat_at(
    make_verified_installation_access,
) -> None:
    from test_runner_job_protocol import (
        authenticate,
        enqueue_pull_request_job,
        insert_installation,
        pair_runner_assigned_to_repo,
    )

    from pr_reviewer.contracts.runner import JobEnvelope
    from pr_reviewer.control_plane.runner_jobs import claim_job, heartbeat_job
    from pr_reviewer.db.client import connection

    installation_id = 91002
    github_repository_id = 92002
    insert_installation(installation_id)
    credential = pair_runner_assigned_to_repo(
        installation_id,
        github_repository_id,
        make_verified_installation_access,
    )
    enqueue_pull_request_job("delivery-presence-hb", installation_id, github_repository_id)
    runner = authenticate(credential.credential)
    claimed = claim_job(runner)
    assert isinstance(claimed, JobEnvelope)
    with connection() as conn:
        before = conn.execute(
            "select last_heartbeat_at from runners where id = %s",
            (str(runner.runner_id),),
        ).fetchone()["last_heartbeat_at"]
    lease = heartbeat_job(runner.runner_id, claimed.job_id, claimed.lease_token)
    assert lease.status == "active"
    with connection() as conn:
        after = conn.execute(
            "select last_heartbeat_at from runners where id = %s",
            (str(runner.runner_id),),
        ).fetchone()["last_heartbeat_at"]
    assert after is not None
    assert before is not None
    assert after >= before


def test_compute_runner_status_prefers_active_job_over_stale_heartbeat() -> None:
    from pr_reviewer.control_plane.runner_presence import compute_runner_status

    now = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    stale = now - timedelta(hours=1)
    assert compute_runner_status(
        last_heartbeat_at=stale,
        has_active_job=True,
        now=now,
    ) == "online"


def test_compute_runner_status_marks_recent_heartbeat_online() -> None:
    from pr_reviewer.control_plane.runner_presence import compute_runner_status

    now = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    recent = now - timedelta(seconds=30)
    assert compute_runner_status(
        last_heartbeat_at=recent,
        has_active_job=False,
        now=now,
    ) == "online"


def test_compute_runner_status_marks_missing_heartbeat_never_seen() -> None:
    from pr_reviewer.control_plane.runner_presence import compute_runner_status

    now = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    assert compute_runner_status(
        last_heartbeat_at=None,
        has_active_job=False,
        now=now,
    ) == "never_seen"
