"""The whole TUI is a transcript, not a form.

D1 applies to every screen under tui/, not a hand-picked pair. These tests discover all
screen and widget modules automatically so a new screen added next month cannot reintroduce
Button widgets or bordered containers without failing the gate.
"""

from __future__ import annotations

import ast
import asyncio
import re
from pathlib import Path

import pytest
from repo_paths import REPO_ROOT
from textual.app import App, ComposeResult

REPO_ROOT = REPO_ROOT
TUI_ROOT = REPO_ROOT / "src" / "pr_reviewer" / "tui"

_BORDER_LINE_RE = re.compile(r"border[^:]*:\s*(?!none\b)(?!.*transparent\b)", re.IGNORECASE)


def _tui_python_modules() -> tuple[Path, ...]:
    return tuple(sorted(path for path in TUI_ROOT.rglob("*.py") if path.is_file()))


def _css_strings_in_module(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    css_chunks: list[str] = []

    def collect_from_assign(node: ast.Assign) -> None:
        for target in node.targets:
            if (
                isinstance(target, ast.Name)
                and target.id in {"DEFAULT_CSS", "CSS", "REVIEWER_CSS"}
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                css_chunks.append(node.value.value)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            collect_from_assign(node)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.Assign):
                    collect_from_assign(item)
    return css_chunks


def _button_offenders() -> list[str]:
    offenders: list[str] = []
    for path in _tui_python_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(REPO_ROOT)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "textual.widgets"
                and any(alias.name == "Button" for alias in node.names)
            ):
                offenders.append(f"{rel}: imports Button")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "Button"
            ):
                offenders.append(f"{rel}: constructs Button")
    return offenders


def _border_offenders() -> list[str]:
    offenders: list[str] = []
    for path in _tui_python_modules():
        rel = path.relative_to(REPO_ROOT)
        for css in _css_strings_in_module(path):
            for line in css.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("/*"):
                    continue
                if "border" not in stripped.lower():
                    continue
                if _BORDER_LINE_RE.search(stripped):
                    offenders.append(f"{rel}: {stripped}")
    return offenders


def test_no_tui_module_imports_or_constructs_button() -> None:
    offenders = _button_offenders()
    assert offenders == [], "Button widgets found:\n" + "\n".join(offenders)


def test_no_tui_css_declares_a_visible_border() -> None:
    offenders = _border_offenders()
    assert offenders == [], "Visible borders found:\n" + "\n".join(offenders)


class _NeverRespondingInstallationClient:
    def fetch(self, hosted_origin: str, credential: str) -> object:
        import threading

        threading.Event().wait()
        raise AssertionError("unreachable")


def test_first_paint_does_not_wait_on_installation_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pr_reviewer.runner.secrets import FileSecretStore
    from pr_reviewer.tui.app import ReviewerApp

    secrets = FileSecretStore(tmp_path)
    secrets.set("runner_credential", "test-runner-credential")
    secrets.set("model_key", "sk-test-model-key")

    def skip_background_fetch(self: ReviewerApp) -> None:
        return None

    monkeypatch.setattr(ReviewerApp, "_refresh_installation_snapshot_async", skip_background_fetch)

    async def exercise() -> None:
        app = ReviewerApp(
            secrets=secrets,
            config_dir=tmp_path,
            installation_client=_NeverRespondingInstallationClient(),
        )
        async with app.run_test() as pilot:
            status = pilot.app.query_one("#startup-status")
            text = str(status.render()).lower()
            assert "checking sign-in" in text

    asyncio.run(exercise())


class FakePairingClient:
    def create_code(self, device_name: str, challenge: str) -> str:
        return "PAIR-TRANSCRIPT-1"

    def status(self, code: str, challenge: str) -> str:
        return "pending"

    def exchange(self, code: str, proof: str) -> str:
        return "runner-credential"


def test_sign_in_still_works_without_a_button() -> None:
    from pr_reviewer.tui.screens.connect import ConnectConfig, ConnectPanel

    class Harness(App[None]):
        def compose(self) -> ComposeResult:
            yield ConnectPanel(
                config=ConnectConfig(
                    hosted_origin="https://reviewer.niresh.tech",
                    device_name="test-laptop",
                ),
                pairing_client=FakePairingClient(),
                pairing_deadline_seconds=0.2,
                pairing_poll_interval=0.01,
            )

    async def exercise() -> None:
        async with Harness().run_test() as pilot:
            from textual.widgets import Button

            assert not pilot.app.query(Button)
            await pilot.click("#connect-sign-in")
            for _ in range(200):
                if pilot.app.query("#sign-in-url"):
                    break
                await pilot.pause()
            assert pilot.app.query("#sign-in-url")
            url_text = str(pilot.app.query_one("#sign-in-url").render())
            assert "PAIR-TRANSCRIPT-1" in url_text

    asyncio.run(exercise())
