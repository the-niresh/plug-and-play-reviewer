from __future__ import annotations

import os
import sys
from pathlib import Path

_TESTS_ROOT = Path(__file__).resolve().parent
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))
for _subdir in sorted(_TESTS_ROOT.iterdir()):
    if _subdir.is_dir() and not _subdir.name.startswith(("_", ".")):
        _entry = str(_subdir)
        if _entry not in sys.path:
            sys.path.insert(0, _entry)

from collections.abc import Callable, Iterator  # noqa: E402

import pytest  # noqa: E402

from pr_reviewer.config import default_database_url  # noqa: E402

os.environ["DATABASE_URL"] = default_database_url()
os.environ["GITHUB_WEBHOOK_SECRET"] = "test-secret"

from pr_reviewer.contracts.runner import VerifiedInstallationAccess  # noqa: E402
from pr_reviewer.db.client import close_pool, connection  # noqa: E402
from pr_reviewer.db.migrate import migrate  # noqa: E402

migrate()


@pytest.fixture
def make_verified_installation_access() -> (
    Callable[[int, int, dict[int, str] | None], VerifiedInstallationAccess]
):
    """Test-only construction of VerifiedInstallationAccess.

    VerifiedInstallationAccess has exactly one real construction site in src/
    (control_plane/github_oauth.py's verify_installation_access, which calls GitHub's own
    /user/installations), enforced by
    test_verified_installation_access_construction_site_is_exactly_github_oauth in
    tests/test_github_oauth.py. Tests need a way to build one anyway, so this factory lives in
    tests/conftest.py, outside the src/ scan that check enforces, rather than adding a second
    construction site to production code. A fixture, not a plain importable function, because
    tests/ has no __init__.py and is not set up as an importable package.

    repositories maps github_repository_id -> name, the same shape GitHub's own response would
    give the real verifier. Defaults to empty for tests that never call approve_pairing with a
    non-empty repository_ids list.
    """

    def factory(
        github_user_id: int, installation_id: int, repositories: dict[int, str] | None = None
    ) -> VerifiedInstallationAccess:
        return VerifiedInstallationAccess(
            github_user_id=github_user_id,
            installation_id=installation_id,
            repositories=repositories or {},
        )

    return factory


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    with connection() as conn, conn.transaction():
        conn.execute(
            """
            truncate
              review_comment_feedback,
              review_comment_posts,
              repository_budget_reservations,
              repository_budgets,
              connector_circuits,
              notification_channels,
              connector_runs,
              model_calls,
              agent_events,
              review_jobs,
              github_deliveries,
              prompt_versions,
              pairing_codes,
              oauth_states,
              repository_assignments,
              runners,
              repositories,
              installations
            restart identity cascade
            """
        )
    yield


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    del session, exitstatus
    close_pool()

@pytest.fixture(autouse=True)
def _isolate_runner_config(tmp_path_factory, monkeypatch):
    """Keep tests out of the developer's real ~/.config/pr-reviewer.

    default_config_dir() resolves from XDG_CONFIG_HOME, and any test that builds a real
    SecretStore or runs the setup wizard without passing config_dir writes there. One did:
    a live setup.json was found holding the fixture value https://control.example.test,
    which pointed a real runner at a control plane that does not exist.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path_factory.mktemp("xdg-config")))
