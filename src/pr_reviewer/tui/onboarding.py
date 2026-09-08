"""First-run onboarding rendered as a transcript.

Steps and validation come from onboarding/state.py only. This module is a renderer: it
shows what the shared state machine says, collects answers, and calls validate_step. It
does not keep its own copy of the step list or validation rules.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, Static

from pr_reviewer.local_store.project_gist import default_project_gist_path, save_project_gist
from pr_reviewer.onboarding.state import ONBOARDING_STEPS, OnboardingStep, validate_step
from pr_reviewer.retrieval.repo_profile import ProfileClaim, RepoProfile
from pr_reviewer.reviewer.specialists import (
    SPECIALIST_CONCERNS,
    get_enabled_specialists,
    set_enabled_specialists,
    specialist_cost_notice,
)
from pr_reviewer.security.instruction_sources import INSTRUCTION_BLOCK_WEIGHT, PromptBlock
from pr_reviewer.tui.widgets.prompt_action import PromptAction

PLATFORM_KEY_ADVICE = (
    "A platform API key breaks less often than a subscription. "
    "Subscriptions get revoked or throttled in ways a tool cannot see coming."
)

MAX_PROFILE_QUESTIONS = 3

_PER_REPO_REQUIRED_FIELDS = frozenset(
    {
        ("project_description",),
        ("repository", "index_requested"),
        ("run_location",),
    }
)

_PYTHON_API_HINTS = (
    "fastapi",
    "flask",
    "django",
    "sqlalchemy",
    "alembic",
    "postgresql",
    "api/",
    "routes/",
)

_REACT_UI_HINTS = (
    "react",
    "vite",
    "tailwind",
    "components/",
    "jsx",
    "tsx",
    "pages/",
)


@dataclass(frozen=True)
class ProfileQuestion:
    question_id: str
    prompt: str
    source_claim_kind: str
    source_path: str | None


class OnboardingComplete(Message):
    """Posted when every repository has finished onboarding."""


def default_project_answers_path(
    owner: str, repo: str, *, config_dir: Path | None = None
) -> Path:
    return default_project_gist_path(owner, repo, config_dir=config_dir).parent / (
        "project-answers.md"
    )


def format_project_answers(
    questions: Sequence[ProfileQuestion],
    answers: Mapping[str, str],
) -> str:
    sections: list[str] = []
    for question in questions:
        answer = answers.get(question.question_id, "").strip()
        sections.append(f"## {question.prompt}\n{answer}\n")
    return "\n".join(sections) + "\n"


def save_project_answers(path: Path, content: str) -> None:
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("project answers must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cleaned + "\n", encoding="utf-8")


def load_project_answers(path: Path) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def project_answers_prompt_block(text: str) -> PromptBlock:
    return PromptBlock(weight=INSTRUCTION_BLOCK_WEIGHT, texts=(text,))


def _profile_corpus(profile: RepoProfile) -> str:
    parts = [claim.text.lower() for claim in profile.claims]
    parts.extend(path.lower() for claim in profile.claims for path in claim.supporting_paths)
    return " ".join(parts)


def _detect_profile_flavor(profile: RepoProfile) -> str:
    corpus = _profile_corpus(profile)
    api_score = sum(1 for hint in _PYTHON_API_HINTS if hint in corpus)
    react_score = sum(1 for hint in _REACT_UI_HINTS if hint in corpus)
    if react_score > api_score:
        return "react_ui"
    if api_score > 0:
        return "python_api"
    return "generic"


def _question_for_claim(claim: ProfileClaim, flavor: str) -> ProfileQuestion:
    path = claim.supporting_paths[0] if claim.supporting_paths else None
    question_id = f"{claim.kind}:{path or claim.text[:32]}"
    text_lower = claim.text.lower()

    if flavor == "python_api" and path and "api" in path.lower():
        prompt = (
            f"The profile points at {path}. What breaks most often in that API layer?"
        )
    elif flavor == "python_api" and (
        "migration" in text_lower or (path and "alembic" in path.lower())
    ):
        label = path or claim.text
        prompt = (
            f"The profile mentions database migrations ({label}). "
            "What should a reviewer never flag there?"
        )
    elif flavor == "react_ui" and path and "component" in path.lower():
        prompt = (
            f"The profile names {path}. "
            "What UI patterns should a reviewer never complain about?"
        )
    elif flavor == "react_ui":
        prompt = (
            f"The profile describes {claim.text}. "
            "Which parts of the frontend matter most for review?"
        )
    elif path:
        prompt = (
            f"{path} shows up in the profile. "
            "Which directories there matter most for review?"
        )
    else:
        prompt = (
            f"The profile says: {claim.text}. "
            "What should a reviewer never complain about here?"
        )

    return ProfileQuestion(
        question_id=question_id,
        prompt=prompt,
        source_claim_kind=claim.kind,
        source_path=path,
    )


def questions_from_profile(
    profile: RepoProfile,
    *,
    max_questions: int = MAX_PROFILE_QUESTIONS,
) -> tuple[ProfileQuestion, ...]:
    flavor = _detect_profile_flavor(profile)
    questions: list[ProfileQuestion] = []
    for claim in profile.claims:
        if len(questions) >= max_questions:
            break
        questions.append(_question_for_claim(claim, flavor))
    return tuple(questions)


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
    OnboardingPanel .onboarding-input,
    OnboardingPanel .onboarding-specialist-cost {
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
        profiles: Mapping[str, RepoProfile] | None = None,
        repository_ids: Mapping[str, int] | None = None,
        repo_config_path: Path | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._config_dir = config_dir
        self._profiles = dict(profiles or {})
        self._repository_ids = dict(repository_ids or {})
        self._repo_config_path = repo_config_path
        self._step_index = 0
        self._payload: dict[str, object] = {}
        self._errors: tuple[str, ...] = ()
        self._finished = False
        self._completed_repositories: list[str] = []
        self._current_repository = repositories[0] if repositories else None
        self._pending_repositories = list(repositories[1:])
        self._in_profile_questions = False
        self._profile_questions: tuple[ProfileQuestion, ...] = ()
        self._profile_question_index = 0
        self._profile_answers: dict[str, str] = {}
        self._in_specialist_selection = False
        self._selected_specialists: set[str] = set()
        self._specialist_notice = ""

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

    @property
    def in_profile_questions(self) -> bool:
        return self._in_profile_questions

    @property
    def current_profile_question(self) -> ProfileQuestion | None:
        if not self._in_profile_questions:
            return None
        return self._profile_questions[self._profile_question_index]

    @property
    def in_specialist_selection(self) -> bool:
        return self._in_specialist_selection

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
            Static(
                "",
                id="onboarding-specialist-cost",
                classes="onboarding-specialist-cost",
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
        if self._in_profile_questions:
            self.submit_profile_answer(value)
            return
        if self._in_specialist_selection:
            if value.lower() in {"", "done", "continue"}:
                self.finish_specialist_selection()
            else:
                notice = self.toggle_specialist(value.lower())
                self._specialist_notice = notice
                self._set_specialist_cost(notice)
                self.query_one("#onboarding-input", Input).value = ""
            return
        fields = _fields_from_input(self.current_step, value)
        self.try_advance(fields)

    def submit_profile_answer(self, answer: str) -> bool:
        if not self._in_profile_questions:
            return False
        cleaned = answer.strip()
        if not cleaned:
            self._set_errors("answer is required")
            return False
        question = self._profile_questions[self._profile_question_index]
        self._profile_answers[question.question_id] = cleaned
        self._profile_question_index += 1
        self._set_errors("")
        if self._profile_question_index < len(self._profile_questions):
            self._refresh_transcript()
            return True
        self._save_profile_answers()
        self._in_profile_questions = False
        self._profile_question_index = 0
        return self._advance_to_next_step()

    def toggle_specialist(self, concern: str) -> str:
        if concern not in SPECIALIST_CONCERNS:
            return f"Unknown specialist: {concern}"
        if concern in self._selected_specialists:
            self._selected_specialists.remove(concern)
        else:
            self._selected_specialists.add(concern)
        return specialist_cost_notice(len(self._selected_specialists))

    def finish_specialist_selection(self) -> bool:
        if not self._in_specialist_selection:
            return False
        repo_id = self._github_id_for_current_repo()
        if repo_id is not None and self._repo_config_path is not None:
            set_enabled_specialists(
                self._repo_config_path,
                repo_id,
                tuple(sorted(self._selected_specialists)),
            )
        self._in_specialist_selection = False
        self._selected_specialists.clear()
        self._specialist_notice = ""
        return self._finish_repository_pass()

    def try_advance(self, fields: Mapping[str, object]) -> bool:
        if self._in_profile_questions or self._in_specialist_selection:
            return False
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
        if (
            self.current_step.required_fields == ("repository", "index_requested")
            and self._start_profile_questions()
        ):
            return True
        if (
            self.current_step.required_fields == ("run_location",)
            and self._start_specialist_selection()
        ):
            return True
        return self._advance_to_next_step()

    def _start_profile_questions(self) -> bool:
        if self._current_repository is None:
            return False
        profile = self._profiles.get(self._current_repository)
        if profile is None:
            return False
        questions = questions_from_profile(profile)
        if not questions:
            return False
        self._profile_questions = questions
        self._profile_question_index = 0
        self._profile_answers = {}
        self._in_profile_questions = True
        self._refresh_transcript()
        return True

    def _start_specialist_selection(self) -> bool:
        if not self._should_offer_specialist_selection():
            return False
        repo_id = self._github_id_for_current_repo()
        assert repo_id is not None and self._repo_config_path is not None
        self._selected_specialists = set(get_enabled_specialists(self._repo_config_path, repo_id))
        self._in_specialist_selection = True
        self._specialist_notice = specialist_cost_notice(len(self._selected_specialists))
        self._refresh_transcript()
        return True

    def _should_offer_specialist_selection(self) -> bool:
        if self._repo_config_path is None:
            return False
        return self._github_id_for_current_repo() is not None

    def _github_id_for_current_repo(self) -> int | None:
        if self._current_repository is None:
            return None
        return self._repository_ids.get(self._current_repository)

    def _advance_to_next_step(self) -> bool:
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

    def _save_profile_answers(self) -> None:
        if self._current_repository is None:
            return
        owner, repo = self._current_repository.split("/", 1)
        path = default_project_answers_path(owner, repo, config_dir=self._config_dir)
        content = format_project_answers(self._profile_questions, self._profile_answers)
        save_project_answers(path, content)

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
        specialist_cost = self.query_one("#onboarding-specialist-cost", Static)
        if self._finished:
            self.query_one("#onboarding-progress", Static).update("Onboarding complete.")
            self.query_one("#onboarding-step-title", Static).update("")
            self.query_one("#onboarding-step-hint", Static).update("")
            self.query_one("#onboarding-provider-advice", Static).display = False
            specialist_cost.display = False
            self.query_one("#onboarding-input", Input).display = False
            self.query_one("#onboarding-continue", PromptAction).display = False
            return

        if self._in_profile_questions:
            question = self.current_profile_question
            assert question is not None
            self.query_one("#onboarding-progress", Static).update(
                f"Profile question {self._profile_question_index + 1} of "
                f"{len(self._profile_questions)}"
            )
            self.query_one("#onboarding-step-title", Static).update("About this repository")
            self.query_one("#onboarding-step-hint", Static).update(question.prompt)
            self.query_one("#onboarding-provider-advice", Static).display = False
            specialist_cost.display = False
            self.query_one("#onboarding-input", Input).display = True
            self.query_one("#onboarding-continue", PromptAction).display = True
            self.query_one("#onboarding-input", Input).placeholder = "your answer"
            self.query_one("#onboarding-input", Input).value = ""
            self.query_one("#onboarding-input", Input).password = False
            return

        if self._in_specialist_selection:
            enabled = ", ".join(sorted(self._selected_specialists)) or "none"
            options = ", ".join(SPECIALIST_CONCERNS)
            self.query_one("#onboarding-progress", Static).update("Optional specialist reviewers")
            self.query_one("#onboarding-step-title", Static).update("Specialists")
            self.query_one("#onboarding-step-hint", Static).update(
                f"Type a concern to toggle it on or off: {options}. "
                f"Enabled: {enabled}. Leave blank and continue when done."
            )
            self.query_one("#onboarding-provider-advice", Static).display = False
            specialist_cost.update(self._specialist_notice)
            specialist_cost.display = bool(self._specialist_notice)
            self.query_one("#onboarding-input", Input).display = True
            self.query_one("#onboarding-continue", PromptAction).display = True
            self.query_one("#onboarding-input", Input).placeholder = "security, correctness, ..."
            self.query_one("#onboarding-input", Input).value = ""
            self.query_one("#onboarding-input", Input).password = False
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
        specialist_cost.display = False
        self.query_one("#onboarding-input", Input).placeholder = _input_placeholder(step)
        self.query_one("#onboarding-input", Input).value = ""
        self.query_one("#onboarding-input", Input).password = step.required_fields == ("key",)

    def _set_errors(self, message: str) -> None:
        if not self.is_mounted:
            return
        widget = self.query_one("#onboarding-errors", Static)
        widget.update(message)
        widget.display = bool(message)

    def _set_specialist_cost(self, message: str) -> None:
        if not self.is_mounted:
            return
        widget = self.query_one("#onboarding-specialist-cost", Static)
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
