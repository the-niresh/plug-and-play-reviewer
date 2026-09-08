"""First-run onboarding rendered as a transcript.

Steps and validation come from onboarding/state.py only. This module is a renderer: it
shows what the shared state machine says, collects answers, and calls validate_step. It
does not keep its own copy of the step list or validation rules.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, Static

from pr_reviewer.local_store.project_gist import default_project_gist_path, save_project_gist
from pr_reviewer.onboarding.state import ONBOARDING_STEPS, OnboardingStep, validate_step
from pr_reviewer.tui.widgets.prompt_action import PromptAction

PLATFORM_KEY_ADVICE = (
    "A platform API key breaks less often than a subscription. "
    "Subscriptions get revoked or throttled in ways a tool cannot see coming."
)

_PER_REPO_REQUIRED_FIELDS = frozenset(
    {
        ("project_description",),
        ("repository", "index_requested"),
        ("run_location",),
    }
)


class OnboardingComplete(Message):
    """Posted when every repository has finished onboarding."""


def _per_repo_step_indices() -> tuple[int, ...]:
    return tuple(
        index
        for index, step in enumerate(ONBOARDING_STEPS)
        if step.required_fields in _PER_REPO_REQUIRED_FIELDS
    )


class OnboardingPanel(Widget):
    """Walk the shared onboarding steps as a transcript. Repeat per repository."""

    DEFAULT_CSS = """
    OnboardingPanel {
        padding: 1 2;
    }

    OnboardingPanel .onboarding-heading {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    OnboardingPanel .onboarding-step-title {
        color: $accent;
        text-style: bold;
        margin-top: 1;
    }

    OnboardingPanel .onboarding-step-hint,
    OnboardingPanel .onboarding-progress,
    OnboardingPanel .onboarding-input {
        color: $text-muted;
        margin-bottom: 1;
    }

    OnboardingPanel .onboarding-advice {
        color: $text-muted;
        margin-bottom: 1;
    }

    OnboardingPanel .onboarding-errors {
        color: $error;
        margin-bottom: 1;
    }

    OnboardingPanel .onboarding-prompt {
        color: $accent;
        margin-top: 1;
    }

    OnboardingPanel .onboarding-prompt:hover {
        text-style: underline;
    }

    OnboardingPanel .onboarding-prompt:focus {
        text-style: bold underline;
    }
    """

    def __init__(
        self,
        *,
        repositories: tuple[str, ...] = (),
        config_dir: Path | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._config_dir = config_dir
        self._step_index = 0
        self._payload: dict[str, object] = {}
        self._errors: tuple[str, ...] = ()
        self._finished = False
        self._completed_repositories: list[str] = []
        self._current_repository = repositories[0] if repositories else None
        self._pending_repositories = list(repositories[1:])

    @property
    def steps(self) -> tuple[OnboardingStep, ...]:
        return ONBOARDING_STEPS

    @property
    def step_ids(self) -> tuple[str, ...]:
        return tuple(step.id for step in ONBOARDING_STEPS)

    @property
    def current_step(self) -> OnboardingStep:
        return ONBOARDING_STEPS[self._step_index]

    @property
    def current_repository(self) -> str | None:
        return self._current_repository

    @property
    def completed_repositories(self) -> tuple[str, ...]:
        return tuple(self._completed_repositories)

    @property
    def is_complete(self) -> bool:
        return self._finished

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("reviewer", classes="onboarding-heading", id="onboarding-heading"),
            Static("", id="onboarding-progress", classes="onboarding-progress"),
            Static("", id="onboarding-step-title", classes="onboarding-step-title"),
            Static("", id="onboarding-step-hint", classes="onboarding-step-hint"),
            Static(
                PLATFORM_KEY_ADVICE,
                id="onboarding-provider-advice",
                classes="onboarding-advice",
            ),
            Static("", id="onboarding-errors", classes="onboarding-errors"),
            Input(placeholder="", id="onboarding-input", classes="onboarding-input"),
            PromptAction("> continue", id="onboarding-continue", classes="onboarding-prompt"),
            id="onboarding-panel",
        )

    def on_mount(self) -> None:
        self._refresh_transcript()

    def on_prompt_action_activated(self, event: PromptAction.Activated) -> None:
        if event.prompt_action.id != "onboarding-continue":
            return
        value = self.query_one("#onboarding-input", Input).value.strip()
        fields = _fields_from_input(self.current_step, value)
        self.try_advance(fields)

    def try_advance(self, fields: Mapping[str, object]) -> bool:
        self._payload.update(fields)
        if (
            self.current_step.required_fields == ("repository", "index_requested")
            and self._current_repository is not None
            and "repository" not in fields
        ):
            self._payload["repository"] = self._current_repository
        result = validate_step(self.current_step.id, self._payload)
        if not result.valid:
            self._errors = result.errors
            self._set_errors("\n".join(result.errors))
            self._refresh_transcript()
            return False

        self._errors = ()
        self._set_errors("")
        if self.current_step.required_fields == ("project_description",):
            self._save_project_gist()
        next_index = _advance_step_index(
            self._step_index,
            completed_repositories=self._completed_repositories,
        )
        if next_index is None:
            return self._finish_repository_pass()
        self._step_index = next_index
        self._refresh_transcript()
        return True

    def _save_project_gist(self) -> None:
        if self._current_repository is None:
            return
        description = self._payload.get("project_description")
        if not isinstance(description, str) or not description.strip():
            return
        owner, repo = self._current_repository.split("/", 1)
        path = default_project_gist_path(owner, repo, config_dir=self._config_dir)
        save_project_gist(path, description)

    def _finish_repository_pass(self) -> bool:
        if self._current_repository is not None:
            self._completed_repositories.append(self._current_repository)
        if self._pending_repositories:
            self._current_repository = self._pending_repositories.pop(0)
            self._step_index = _per_repo_step_indices()[0]
            self._refresh_transcript()
            return True
        self._finished = True
        self.post_message(OnboardingComplete())
        self._refresh_transcript()
        return True

    def _refresh_transcript(self) -> None:
        if not self.is_mounted:
            return
        if self._finished:
            self.query_one("#onboarding-progress", Static).update("Onboarding complete.")
            self.query_one("#onboarding-step-title", Static).update("")
            self.query_one("#onboarding-step-hint", Static).update("")
            self.query_one("#onboarding-provider-advice", Static).display = False
            self.query_one("#onboarding-input", Input).display = False
            self.query_one("#onboarding-continue", PromptAction).display = False
            return

        step = self.current_step
        active = _active_step_indices_for(self._completed_repositories)
        position = active.index(self._step_index) + 1
        repo_line = ""
        if self._current_repository is not None:
            total = len(self._completed_repositories) + len(self._pending_repositories) + 1
            current_number = len(self._completed_repositories) + 1
            repo_line = f"Repository {current_number} of {total}: {self._current_repository}"
        self.query_one("#onboarding-progress", Static).update(
            f"Step {position} of {len(active)}"
            + (f" . {repo_line}" if repo_line else "")
        )
        self.query_one("#onboarding-step-title", Static).update(step.title)
        self.query_one("#onboarding-step-hint", Static).update(step.hint)
        advice = self.query_one("#onboarding-provider-advice", Static)
        advice.display = step.required_fields == ("provider",)
        self.query_one("#onboarding-input", Input).placeholder = _input_placeholder(step)
        self.query_one("#onboarding-input", Input).value = ""
        self.query_one("#onboarding-input", Input).password = step.required_fields == ("key",)

    def _set_errors(self, message: str) -> None:
        if not self.is_mounted:
            return
        widget = self.query_one("#onboarding-errors", Static)
        widget.update(message)
        widget.display = bool(message)


def _active_step_indices_for(completed_repositories: list[str]) -> tuple[int, ...]:
    if not completed_repositories:
        return tuple(range(len(ONBOARDING_STEPS)))
    return _per_repo_step_indices()


def _advance_step_index(
    step_index: int,
    *,
    completed_repositories: list[str],
) -> int | None:
    active = _active_step_indices_for(completed_repositories)
    position = active.index(step_index)
    if position + 1 >= len(active):
        return None
    return active[position + 1]


def _fields_from_input(step: OnboardingStep, value: str) -> dict[str, object]:
    fields = step.required_fields
    if fields == ("provider",):
        return {"provider": value}
    if fields == ("key",):
        return {"key": value}
    if fields == ("project_description",):
        return {"project_description": value}
    if fields == ("repository", "index_requested"):
        repository = value or ""
        return {"repository": repository, "index_requested": True}
    if fields == ("signed_in", "selected_repository_ids"):
        ids = [int(part) for part in value.split(",") if part.strip().isdigit()]
        return {"signed_in": True, "selected_repository_ids": ids}
    if fields == ("run_location",):
        return {"run_location": value}
    return {}


def _input_placeholder(step: OnboardingStep) -> str:
    fields = step.required_fields
    if fields == ("provider",):
        return "openai or subscription"
    if fields == ("key",):
        return "paste your api key"
    if fields == ("project_description",):
        return "describe what this repository does"
    if fields == ("repository", "index_requested"):
        return "owner/repository (leave blank to use the current repository)"
    if fields == ("signed_in", "selected_repository_ids"):
        return "repository ids, comma separated (sign in first if needed)"
    if fields == ("run_location",):
        return "local or hosted"
    return ""
