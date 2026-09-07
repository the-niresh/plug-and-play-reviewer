"""The sign-in screen is a transcript, not a form.

D1's whole point: Button, Label and Static inside a bordered, padded panel read like a
web form, and Niresh called that unusable. These tests pin down the two concrete rules so
the old style cannot creep back in: no Button widget anywhere on the connect screen, and
no CSS container declares a border, on either the connect screen or the review screen.
"""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.widgets import Button

from pr_reviewer.tui.screens.connect import ConnectConfig, ConnectPanel
from pr_reviewer.tui.screens.review import ReviewPanel


class FakePairingClient:
    def __init__(self) -> None:
        self.create_calls: list[tuple[str, str]] = []

    def create_code(self, device_name: str, challenge: str) -> str:
        self.create_calls.append((device_name, challenge))
        return "PAIR-TRANSCRIPT-1"

    def status(self, code: str, challenge: str) -> str:
        return "pending"

    def exchange(self, code: str, proof: str) -> str:
        return "runner-credential"


def make_connect_harness() -> App[None]:
    class Harness(App[None]):
        def compose(self) -> ComposeResult:
            yield ConnectPanel(
                config=ConnectConfig(
                    hosted_origin="https://reviewer.niresh.tech",
                    device_name="test-laptop",
                ),
                pairing_client=FakePairingClient(),
                # Short and fast: FakePairingClient.status never resolves past "pending",
                # so a real 300s deadline would leave the worker thread running for the
                # full wait and the test process joining it at shutdown -- the exact
                # leaked-thread cost AGENTS.md warns about.
                pairing_deadline_seconds=0.2,
                pairing_poll_interval=0.01,
            )

    return Harness()


def test_connect_screen_has_no_button_widget() -> None:
    """The sign-in action must not be a Button -- that is the whole form look."""

    async def exercise() -> None:
        async with make_connect_harness().run_test() as pilot:
            assert not pilot.app.query(Button)

    asyncio.run(exercise())


def test_connect_screen_declares_no_border() -> None:
    """A form hides behind boxes. A transcript has none."""
    assert "border" not in ConnectPanel.DEFAULT_CSS.lower()


def test_review_screen_declares_no_border() -> None:
    """Same rule for the review path: a finding is a transcript row, not a bordered card."""
    assert "border" not in ReviewPanel.DEFAULT_CSS.lower()


def test_sign_in_still_works_without_a_button() -> None:
    """Removing the Button must not remove the behaviour -- clicking the prompt line still
    starts the same sign-in flow it always did."""

    async def exercise() -> None:
        async with make_connect_harness().run_test() as pilot:
            await pilot.click("#connect-sign-in")
            for _ in range(200):
                if pilot.app.query("#sign-in-url"):
                    break
                await pilot.pause()
            assert pilot.app.query("#sign-in-url")
            url_text = str(pilot.app.query_one("#sign-in-url").render())
            assert "PAIR-TRANSCRIPT-1" in url_text

    asyncio.run(exercise())
