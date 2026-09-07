"""Select a model by role before forwarding to the underlying provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pr_reviewer.models.provider import ModelProvider, ModelRequest, ModelResponse

ModelRole = Literal["triage", "generate", "judge", "explore"]

_ROLE_FROM_SCHEMA_NAME: dict[str, ModelRole] = {
    "ReviewFindingsDraft": "generate",
    "FindingReflectionScores": "judge",
}


@dataclass(frozen=True)
class RoleModels:
    # Deliberate default split: cheap generation, stronger judging.
    triage: str = "gpt-4o-mini"
    generate: str = "gpt-4o-mini"
    judge: str = "gpt-4.1"
    explore: str = "gpt-4o-mini"

    def for_role(self, role: ModelRole) -> str:
        if role == "triage":
            return self.triage
        if role == "generate":
            return self.generate
        if role == "judge":
            return self.judge
        return self.explore


def role_for_request(request: ModelRequest) -> ModelRole:
    role = _ROLE_FROM_SCHEMA_NAME.get(request.schema_name)
    if role is not None:
        return role
    prompt_name = request.prompt_name.strip().lower()
    if prompt_name.startswith("triage"):
        return "triage"
    if prompt_name.startswith("explore"):
        return "explore"
    return "generate"


class RoleRoutedModelProvider:
    def __init__(self, provider: ModelProvider, role_models: RoleModels | None = None) -> None:
        self._provider = provider
        self._role_models = role_models if role_models is not None else RoleModels()

    def complete_json(self, request: ModelRequest) -> ModelResponse:
        routed_model = self._role_models.for_role(role_for_request(request))
        routed_request = request.model_copy(update={"model": routed_model})
        return self._provider.complete_json(routed_request)
