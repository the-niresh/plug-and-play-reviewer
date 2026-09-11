"""`reviewer login --no-tui`: sign in from a plain terminal.

The TUI used to be compulsory for sign-in, which is also where the link was hardest to
get at: inside a full-screen app it is not ordinary terminal text, so copying it needed
OSC 52 (ignored by macOS Terminal.app) or a clipboard tool, and opening it needed browser
detection that was wrong on macOS. Printing the link sidesteps all three.
"""

from __future__ import annotations

import pytest


class _FakeClient:
    def __init__(self) -> None:
        self.created: tuple[str, str] | None = None
        self.exchanged: tuple[str, str] | None = None

    def create_code(self, device_name: str, challenge: str) -> str:
        self.created = (device_name, challenge)
        return "PAIRCODE"

    def status(self, code: str, challenge: str):  # type: ignore[no-untyped-def]
        raise AssertionError("wait_for_pairing is stubbed in these tests")

    def exchange(self, code: str, proof: str) -> str:
        self.exchanged = (code, proof)
        return "runner-credential-value"


def _patch(monkeypatch: pytest.MonkeyPatch, client: _FakeClient, store: dict[str, str]) -> None:
    import pr_reviewer.runner.cli.login as login

    monkeypatch.setattr(login, "resolved_hosted_origin", lambda: "https://control.example.test")
    monkeypatch.setattr(login, "HostedPairingClient", lambda origin: client)
    monkeypatch.setattr(
        login,
        "build_github_sign_in_url",
        lambda origin, pairing_code: f"{origin}/s?c={pairing_code}",
    )
    monkeypatch.setattr(login, "wait_for_pairing", lambda **_kwargs: None)

    class _Store:
        def set(self, name: str, value: str) -> None:
            store[name] = value

        def get(self, name: str) -> str | None:
            return store.get(name)

        def delete(self, name: str) -> None:
            store.pop(name, None)

    monkeypatch.setattr(login, "get_secret_store", lambda **_kwargs: _Store())


def test_the_link_is_printed_as_plain_text_on_its_own_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from pr_reviewer.runner.cli.login import main

    client = _FakeClient()
    _patch(monkeypatch, client, {})

    assert main(["--device-name", "macbook"]) == 0

    lines = [line.strip() for line in capsys.readouterr().out.splitlines()]
    # On its own line so a double-click selects the whole URL, and terminals that
    # linkify URLs can find it. Nothing may share the line with it.
    assert "https://control.example.test/s?c=PAIRCODE" in lines


def test_the_stored_credential_comes_from_the_exchange_not_from_approval(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    from pr_reviewer.runner.cli.login import RUNNER_CREDENTIAL_SECRET, main

    client = _FakeClient()
    store: dict[str, str] = {}
    _patch(monkeypatch, client, store)

    assert main([]) == 0
    assert store[RUNNER_CREDENTIAL_SECRET] == "runner-credential-value"


def test_only_the_hash_of_the_verifier_reaches_the_control_plane(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verifier proves ownership at exchange time, so it must never be sent earlier."""
    from pr_reviewer.runner.cli.login import main
    from pr_reviewer.tui.screens.connect import sha256_hex

    client = _FakeClient()
    _patch(monkeypatch, client, {})

    assert main([]) == 0
    assert client.created is not None and client.exchanged is not None
    _device, challenge = client.created
    _code, verifier = client.exchanged
    assert challenge == sha256_hex(verifier)
    assert challenge != verifier


def test_a_failed_exchange_is_not_reported_as_signed_in(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Approval is not sign-in: the exchange can still fail after the browser half worked."""
    from pr_reviewer.runner.cli.login import main

    class _Failing(_FakeClient):
        def exchange(self, code: str, proof: str) -> str:
            raise RuntimeError("boom")

    store: dict[str, str] = {}
    _patch(monkeypatch, _Failing(), store)

    assert main([]) == 1
    assert store == {}
    assert "signed in as" not in capsys.readouterr().out.lower()
