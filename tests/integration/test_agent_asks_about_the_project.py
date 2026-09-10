"""After profiling, the agent asks targeted questions derived from the profile.

The point of 35.D5 is not that questions exist -- it is that a Python API repository and a
React app get different questions traceable to their own profile claims. A fixed list that
never changes when you swap profiles proves the agent did not read anything.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pr_reviewer.retrieval.repo_profile import ProfileClaim, RepoProfile


def _profile(
    *,
    repository_id: int,
    claims: tuple[ProfileClaim, ...],
) -> RepoProfile:
    return RepoProfile(
        repository_id=repository_id,
        commit_sha="a" * 40,
        model="fake-model",
        prompt_version="repo-profile-v1",
        generated_at=datetime.now(tz=UTC),
        content_hash="b" * 64,
        claims=claims,
    )


PYTHON_API_PROFILE = _profile(
    repository_id=11,
    claims=(
        ProfileClaim(
            kind="stack",
            text="FastAPI HTTP API backed by PostgreSQL with Alembic migrations.",
            supporting_paths=("src/api/", "alembic/"),
            status="promoted",
        ),
        ProfileClaim(
            kind="focus",
            text="Route handlers live under src/api and share database session wiring.",
            supporting_paths=("src/api/routes/",),
            status="candidate",
        ),
    ),
)

REACT_APP_PROFILE = _profile(
    repository_id=22,
    claims=(
        ProfileClaim(
            kind="stack",
            text="React dashboard built with Vite, Tailwind, and shared UI components.",
            supporting_paths=("apps/web/src/components/",),
            status="promoted",
        ),
        ProfileClaim(
            kind="focus",
            text="Page layouts and hooks live under apps/web/src.",
            supporting_paths=("apps/web/src/pages/",),
            status="candidate",
        ),
    ),
)


def test_python_and_react_profiles_produce_different_questions() -> None:
    from pr_reviewer.tui.onboarding import questions_from_profile

    api_questions = questions_from_profile(PYTHON_API_PROFILE)
    react_questions = questions_from_profile(REACT_APP_PROFILE)

    api_prompts = tuple(q.prompt for q in api_questions)
    react_prompts = tuple(q.prompt for q in react_questions)

    assert api_prompts != react_prompts
    assert api_prompts
    assert react_prompts


def test_each_question_is_traceable_to_its_own_profile() -> None:
    from pr_reviewer.tui.onboarding import questions_from_profile

    for profile in (PYTHON_API_PROFILE, REACT_APP_PROFILE):
        profile_paths = {
            path.lower()
            for claim in profile.claims
            for path in claim.supporting_paths
        }
        profile_text = " ".join(claim.text.lower() for claim in profile.claims)
        for question in questions_from_profile(profile):
            haystack = question.prompt.lower()
            path_hit = question.source_path is not None and (
                question.source_path.lower() in haystack
                or question.source_path.lower() in profile_paths
            )
            kind_hit = question.source_claim_kind in {
                claim.kind for claim in profile.claims
            }
            text_hit = any(
                token in haystack
                for token in profile_text.split()
                if len(token) > 4
            )
            assert path_hit or text_hit
            assert kind_hit


def test_profile_answers_are_saved_beside_the_gist_as_asserted_context(
    tmp_path: Path,
) -> None:
    from pr_reviewer.local_store.project_gist import load_project_gist
    from pr_reviewer.security.instruction_sources import INSTRUCTION_BLOCK_WEIGHT
    from pr_reviewer.tui.onboarding import (
        OnboardingPanel,
        default_project_answers_path,
        load_project_answers,
        project_answers_prompt_block,
        questions_from_profile,
    )

    panel = OnboardingPanel(
        repositories=("acme/api-service",),
        config_dir=tmp_path,
        profiles={"acme/api-service": PYTHON_API_PROFILE},
    )
    assert panel.try_advance({"provider": "openai"})
    assert panel.try_advance({"key": "sk-test"})
    assert panel.try_advance({"project_description": "Compliance API for food safety."})
    assert panel.try_advance({"repository": "acme/api-service", "index_requested": True})

    expected_questions = questions_from_profile(PYTHON_API_PROFILE)
    assert panel.in_profile_questions
    assert panel.current_profile_question == expected_questions[0]

    for index, question in enumerate(expected_questions):
        assert panel.current_profile_question == question
        assert panel.submit_profile_answer(f"answer for question {index}")

    answers_path = default_project_answers_path(
        "acme", "api-service", config_dir=tmp_path
    )
    gist_path = tmp_path / "repos" / "acme__api-service" / "project.md"
    assert answers_path.parent == gist_path.parent
    assert answers_path.name == "project-answers.md"
    saved = load_project_answers(answers_path)
    assert saved is not None
    assert "answer for question 0" in saved
    assert expected_questions[0].prompt in saved
    assert load_project_gist(gist_path) == "Compliance API for food safety."

    block = project_answers_prompt_block(saved)
    assert block.weight == INSTRUCTION_BLOCK_WEIGHT
    assert block.weight == "asserted"

    assert panel.try_advance({"signed_in": True, "selected_repository_ids": [11]})
    assert panel.try_advance({"run_location": "local"})
    assert panel.is_complete
