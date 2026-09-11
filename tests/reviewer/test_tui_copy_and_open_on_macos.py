"""`c` and `o` on a Mac.

Both were reported broken from a MacBook terminal and both were real, for different
reasons. These tests pin the platform behaviour, since neither would ever be caught by
running the suite on Linux.
"""

from __future__ import annotations

import pytest


def test_a_mac_counts_as_graphical_without_display(monkeypatch: pytest.MonkeyPatch) -> None:
    """macOS sets no DISPLAY, and `o` used to read that as "no browser here".

    GUI_ENV_VARS is X11 and Wayland. Aqua sets none of them, so the guard refused before
    webbrowser was ever asked, on every Mac.
    """
    import pr_reviewer.tui.screens.connect as connect

    for name in connect.GUI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(connect.sys, "platform", "darwin")
    monkeypatch.setattr(connect.webbrowser, "get", lambda: type("B", (), {"name": "safari"})())

    assert connect.gui_browser_plausible() is True


def test_linux_without_a_display_is_still_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    """The headless-box guard must survive the macOS fix."""
    import pr_reviewer.tui.screens.connect as connect

    for name in connect.GUI_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(connect.sys, "platform", "linux")

    assert connect.gui_browser_plausible() is False


def test_mac_clipboard_prefers_pbcopy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Terminal.app ignores OSC 52, so the system tool is the one that actually copies."""
    import pr_reviewer.tui.clipboard as clipboard

    monkeypatch.setattr(clipboard.sys, "platform", "darwin")
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: f"/usr/bin/{name}")

    assert clipboard.system_clipboard_command() == ("pbcopy",)


def test_copy_reports_failure_when_no_clipboard_tool_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """It must not claim a copy it did not make. The connect screen used to say
    "Link copied." unconditionally, including when nothing reached the clipboard."""
    import pr_reviewer.tui.clipboard as clipboard

    monkeypatch.setattr(clipboard.shutil, "which", lambda name: None)

    assert clipboard.copy_to_system_clipboard("https://example.test") is False


def test_copy_sends_the_text_on_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    import pr_reviewer.tui.clipboard as clipboard

    seen: dict[str, object] = {}

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        seen["command"] = command
        seen["input"] = kwargs.get("input")
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(clipboard.sys, "platform", "darwin")
    monkeypatch.setattr(clipboard.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(clipboard.subprocess, "run", fake_run)

    assert clipboard.copy_to_system_clipboard("https://example.test") is True
    assert seen["command"] == ("pbcopy",)
    assert seen["input"] == b"https://example.test"
