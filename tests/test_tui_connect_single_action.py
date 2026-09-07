"""Connect screen offers exactly one action: sign in.

That action used to be a Button. It is a PromptAction now (see
tests/test_tui_is_a_transcript.py) -- a transcript line, not a bordered widget -- but the
"exactly one action, and it says sign in" contract this test pins down has not changed.
"""

from __future__ import annotations

import asyncio

from pr_reviewer.tui.screens.connect import ConnectConfig, ConnectPanel
from pr_reviewer.tui.widgets.prompt_action import PromptAction


class FakePairingClient:
    def create_code(self, device_name: str, challenge: str) -> str:
        return "PAIR-SINGLE-1"

    def status(self, code: str, challenge: str) -> str:
        return "pending"


def test_connect_screen_offers_only_sign_in() -> None:
    async def exercise() -> None:
        from textual.app import App, ComposeResult
        from textual.widgets import Button

        class Harness(App[None]):
            def compose(self) -> ComposeResult:
                yield ConnectPanel(
                    config=ConnectConfig(
                        hosted_origin="https://reviewer.niresh.tech",
                        device_name="test-laptop",
                    ),
                    pairing_client=FakePairingClient(),
                )

        async with Harness().run_test() as pilot:
            assert not pilot.app.query(Button)
            actions = pilot.app.query(PromptAction)
            assert len(actions) == 1
            assert "sign in" in str(actions[0].render()).lower()
            assert len(pilot.app.query("#install-url")) == 0
            assert len(pilot.app.query("#sign-in-url")) == 0
            assert len(pilot.app.query("#pairing-code")) == 0

    asyncio.run(exercise())
