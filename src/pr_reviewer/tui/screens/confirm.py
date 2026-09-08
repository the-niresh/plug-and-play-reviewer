"""A yes/no confirmation modal for actions that are not safely undoable from the TUI.

Logging out is the first caller: it revokes the runner hosted-side (control_plane/pairing
never creates a way to un-revoke one), so a single stray keypress or an accidental click on
the footer's own "Log out" hint must not be enough to trigger it on its own.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.events import Key
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("y", "confirm", "Yes", show=True),
        Binding("n", "cancel", "No", show=True),
    ]

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    ConfirmScreen > Vertical {
        width: auto;
        max-width: 60;
        padding: 1 3;
        background: $surface;
    }

    ConfirmScreen .confirm-message {
        margin-bottom: 1;
    }

    ConfirmScreen .confirm-prompt {
        color: $text-muted;
    }
    """

    def __init__(
        self,
        message: str,
        *,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
    ) -> None:
        super().__init__()
        self._message = message
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self._message, classes="confirm-message"),
            Static(
                f"y: {self._confirm_label.lower()}  n: {self._cancel_label.lower()}",
                classes="confirm-prompt",
                id="confirm-prompt",
            ),
        )

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)

    def on_key(self, event: Key) -> None:
        if event.key == "escape":
            self.dismiss(False)
            return
        if event.character == "y":
            self.dismiss(True)
            return
        if event.character == "n":
            self.dismiss(False)
