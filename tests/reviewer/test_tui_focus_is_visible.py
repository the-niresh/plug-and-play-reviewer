"""Every focusable transcript row must look focused.

PromptAction sets can_focus = True and had no :focus style. Tab into the repositories
list, press the arrow keys, and focus moved with nothing on screen changing, so Enter was
a guess about which repository you were on. A focus ring is not decoration on a list you
drive with the keyboard; it is the only thing that says where you are.
"""

from __future__ import annotations

from pr_reviewer.tui.widgets.prompt_action import PromptAction


def test_prompt_action_styles_its_own_focus_state() -> None:
    css = PromptAction.DEFAULT_CSS
    assert "PromptAction:focus" in css
    # More than one channel, so it still reads on a terminal that drops colour.
    assert "background:" in css
    assert "text-style: bold" in css


def test_the_style_lives_on_the_widget_not_on_one_screen() -> None:
    """A per-screen rule only fixes the screens someone remembered."""
    from pathlib import Path

    from pr_reviewer.tui.widgets import prompt_action

    source = Path(prompt_action.__file__).read_text(encoding="utf-8")
    assert "DEFAULT_CSS" in source
