"""A credential the control plane has forgotten must not trap the terminal.

The connect screen only appears when no runner credential is stored. So when the
hosted plane started answering 401 unknown_credential, the terminal showed "sign in
again to re-pair it" on every start and offered nothing anywhere that could sign in.
The advice was correct and impossible to follow.
"""

from __future__ import annotations

from pr_reviewer.tui.auth_state import RUNNER_CREDENTIAL_SECRET, is_github_connected


class _Store:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = dict(values)

    def get(self, name: str) -> str | None:
        return self._values.get(name)

    def set(self, name: str, value: str) -> None:
        self._values[name] = value

    def delete(self, name: str) -> None:
        self._values.pop(name, None)


class _RefusingStore(_Store):
    def delete(self, name: str) -> None:
        raise RuntimeError("keyring is locked")


class _Client:
    def fetch(self, hosted_origin: str, credential: str) -> object:
        raise RuntimeError("401 unknown_credential")


def _app(store: _Store):
    """The one method under test, with only the two attributes it touches."""
    from pr_reviewer.tui.app import ReviewerApp

    app = ReviewerApp.__new__(ReviewerApp)
    app._secrets = store  # type: ignore[attr-defined]
    app._installation_client = _Client()  # type: ignore[attr-defined]
    app._installation_snapshot = None  # type: ignore[attr-defined]
    return app


def test_a_rejected_credential_is_dropped_so_the_connect_screen_can_come_back(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PR_REVIEWER_HOSTED_ORIGIN", "https://control.example.test")
    store = _Store({RUNNER_CREDENTIAL_SECRET: "stale-credential"})
    assert is_github_connected(store)  # type: ignore[arg-type]

    snapshot, message = _app(store)._fetch_installation_snapshot_from_network()

    assert snapshot is None
    assert "control.example.test" in str(message)
    assert not is_github_connected(store)  # type: ignore[arg-type]


def test_a_working_terminal_keeps_its_credential_through_one_failed_refresh(
    monkeypatch,
) -> None:
    """Only a terminal with nothing to show is at the dead end this fix is for."""
    from pr_reviewer.tui.installation_snapshot import InstallationSnapshot

    monkeypatch.setenv("PR_REVIEWER_HOSTED_ORIGIN", "https://control.example.test")
    store = _Store({RUNNER_CREDENTIAL_SECRET: "credential"})
    app = _app(store)
    app._installation_snapshot = InstallationSnapshot(  # type: ignore[attr-defined]
        github_login="someone",
        github_user_id=1,
        installation_id=2,
        repositories=(),
    )

    snapshot, message = app._fetch_installation_snapshot_from_network()

    assert snapshot is None
    assert "no longer recognised" in str(message)
    assert is_github_connected(store)  # type: ignore[arg-type]


def test_a_secret_store_that_refuses_to_delete_still_reports_the_problem(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PR_REVIEWER_HOSTED_ORIGIN", "https://control.example.test")
    store = _RefusingStore({RUNNER_CREDENTIAL_SECRET: "stale-credential"})

    snapshot, message = _app(store)._fetch_installation_snapshot_from_network()

    assert snapshot is None
    assert "no longer recognised" in str(message)
