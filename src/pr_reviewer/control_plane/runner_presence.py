"""Runner online/offline status for the hosted dashboard."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from psycopg import Connection
from pydantic import BaseModel, ConfigDict, Field

from pr_reviewer.control_plane.github_auth import LiveInstallationAssertion
from pr_reviewer.db.client import Row, connection

RunnerPresenceStatus = Literal["online", "offline", "never_seen"]
RUNNER_ONLINE_THRESHOLD = timedelta(minutes=6)


class RunnerStatusSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    runner_id: str = Field(min_length=1)
    device_name: str = Field(min_length=1)
    installation_id: int = Field(gt=0)
    status: RunnerPresenceStatus
    last_heartbeat_at: datetime | None = None


def compute_runner_status(
    *,
    last_heartbeat_at: datetime | None,
    has_active_job: bool,
    now: datetime | None = None,
    threshold: timedelta = RUNNER_ONLINE_THRESHOLD,
) -> RunnerPresenceStatus:
    if has_active_job:
        return "online"
    if last_heartbeat_at is None:
        return "never_seen"
    clock = now or datetime.now(UTC)
    when = last_heartbeat_at
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    if clock - when <= threshold:
        return "online"
    return "offline"


def touch_runner_heartbeat(conn: Connection[Row], runner_id: object) -> None:
    conn.execute(
        """
        update runners
        set last_heartbeat_at = now()
        where id = %s
          and revoked_at is null
        """,
        (str(runner_id),),
    )


def list_runners_for_viewer(
    assertion: LiveInstallationAssertion,
    *,
    now: datetime | None = None,
) -> tuple[RunnerStatusSummary, ...]:
    installation_ids = list(assertion.installations)
    if not installation_ids:
        return ()
    with connection() as conn:
        rows = conn.execute(
            """
            select
              r.id::text as runner_id,
              r.device_name,
              r.installation_id,
              r.last_heartbeat_at,
              exists (
                select 1
                from review_jobs j
                where j.locked_by = r.id::text
                  and j.status = 'running'
                  and j.locked_until > now()
              ) as has_active_job
            from runners r
            where r.installation_id = any(%s)
              and r.github_user_id = %s
              and r.revoked_at is null
            order by r.device_name, r.id
            """,
            (installation_ids, assertion.github_user_id),
        ).fetchall()
    clock = now or datetime.now(UTC)
    return tuple(
        RunnerStatusSummary(
            runner_id=str(row["runner_id"]),
            device_name=str(row["device_name"]),
            installation_id=int(row["installation_id"]),
            status=compute_runner_status(
                last_heartbeat_at=row["last_heartbeat_at"],
                has_active_job=bool(row["has_active_job"]),
                now=clock,
            ),
            last_heartbeat_at=row["last_heartbeat_at"],
        )
        for row in rows
    )
