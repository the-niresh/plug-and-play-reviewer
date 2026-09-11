"""A single transcript line the user can activate, in place of a Button.

A Button carries a border and padding by default, which is exactly the "form" look this
track exists to remove (see tests/test_tui_is_a_transcript.py). PromptAction reads like a
line someone typed at a prompt (`> sign in`) and responds to the same click and keyboard
activation a Button did, so replacing one with the other changes how it looks, not what
it does.
"""

from __future__ import annotations

from textual.message import Message
from textual.widgets import Static


class PromptAction(Static):
    """A clickable, focusable transcript line. No border, no padding, no button chrome."""

    can_focus = True

    # can_focus without a focus style is a keyboard trap with the lights off. Tab into a
    # list of these and the arrow keys move focus with nothing on screen changing, so
    # pressing Enter is a guess about which row you are on. Styled here rather than per
    # screen so every list of these rows shows its current item, not just the ones
    # somebody remembered.
    DEFAULT_CSS = """
    PromptAction:focus {
        background: $primary;
        color: $background;
        text-style: bold;
    }
    """

    class Activated(Message):
        def __init__(self, prompt_action: PromptAction) -> None:
            self.prompt_action = prompt_action
            super().__init__()

    def on_click(self) -> None:
        self.post_message(self.Activated(self))

    def press(self) -> None:
        """Mirrors Button.press() -- App.action_activate_focused (tui/app.py) calls this on
        whatever widget holds focus, so plain Enter keeps working with no border to press."""
        self.post_message(self.Activated(self))
