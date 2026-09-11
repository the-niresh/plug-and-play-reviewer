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
    """One person per repository. Not one repository per installation.

    A repository is held by one runner at a time, and repository_assignments enforces
    that for every tier with a hard unique(repository_id). This check exists so the limit
    is explained at pairing time, in words, instead of letting someone finish GitHub
    sign-in and then meet a conflict when their runner first tries to claim.

    It is deliberately not a count. An installation may connect every repository it
    covers, and two people may hold different repositories on the same installation. The
    earlier version denied any pairing that named more than one repository and denied a
    second runner on an installation even for the same person, which is not the rule.
    """
    if installation_access_tier(conn, installation_id) != FREE_ACCESS_TIER:
        return None
    if not github_repository_ids:
        return None

    held_by_someone_else = conn.execute(
        """
        select distinct r.github_repository_id
        from repository_assignments ra
        join repositories r on r.id = ra.repository_id
        join runners ru on ru.id = ra.runner_id
        where r.installation_id = %s
          and ru.revoked_at is null
          and ru.github_user_id is distinct from %s
          and r.github_repository_id = any(%s)
        """,
        (installation_id, github_user_id, list(github_repository_ids)),
    ).fetchall()
    if held_by_someone_else:
        return "repository_claimed_by_another_user"

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
