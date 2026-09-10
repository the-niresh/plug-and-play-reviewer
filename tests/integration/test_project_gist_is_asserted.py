"""The user's own project description is asserted context.

The point of 35.D3 is not that a file gets written to disk -- it is that this asserted
gist never blends into the inferred profile retrieval/repo_profile.py builds. A test that
only checked the file existed would still pass if the two were silently merged.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pr_reviewer.local_store.project_gist import (
    default_project_gist_path,
    load_project_gist,
    project_gist_prompt_block,
    repo_gist_slug,
    save_project_gist,
)
from pr_reviewer.retrieval.repo_profile import (
    PROFILE_BLOCK_WEIGHT,
    ProfileClaim,
    RepoProfile,
    assemble_prompt_blocks,
)
from pr_reviewer.security.instruction_sources import INSTRUCTION_BLOCK_WEIGHT

GIST_TEXT = "We ship a compliance SaaS. Never flag missing PII masking as low severity."


def _sample_profile() -> RepoProfile:
    return RepoProfile(
        repository_id=11,
        commit_sha="a" * 40,
        model="fake-model",
        prompt_version="repo-profile-v1",
        generated_at=datetime.now(tz=UTC),
        content_hash="b" * 64,
        claims=(
            ProfileClaim(
                kind="focus",
                text="This is a Python API service built with FastAPI.",
                status="candidate",
            ),
        ),
    )


def test_gist_slug_joins_owner_and_repo_with_a_double_underscore() -> None:
    assert repo_gist_slug("acme", "widgets") == "acme__widgets"
    with pytest.raises(ValueError):
        repo_gist_slug("", "widgets")
    with pytest.raises(ValueError):
        repo_gist_slug("acme", "")


def test_default_path_matches_the_documented_layout(tmp_path: Path) -> None:
    path = default_project_gist_path("acme", "widgets", config_dir=tmp_path)
    assert path == tmp_path / "repos" / "acme__widgets" / "project.md"


def test_default_path_falls_under_home_config_when_unset() -> None:
    path = default_project_gist_path("acme", "widgets")
    expected = Path.home() / ".config" / "pr-reviewer" / "repos" / "acme__widgets" / "project.md"
    assert path == expected


def test_gist_round_trips_through_save_and_load(tmp_path: Path) -> None:
    path = default_project_gist_path("acme", "widgets", config_dir=tmp_path)
    assert load_project_gist(path) is None

    save_project_gist(path, GIST_TEXT)
    assert path.is_file()
    assert load_project_gist(path) == GIST_TEXT


def test_empty_gist_is_refused(tmp_path: Path) -> None:
    path = default_project_gist_path("acme", "widgets", config_dir=tmp_path)
    with pytest.raises(ValueError):
        save_project_gist(path, "   ")
    assert not path.exists()


def test_gist_block_carries_the_asserted_weight() -> None:
    block = project_gist_prompt_block(GIST_TEXT)
    assert block.weight == "asserted"
    assert block.weight == INSTRUCTION_BLOCK_WEIGHT


def test_gist_and_inferred_profile_never_share_a_block() -> None:
    """The real assertion: the human's own words must never land in the inferred
    profile's block, and the profile's claims must never land in the gist's block --
    proving the two stay apart rather than merging into one prompt section."""
    profile = _sample_profile()

    gist_block = project_gist_prompt_block(GIST_TEXT)
    _instructions_asserted, profile_inferred = assemble_prompt_blocks((), profile)

    assert gist_block.weight == "asserted"
    assert profile_inferred.weight == "inferred"
    assert profile_inferred.weight == PROFILE_BLOCK_WEIGHT
    assert gist_block.weight != profile_inferred.weight

    assert GIST_TEXT in gist_block.texts
    assert not any(GIST_TEXT in text for text in profile_inferred.texts)

    for claim in profile.claims:
        assert not any(claim.text in text for text in gist_block.texts)
