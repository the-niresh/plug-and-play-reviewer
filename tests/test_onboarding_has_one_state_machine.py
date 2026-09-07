"""One onboarding state machine shared by both frontends (Phase 35 C4).

The browser and terminal may render differently, but the ordered steps and their
validation rules live in one Python module under onboarding/.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "pr_reviewer"
WEB_ONBOARDING_PAGE = REPO_ROOT / "apps" / "web" / "src" / "app" / "onboarding" / "page.tsx"
LOCAL_ONBOARDING_API = SRC_ROOT / "runner" / "web" / "local_auth.py"
TUI_ROOT = SRC_ROOT / "tui"

STEP_IDS = (
    "provider",
    "key",
    "project_description",
    "clone_and_index",
    "github",
    "review_location",
)


def test_shared_state_machine_defines_the_canonical_step_order() -> None:
    from pr_reviewer.onboarding.state import ONBOARDING_STEPS

    assert tuple(step.id for step in ONBOARDING_STEPS) == STEP_IDS


def test_browser_onboarding_page_reads_steps_from_the_local_api() -> None:
    source = WEB_ONBOARDING_PAGE.read_text(encoding="utf-8")
    assert "/onboarding/steps" in source, "browser onboarding must fetch the shared step list"
    has_full_copy = all(f'"{step}"' in source or f"'{step}'" in source for step in STEP_IDS)
    assert not has_full_copy, "browser onboarding keeps a local copy of the canonical steps"


def test_local_onboarding_api_serves_steps_from_the_shared_state_machine() -> None:
    source = LOCAL_ONBOARDING_API.read_text(encoding="utf-8")
    assert "pr_reviewer.onboarding.state" in source
    assert "/onboarding/steps" in source


def test_terminal_frontend_has_no_full_step_list_copy() -> None:
    copied_in: list[str] = []
    for path in sorted(TUI_ROOT.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if all(f'"{step}"' in source or f"'{step}'" in source for step in STEP_IDS):
            copied_in.append(str(path.relative_to(REPO_ROOT)))
    assert copied_in == [], f"terminal frontend copied onboarding steps locally: {copied_in}"
