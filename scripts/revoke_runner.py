"""Revoke a runner row so its free-tier slot is released.

On the free tier one active runner holds the only slot for its installation, and a
killed runner process does not revoke its own row. That leaves the owner unable to pair
a new terminal, with the control plane saying only that pairing did not complete. There
is no dashboard button for this yet, so this is the supported way out.

    DATABASE_URL=... uv run python scripts/revoke_runner.py --list
    DATABASE_URL=... uv run python scripts/revoke_runner.py <runner-id>
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid

import psycopg
from psycopg.rows import dict_row

from pr_reviewer.config import normalize_database_url
from pr_reviewer.control_plane.repository_policy import revoke_runner


def _active_runners(database_url: str) -> list[dict[str, object]]:
    with psycopg.connect(normalize_database_url(database_url), row_factory=dict_row) as conn:
        rows = conn.execute(
            """
            select id, device_name, github_user_id, installation_id, last_heartbeat_at
            from runners
            where revoked_at is null
            order by created_at
            """
        ).fetchall()
    return [dict(row) for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runner_id", nargs="?", help="Runner id to revoke.")
    parser.add_argument("--list", action="store_true", help="Show active runners and exit.")
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    if args.list or not args.runner_id:
        rows = _active_runners(database_url)
        if not rows:
            print("No active runners.")
            return 0
        for row in rows:
            print(
                f"{row['id']}  {row['device_name']!r}  "
                f"user={row['github_user_id']}  installation={row['installation_id']}  "
                f"last_heartbeat={row['last_heartbeat_at']}"
            )
        return 0

    revoke_runner(uuid.UUID(args.runner_id))
    print(f"revoked {args.runner_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
