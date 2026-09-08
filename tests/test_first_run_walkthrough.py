"""First run walks the shared onboarding state machine in the terminal.

The point of 35.D2 is not that onboarding.py exists -- it is that the TUI renders
ONBOARDING_STEPS from onboarding/state.py and calls validate_step for every advance,
without keeping its own copy of the step list or validation rules.
"""

from __future__ import annotations

import asyncio

from pr_reviewer.onboarding.state import ONBOARDING_STEPS
from pr_reviewer.onboarding.state import validate_step as real_validate_step


def _advance_through_first_repository(panel) -> None:
    assert panel.try_advance({"provider": "openai"})
    assert panel.try_advance({"key": "sk-test-key"})
    assert panel.try_advance({"project_description": "A compliance SaaS for food safety."})
    assert panel.try_advance({"repository": "acme/alpha", "index_requested": True})
    assert panel.try_advance({"signed_in": True, "selected_repository_ids": [11, 12]})
    assert panel.try_advance({"run_location": "local"})


def test_onboarding_panel_steps_are_the_shared_state_machine() -> None:
    from pr_reviewer.tui.onboarding import OnboardingPanel

    panel = OnboardingPanel(repositories=("acme/alpha",))
    assert panel.steps is ONBOARDING_STEPS
    assert panel.step_ids == tuple(step.id for step in ONBOARDING_STEPS)


def test_walkthrough_calls_shared_validate_step_for_every_step(monkeypatch) -> None:
    from pr_reviewer.tui.onboarding import OnboardingPanel

    calls: list[str] = []

    def recording_validate(step_id: str, payload: dict[str, object]):
        calls.append(step_id)
        return real_validate_step(step_id, payload)

    monkeypatch.setattr("pr_reviewer.tui.onboarding.validate_step", recording_validate)
    panel = OnboardingPanel(repositories=("acme/alpha", "acme/beta"))
    _advance_through_first_repository(panel)

    assert calls == [step.id for step in ONBOARDING_STEPS]


def test_walkthrough_repeats_project_setup_for_each_repository() -> None:
    from pr_reviewer.tui.onboarding import OnboardingPanel

    panel = OnboardingPanel(repositories=("acme/alpha", "acme/beta"))
    _advance_through_first_repository(panel)

    assert panel.current_step.required_fields == ("project_description",)
    assert panel.current_repository == "acme/beta"
    assert panel.completed_repositories == ("acme/alpha",)

    assert panel.try_advance({"project_description": "Second repo is the dashboard."})
    assert panel.try_advance({"repository": "acme/beta", "index_requested": True})
    assert panel.try_advance({"run_location": "hosted"})
    assert panel.is_complete
    assert panel.completed_repositories == ("acme/alpha", "acme/beta")


def test_provider_step_advises_that_platform_keys_break_less_often() -> None:
    async def exercise() -> None:
        from textual.app import App, ComposeResult
        from textual.widgets import Button

        from pr_reviewer.tui.onboarding import OnboardingPanel

        panel = OnboardingPanel(repositories=("acme/alpha",))

        class Harness(App[None]):
            def compose(self) -> ComposeResult:
                yield panel

        async with Harness().run_test() as pilot:
            advice = pilot.app.query_one("#onboarding-provider-advice")
            text = str(advice.render()).lower()
            assert "platform api key" in text
            assert "subscription" in text
            assert "revoked" in text or "throttled" in text
            assert not pilot.app.query(Button)

    asyncio.run(exercise())


def test_onboarding_transcript_declares_no_border() -> None:
    from pr_reviewer.tui.onboarding import OnboardingPanel

    assert "border" not in OnboardingPanel.DEFAULT_CSS.lower()
