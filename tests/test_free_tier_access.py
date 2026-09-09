"""Backend enforcement for free mode: one GitHub user and one repository."""

from __future__ import annotations

import hashlib

from pr_reviewer.contracts.runner import PairingApproved, PairingDenied, RunnerCredential
from pr_reviewer.control_plane.pairing import (
    approve_pairing,
    create_pairing_code,
    exchange_pairing_code,
)
from pr_reviewer.control_plane.repository_policy import revoke_runner
from pr_reviewer.db.client import connection
from pr_reviewer.jobs import enqueue_review_job


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _insert_installation(installation_id: int) -> None:
    with connection() as conn, conn.transaction():
        conn.execute(
            "insert into installations (id, account_login) values (%s, %s)",
            (installation_id, "acme"),
        )


def _set_access_tier(installation_id: int, tier: str) -> None:
    with connection() as conn, conn.transaction():
        conn.execute(
            "update installations set access_tier = %s where id = %s",
            (tier, installation_id),
        )


def _pull_request_payload(
    *,
    installation_id: int,
    github_repository_id: int,
    pull_request_number: int = 1,
) -> dict[str, object]:
    return {
        "action": "opened",
        "installation": {"id": installation_id},
        "repository": {"id": github_repository_id, "name": "widgets"},
        "pull_request": {
            "number": pull_request_number,
            "base": {"sha": "a" * 40},
            "head": {"sha": "b" * 40},
        },
    }


def _pair_runner(
    *,
    installation_id: int,
    github_user_id: int,
    github_repository_id: int,
    device_name: str,
    verifier: str,
) -> RunnerCredential:
    from pr_reviewer.contracts.runner import VerifiedInstallationAccess

    challenge = create_pairing_code(device_name, _sha256_hex(verifier))
    access = VerifiedInstallationAccess(
        github_user_id=github_user_id,
        installation_id=installation_id,
        repositories={github_repository_id: "acme/widgets"},
    )
    approved = approve_pairing(challenge.code, access, [github_repository_id])
    assert isinstance(approved, PairingApproved)
    exchanged = exchange_pairing_code(challenge.code, verifier)
    assert isinstance(exchanged, RunnerCredential)
    return exchanged


def test_free_tier_denies_approval_of_two_repositories(
    make_verified_installation_access,
) -> None:
    installation_id = 9101
    _insert_installation(installation_id)
    challenge = create_pairing_code("laptop", _sha256_hex("v"))
    access = make_verified_installation_access(42, installation_id, {11: "a", 12: "b"})

    result = approve_pairing(challenge.code, access, [11, 12])

    assert isinstance(result, PairingDenied)
    assert result.reason == "free_tier_one_repository"


def test_free_tier_denies_a_second_github_user(
    make_verified_installation_access,
) -> None:
    installation_id = 9102
    _insert_installation(installation_id)
    _pair_runner(
        installation_id=installation_id,
        github_user_id=1001,
        github_repository_id=11,
        device_name="first-laptop",
        verifier="v1",
    )

    challenge = create_pairing_code("second-laptop", _sha256_hex("v2"))
    access = make_verified_installation_access(1002, installation_id, {11: "acme/widgets"})
    result = approve_pairing(challenge.code, access, [11])

    assert isinstance(result, PairingDenied)
    assert result.reason == "free_tier_one_user"


def test_free_tier_denies_a_second_repository_after_one_is_assigned(
    make_verified_installation_access,
) -> None:
    installation_id = 9103
    _insert_installation(installation_id)
    _pair_runner(
        installation_id=installation_id,
        github_user_id=1001,
        github_repository_id=11,
        device_name="first-laptop",
        verifier="v1",
    )

    challenge = create_pairing_code("second-laptop", _sha256_hex("v2"))
    access = make_verified_installation_access(1001, installation_id, {12: "acme/other"})
    result = approve_pairing(challenge.code, access, [12])

    assert isinstance(result, PairingDenied)
    assert result.reason == "free_tier_one_repository"


def test_free_tier_allows_repairing_after_revoke(
    make_verified_installation_access,
) -> None:
    installation_id = 9104
    _insert_installation(installation_id)
    first = _pair_runner(
        installation_id=installation_id,
        github_user_id=1001,
        github_repository_id=11,
        device_name="old-laptop",
        verifier="v1",
    )
    revoke_runner(first.runner_id)

    challenge = create_pairing_code("new-laptop", _sha256_hex("v2"))
    access = make_verified_installation_access(1001, installation_id, {12: "acme/other"})
    approved = approve_pairing(challenge.code, access, [12])
    assert isinstance(approved, PairingApproved)
    exchanged = exchange_pairing_code(challenge.code, "v2")
    assert isinstance(exchanged, RunnerCredential)


def test_free_tier_enqueue_ignores_unassigned_repository() -> None:
    installation_id = 9105
    _insert_installation(installation_id)
    _pair_runner(
        installation_id=installation_id,
        github_user_id=1001,
        github_repository_id=11,
        device_name="laptop",
        verifier="v1",
    )

    result = enqueue_review_job(
        "delivery-free-tier-ignore",
        "pull_request",
        _pull_request_payload(installation_id=installation_id, github_repository_id=22),
    )

    assert result == "ignored"
    with connection() as conn:
        row = conn.execute(
            "select count(*) as count from review_jobs where delivery_id = %s",
            ("delivery-free-tier-ignore",),
        ).fetchone()
    assert row is not None
    assert int(row["count"]) == 0


def test_free_tier_enqueue_allows_the_assigned_repository() -> None:
    installation_id = 9106
    _insert_installation(installation_id)
    _pair_runner(
        installation_id=installation_id,
        github_user_id=1001,
        github_repository_id=11,
        device_name="laptop",
        verifier="v1",
    )

    result = enqueue_review_job(
        "delivery-free-tier-allow",
        "pull_request",
        _pull_request_payload(installation_id=installation_id, github_repository_id=11),
    )

    assert result == "enqueued"


def test_team_tier_skips_free_repository_limit_at_approval(
    make_verified_installation_access,
) -> None:
    installation_id = 9107
    _insert_installation(installation_id)
    _set_access_tier(installation_id, "team")

    challenge = create_pairing_code("team-laptop", _sha256_hex("v"))
    access = make_verified_installation_access(42, installation_id, {11: "a", 12: "b"})
    result = approve_pairing(challenge.code, access, [11, 12])

    assert isinstance(result, PairingApproved)
    assert len(result.repository_ids) == 2


def test_installations_default_to_free_tier() -> None:
    installation_id = 9108
    _insert_installation(installation_id)
    with connection() as conn:
        row = conn.execute(
            "select access_tier from installations where id = %s",
            (installation_id,),
        ).fetchone()
    assert row is not None
    assert row["access_tier"] == "free"
