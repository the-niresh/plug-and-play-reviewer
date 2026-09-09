"""Product access tiers. Free mode is enforced here, not in frontend copy."""

from __future__ import annotations

from collections.abc import Sequence

from psycopg import Connection

from pr_reviewer.contracts.runner import PairingDenialReason
from pr_reviewer.db.client import Row

FREE_ACCESS_TIER = "free"
TEAM_ACCESS_TIER = "team"


def installation_access_tier(conn: Connection[Row], installation_id: int) -> str:
    row = conn.execute(
        "select access_tier from installations where id = %s",
        (installation_id,),
    ).fetchone()
    if row is None:
        return FREE_ACCESS_TIER
    return str(row["access_tier"])


def free_tier_pairing_denial(
    conn: Connection[Row],
    *,
    installation_id: int,
    github_user_id: int,
    github_repository_ids: Sequence[int],
) -> PairingDenialReason | None:
    if installation_access_tier(conn, installation_id) != FREE_ACCESS_TIER:
        return None

    if len(github_repository_ids) > 1:
        return "free_tier_one_repository"

    assigned_repos = conn.execute(
        """
        select distinct r.github_repository_id
        from repository_assignments ra
        join repositories r on r.id = ra.repository_id
        join runners ru on ru.id = ra.runner_id
        where r.installation_id = %s
          and ru.revoked_at is null
        """,
        (installation_id,),
    ).fetchall()
    assigned_ids = {int(row["github_repository_id"]) for row in assigned_repos}
    if (
        assigned_ids
        and github_repository_ids
        and github_repository_ids[0] not in assigned_ids
    ):
        return "free_tier_one_repository"

    active_users = conn.execute(
        """
        select distinct github_user_id
        from runners
        where installation_id = %s
          and revoked_at is null
          and github_user_id is not null
        """,
        (installation_id,),
    ).fetchall()
    if active_users:
        active_user_ids = {int(row["github_user_id"]) for row in active_users}
        if github_user_id not in active_user_ids:
            return "free_tier_one_user"
        return "free_tier_one_user"

    return None


def free_tier_repository_uuids_denial(
    conn: Connection[Row],
    *,
    installation_id: int,
    github_user_id: int,
    repository_uuids: Sequence[object],
) -> PairingDenialReason | None:
    if not repository_uuids:
        return free_tier_pairing_denial(
            conn,
            installation_id=installation_id,
            github_user_id=github_user_id,
            github_repository_ids=(),
        )

    rows = conn.execute(
        """
        select github_repository_id
        from repositories
        where installation_id = %s
          and id = any(%s)
        order by github_repository_id
        """,
        (installation_id, list(repository_uuids)),
    ).fetchall()
    github_repository_ids = [int(row["github_repository_id"]) for row in rows]
    return free_tier_pairing_denial(
        conn,
        installation_id=installation_id,
        github_user_id=github_user_id,
        github_repository_ids=github_repository_ids,
    )


def free_tier_enqueue_allowed(
    conn: Connection[Row],
    *,
    installation_id: int,
    github_repository_id: int,
) -> bool:
    if installation_access_tier(conn, installation_id) != FREE_ACCESS_TIER:
        return True

    assigned_repos = conn.execute(
        """
        select distinct r.github_repository_id
        from repository_assignments ra
        join repositories r on r.id = ra.repository_id
        join runners ru on ru.id = ra.runner_id
        where r.installation_id = %s
          and ru.revoked_at is null
        """,
        (installation_id,),
    ).fetchall()
    assigned_ids = {int(row["github_repository_id"]) for row in assigned_repos}
    if not assigned_ids:
        return True
    return github_repository_id in assigned_ids
