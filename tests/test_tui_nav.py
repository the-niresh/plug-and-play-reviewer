"""Four-section TUI navigation with a persistent current-section indicator."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.containers import Container

from pr_reviewer.tui.app import ReviewerApp
from pr_reviewer.tui.installation_snapshot import InstallationSnapshot, RepositoryPermission
from pr_reviewer.tui.nav import SECTIONS, SectionNav
from pr_reviewer.tui.review_dashboard import ReviewDashboardPanel
from pr_reviewer.tui.screens.profile import ProfilePanel
from pr_reviewer.tui.screens.prompts import AgentPromptsPanel
from pr_reviewer.tui.screens.repositories import RepositoriesPanel

SAMPLE_INSTALLATION = InstallationSnapshot(
    github_login="the-niresh",
    github_user_id=42,
    installation_id=7010,
    repositories=(RepositoryPermission(11, "in-scope"),),
)

SECTION_PANEL_TYPES: dict[str, type] = {
    "repositories": RepositoriesPanel,
    "agent-prompts": AgentPromptsPanel,
    "profile": ProfilePanel,
    "reviews": ReviewDashboardPanel,
}


def connected_secrets(tmp_path: Path):
    from pr_reviewer.runner.secrets import FileSecretStore

    secrets = FileSecretStore(tmp_path)
    secrets.set("runner_credential", "test-runner-credential")
    secrets.set("model_key", "sk-test-model-key")
    return secrets


def make_connected_app(tmp_path: Path) -> ReviewerApp:
    return ReviewerApp(
        secrets=connected_secrets(tmp_path),
        installation_snapshot=SAMPLE_INSTALLATION,
        config_dir=tmp_path,
    )


@pytest.fixture(autouse=True)
def skip_background_installation_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ReviewerApp, "_refresh_installation_snapshot_async", lambda self: None)


@pytest.mark.parametrize("section_id", SECTIONS)
def test_section_ids_are_stable(section_id: str) -> None:
    assert section_id in {"repositories", "agent-prompts", "profile", "reviews"}


def test_section_nav_lists_four_sections() -> None:
    nav = SectionNav()
    assert nav.section_ids == list(SECTIONS)
    assert len(nav.section_ids) == 4


def test_reviewer_app_starts_on_repositories(tmp_path: Path) -> None:
    async def exercise() -> None:
        app = make_connected_app(tmp_path)
        async with app.run_test() as pilot:
            nav = app.query_one(SectionNav)
            assert nav.current_section == "repositories"
            assert pilot.app.query_one("#repositories-heading") is not None

    asyncio.run(exercise())


def test_current_section_is_visually_distinct_without_focus(tmp_path: Path) -> None:
    async def exercise() -> None:
        app = make_connected_app(tmp_path)
        async with app.run_test() as pilot:
            nav = app.query_one(SectionNav)
            current = nav.query_one("#nav-repositories")
            assert "nav-item--current" in current.classes
            profile = nav.query_one("#nav-profile")
            assert "nav-item--current" not in profile.classes

            await pilot.press("tab")
            assert "nav-item--current" in current.classes
            assert "nav-item--current" not in profile.classes

    asyncio.run(exercise())


def test_selecting_a_section_updates_content_and_indicator(tmp_path: Path) -> None:
    async def exercise() -> None:
        app = make_connected_app(tmp_path)
        async with app.run_test() as pilot:
            await pilot.click("#nav-reviews")
            nav = app.query_one(SectionNav)
            assert nav.current_section == "reviews"
            assert pilot.app.query_one(ReviewDashboardPanel) is not None
            reviews = nav.query_one("#nav-reviews")
            repositories = nav.query_one("#nav-repositories")
            assert "nav-item--current" in reviews.classes
            assert "nav-item--current" not in repositories.classes

    asyncio.run(exercise())


@pytest.mark.parametrize("section_id", SECTIONS)
def test_reselecting_section_keeps_exactly_one_panel(
    tmp_path: Path, section_id: str
) -> None:
    async def exercise() -> None:
        app = make_connected_app(tmp_path)
        panel_type = SECTION_PANEL_TYPES[section_id]
        other_section = next(sid for sid in SECTIONS if sid != section_id)

        async with app.run_test() as pilot:
            await pilot.click(f"#nav-{section_id}")
            await pilot.pause()
            await pilot.click(f"#nav-{section_id}")
            await pilot.pause()

            pane = app.query_one("#section-content", Container)
            panels = list(app.query(panel_type))
            assert len(panels) == 1
            assert len(pane.children) == 1

            await pilot.click(f"#nav-{other_section}")
            await pilot.pause()
            await pilot.click(f"#nav-{section_id}")
            await pilot.pause()

            panels = list(app.query(panel_type))
            assert len(panels) == 1
            assert len(pane.children) == 1

    asyncio.run(exercise())


def test_section_mount_failure_shows_one_line_not_traceback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from pr_reviewer.tui.review_dashboard import ReviewDashboardPanel as Dashboard

    def exploding_init(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        raise RuntimeError("simulated mount failure")

    monkeypatch.setattr(Dashboard, "__init__", exploding_init)

    async def exercise() -> None:
        app = make_connected_app(tmp_path)
        async with app.run_test() as pilot:
            await pilot.click("#nav-reviews")
            await pilot.pause()
            error_line = app.query_one("#section-error")
            rendered = str(error_line.render()).lower()
            assert "something went wrong" in rendered
            assert "log" in rendered

    asyncio.run(exercise())

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "Traceback" not in combined
    assert "locals" not in combined.lower()
    assert "simulated mount failure" not in combined

    log_path = tmp_path / "tui-errors.log"
    assert log_path.is_file()
    log_text = log_path.read_text(encoding="utf-8")
    assert "simulated mount failure" in log_text
