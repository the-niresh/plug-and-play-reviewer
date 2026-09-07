"""The user's own description of their project, saved locally.

Saved at ``~/.config/pr-reviewer/repos/<owner>__<repo>/project.md``. This is a human's own
words about the project, typed once during setup (see the onboarding tasks in this
track). It is asserted context in the same sense
``security/instruction_sources.py`` already uses that word for ``CLAUDE.md`` and
``AGENTS.md``, and ``retrieval/repo_profile.py`` is explicit that its inferred profile is
"never merged with asserted instruction files". A project gist is a third asserted
source, not a fourth kind of weight: it reuses the same ``"asserted"`` literal, and it
must stay just as separate from the inferred profile as instruction files already are, so
the reviewer can go on weighing the human's own words higher.
"""

from __future__ import annotations

from pathlib import Path

from pr_reviewer.security.instruction_sources import INSTRUCTION_BLOCK_WEIGHT, PromptBlock


def repo_gist_slug(owner: str, repo: str) -> str:
    if not owner or not repo:
        raise ValueError("owner and repo must both be non-empty")
    return f"{owner}__{repo}"


def default_project_gist_path(
    owner: str, repo: str, *, config_dir: Path | None = None
) -> Path:
    root = config_dir or (Path.home() / ".config" / "pr-reviewer")
    return root / "repos" / repo_gist_slug(owner, repo) / "project.md"


def save_project_gist(path: Path, text: str) -> None:
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("project gist must not be empty")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cleaned + "\n", encoding="utf-8")


def load_project_gist(path: Path) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").strip()
    return text or None


def project_gist_prompt_block(text: str) -> PromptBlock:
    """Asserted, exactly like an instruction file -- never the inferred weight a repo
    profile carries. Reuses ``INSTRUCTION_BLOCK_WEIGHT`` rather than inventing a third
    weight the reviewer has no rule for, so a gist and an instruction file are weighed
    the same way and neither is ever mistaken for the inferred profile.
    """
    return PromptBlock(weight=INSTRUCTION_BLOCK_WEIGHT, texts=(text,))
