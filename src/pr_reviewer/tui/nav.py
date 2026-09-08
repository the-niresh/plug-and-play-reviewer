"""Sidebar navigation between the four reviewer TUI sections."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget

from pr_reviewer.tui.widgets.prompt_action import PromptAction

SECTIONS: tuple[str, ...] = ("repositories", "agent-prompts", "profile", "reviews")


class SectionSelected(Message):
    """Posted when the user picks a sidebar section."""

    def __init__(self, section_id: str) -> None:
        self.section_id = section_id
        super().__init__()


class SectionNav(Widget):
    """Persistent sidebar with a always-visible current section."""

    DEFAULT_CSS = """
    SectionNav {
        width: 22;
        height: 100%;
        padding: 1 0;
    }

    SectionNav:focus-within {
        background: $surface;
    }

    SectionNav .nav-item {
        width: 100%;
        color: $text;
        padding: 0 1;
        margin: 0;
    }

    SectionNav .nav-item--current {
        background: $panel;
        color: $primary;
        text-style: bold;
    }

    SectionNav .nav-item:focus {
        background: $accent 25%;
        text-style: bold;
    }

    SectionNav .nav-item--current:focus {
        background: $panel;
        color: $primary;
        text-style: bold;
    }
    """

    current_section: reactive[str] = reactive("repositories")

    @property
    def section_ids(self) -> list[str]:
        return list(SECTIONS)

    def compose(self) -> ComposeResult:
        for section_id in SECTIONS:
            yield PromptAction(
                f"> {section_id}",
                id=f"nav-{section_id}",
                classes="nav-item",
            )

    def on_mount(self) -> None:
        self._sync_current_classes()

    def watch_current_section(self, _section_id: str) -> None:
        self._sync_current_classes()

    def select_section(self, section_id: str) -> None:
        if section_id not in SECTIONS:
            return
        self.current_section = section_id
        self.post_message(SectionSelected(section_id))

    def on_prompt_action_activated(self, event: PromptAction.Activated) -> None:
        prompt_id = event.prompt_action.id
        if prompt_id is None:
            return
        section_id = prompt_id.removeprefix("nav-")
        if section_id not in SECTIONS:
            return
        self.select_section(section_id)

    def _sync_current_classes(self) -> None:
        for section_id in SECTIONS:
            item = self.query_one(f"#nav-{section_id}", PromptAction)
            item.set_class(section_id == self.current_section, "nav-item--current")
