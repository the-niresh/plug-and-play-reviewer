"""Shared onboarding state machine for terminal and browser frontends."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

OnboardingStepId = Literal[
    "provider",
    "key",
    "project_description",
    "clone_and_index",
    "github",
    "review_location",
]


@dataclass(frozen=True)
class OnboardingStep:
    id: OnboardingStepId
    title: str
    hint: str
    required_fields: tuple[str, ...]


@dataclass(frozen=True)
class StepValidation:
    valid: bool
    errors: tuple[str, ...]


ONBOARDING_STEPS: tuple[OnboardingStep, ...] = (
    OnboardingStep(
        id="provider",
        title="Provider",
        hint="Choose where model calls run.",
        required_fields=("provider",),
    ),
    OnboardingStep(
        id="key",
        title="Key",
        hint="Store a model key on this machine.",
        required_fields=("key",),
    ),
    OnboardingStep(
        id="project_description",
        title="Project description",
        hint="Describe what this repository does.",
        required_fields=("project_description",),
    ),
    OnboardingStep(
        id="clone_and_index",
        title="Clone and index",
        hint="Fetch repository content and build a local index.",
        required_fields=("repository", "index_requested"),
    ),
    OnboardingStep(
        id="github",
        title="GitHub",
        hint="Sign in and choose repositories.",
        required_fields=("signed_in", "selected_repository_ids"),
    ),
    OnboardingStep(
        id="review_location",
        title="Where reviews run",
        hint="Choose local or hosted review execution.",
        required_fields=("run_location",),
    ),
)

_STEP_IDS = {step.id for step in ONBOARDING_STEPS}


def steps_payload() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "id": step.id,
            "title": step.title,
            "hint": step.hint,
            "required_fields": list(step.required_fields),
        }
        for step in ONBOARDING_STEPS
    )


def validate_step(step_id: str, payload: Mapping[str, object]) -> StepValidation:
    if step_id not in _STEP_IDS:
        return StepValidation(valid=False, errors=(f"unknown step: {step_id}",))
    if step_id == "provider":
        return _require_non_empty_string(payload, "provider")
    if step_id == "key":
        return _require_non_empty_string(payload, "key")
    if step_id == "project_description":
        return _require_non_empty_string(payload, "project_description")
    if step_id == "clone_and_index":
        return _validate_clone_and_index(payload)
    if step_id == "github":
        return _validate_github(payload)
    if step_id == "review_location":
        return _validate_review_location(payload)
    return StepValidation(valid=False, errors=(f"unknown step: {step_id}",))


def _require_non_empty_string(payload: Mapping[str, object], field: str) -> StepValidation:
    raw = payload.get(field)
    if isinstance(raw, str) and raw.strip():
        return StepValidation(valid=True, errors=())
    return StepValidation(valid=False, errors=(f"{field} is required",))


def _validate_clone_and_index(payload: Mapping[str, object]) -> StepValidation:
    errors: list[str] = []
    repository = payload.get("repository")
    if not isinstance(repository, str) or "/" not in repository or not repository.strip():
        errors.append("repository must be owner/repository")
    if payload.get("index_requested") is not True:
        errors.append("index_requested must be true")
    return StepValidation(valid=not errors, errors=tuple(errors))


def _validate_github(payload: Mapping[str, object]) -> StepValidation:
    errors: list[str] = []
    if payload.get("signed_in") is not True:
        errors.append("signed_in must be true")
    selected = payload.get("selected_repository_ids")
    if not isinstance(selected, list) or not selected:
        errors.append("selected_repository_ids must be a non-empty list")
    return StepValidation(valid=not errors, errors=tuple(errors))


def _validate_review_location(payload: Mapping[str, object]) -> StepValidation:
    location = payload.get("run_location")
    if location in {"local", "hosted"}:
        return StepValidation(valid=True, errors=())
    return StepValidation(valid=False, errors=("run_location must be local or hosted",))
