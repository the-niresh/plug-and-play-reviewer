"""Hosted dashboard runner status on /api/reviews."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pr_reviewer.control_plane.app import app
from pr_reviewer.control_plane.github_auth import LiveInstallationAssertion
from pr_reviewer.control_plane.github_oauth import LIVE_SIGN_IN_COOKIE_NAME, issue_live_sign_in
from pr_reviewer.db.client import connection


def _client(cookie: str | None = None) -> TestClient:
    cookies = {LIVE_SIGN_IN_COOKIE_NAME: cookie} if cookie is not None else {}
    return TestClient(app, cookies=cookies)


def _signed_in_cookie(installations: dict[int, dict[int, str]]) -> str:
    assertion = LiveInstallationAssertion(
        github_user_id=42, installations=installations, expires_at=2_000_000_000
    )
    return issue_live_sign_in(assertion)


def test_reviews_api_includes_runner_status_for_the_signed_in_viewer() -> None:
    installation_id = 93001
    github_repository_id = 94001
    with connection() as conn, conn.transaction():
        conn.execute(
            "insert into installations (id, account_login) values (%s, 'acme')",
            (installation_id,),
        )
        repo = conn.execute(
            """
            insert into repositories (installation_id, github_repository_id, name)
            values (%s, %s, 'widgets')
            returning id
            """,
            (installation_id, github_repository_id),
        ).fetchone()
        runner = conn.execute(
            """
            insert into runners (
              device_name, credential_hash, mode, platform, version,
              github_user_id, installation_id, last_heartbeat_at
            )
            values ('laptop', 'hash-1', 'full', 'linux-amd64', '0.1.0', 42, %s, now())
            returning id
            """,
            (installation_id,),
        ).fetchone()
        conn.execute(
            "insert into repository_assignments (repository_id, runner_id) values (%s, %s)",
            (repo["id"], runner["id"]),
        )

    cookie = _signed_in_cookie({installation_id: {github_repository_id: "acme/widgets"}})
    response = _client(cookie).get("/api/reviews")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["runners"]) == 1
    assert payload["runners"][0]["device_name"] == "laptop"
    assert payload["runners"][0]["status"] == "online"


def test_reviews_api_hides_runners_for_other_github_users() -> None:
    installation_id = 93002
    github_repository_id = 94002
    with connection() as conn, conn.transaction():
        conn.execute(
            "insert into installations (id, account_login) values (%s, 'acme')",
            (installation_id,),
        )
        conn.execute(
            """
            insert into runners (
              device_name, credential_hash, mode, platform, version,
              github_user_id, installation_id, last_heartbeat_at
            )
            values ('other-user', 'hash-2', 'full', 'linux-amd64', '0.1.0', 99, %s, now())
            """,
            (installation_id,),
        )

    cookie = _signed_in_cookie({installation_id: {github_repository_id: "acme/widgets"}})
    response = _client(cookie).get("/api/reviews")
    assert response.status_code == 200
    assert response.json()["runners"] == []
