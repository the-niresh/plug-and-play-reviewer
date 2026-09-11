"""Agent-prompts screen listing every specialist and its current prompt."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Label, Select, Static, TextArea

from pr_reviewer.local_store.repo_config import RepoConfigStore
from pr_reviewer.reviewer.specialists import (
    SPECIALIST_CONCERNS,
    get_enabled_specialists,
    set_enabled_specialists,
    specialist_cost_notice,
)
from pr_reviewer.tui.agent_prompt_catalogue import list_builtin_agent_prompts
from pr_reviewer.tui.installation_snapshot import InstallationSnapshot
from pr_reviewer.tui.repository_prompt import quote_repository_prompt
from pr_reviewer.tui.widgets.prompt_action import PromptAction


class AgentPromptsPanel(Widget):
    DEFAULT_CSS = """
    AgentPromptsPanel {
        padding: 1 2;
    }

    AgentPromptsPanel .prompts-heading {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    AgentPromptsPanel .prompt-agent-heading {
        text-style: bold;
        margin-top: 1;
    }

    AgentPromptsPanel .prompt-content {
        color: $text-muted;
        margin-bottom: 1;
    }

    AgentPromptsPanel .custom-prompt-heading {
        text-style: bold;
        color: $accent;
        margin-top: 2;
        margin-bottom: 1;
    }

    AgentPromptsPanel .custom-prompt-action {
        color: $accent;
        margin-top: 1;
    }

    AgentPromptsPanel .specialist-heading {
        text-style: bold;
        color: $accent;
        margin-top: 2;
    }

    AgentPromptsPanel .specialist-hint,
    AgentPromptsPanel .specialist-cost {
        color: $text-muted;
    }

    AgentPromptsPanel .specialist-toggle {
        margin-top: 0;
    }
    """

    def __init__(
        self,
        snapshot: InstallationSnapshot | None = None,
        *,
        repo_config: RepoConfigStore | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._snapshot = snapshot
        self._repo_config = repo_config
        repo_options = (
            [(repo.name, str(repo.github_repository_id)) for repo in snapshot.repositories]
            if snapshot is not None
            else []
        )
        self._repo_options = repo_options
        self._default_repo = repo_options[0][1] if repo_options else None

    def compose(self) -> ComposeResult:
        rows: list[Widget] = [
            Label("Agent prompts", classes="prompts-heading", id="agent-prompts-heading")
        ]
        for entry in list_builtin_agent_prompts():
            rows.append(
                Static(
                    f"{entry.label} ({entry.agent_id} v{entry.version})",
                    classes="prompt-agent-heading",
                    id=f"prompt-heading-{entry.agent_id}",
                )
            )
            rows.append(
                Static(
                    entry.content,
                    classes="prompt-content",
                    id=f"prompt-content-{entry.agent_id}",
                )
            )
        if self._repo_options:
            rows.extend(
                [
                    Label(
                        "Custom repository prompt",
                        classes="custom-prompt-heading",
                        id="custom-prompt-heading",
                    ),
                    Select(
                        self._repo_options,
                        id="custom-prompt-repo",
                        value=self._default_repo,
                    ),
                    TextArea(id="custom-prompt-input"),
                    PromptAction(
                        "> save new version",
                        id="custom-prompt-save",
                        classes="custom-prompt-action",
                    ),
                    Static("", id="custom-prompt-status"),
                    Static("", id="custom-prompt-versions"),
                ]
            )
            rows.extend(
                [
                    Label(
                        "Specialist reviewers",
                        classes="specialist-heading",
                        id="specialist-heading",
                    ),
                    Static(
                        "Extra passes over the same diff, one per concern. Off by default "
                        "because each one is another model call. Applies to the repository "
                        "selected above.",
                        classes="specialist-hint",
                        id="specialist-hint",
                    ),
                ]
            )
            rows.extend(
                PromptAction(
                    f"> (off) {concern}",
                    id=f"specialist-{concern}",
                    classes="specialist-toggle",
                )
                for concern in SPECIALIST_CONCERNS
            )
            rows.append(Static("", classes="specialist-cost", id="specialist-cost"))
        yield Vertical(*rows, id="agent-prompts-panel")

    def on_mount(self) -> None:
        self._refresh_custom_prompt_display()
        self._refresh_specialist_display()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "custom-prompt-repo" and event.value is not Select.NULL:
            self._refresh_custom_prompt_display()
            self._refresh_specialist_display()

    def on_prompt_action_activated(self, event: PromptAction.Activated) -> None:
        action_id = event.prompt_action.id or ""
        if action_id.startswith("specialist-"):
            self._toggle_specialist(action_id.removeprefix("specialist-"))
            return
        if action_id != "custom-prompt-save" or self._repo_config is None:
            return
        repo_id = self._selected_repo_id()
        if repo_id is None:
            return
        content = self.query_one("#custom-prompt-input", TextArea).text.strip()
        if not content:
            self._set_custom_status("Enter prompt text first.")
            return
        try:
            saved = self._repo_config.add_repository_prompt(repo_id, content)
        except ValueError as exc:
            self._set_custom_status(str(exc))
            return
        quote_repository_prompt(saved.content)
        self.query_one("#custom-prompt-input", TextArea).clear()
        self._set_custom_status(f"Saved v{saved.version} for this repository.")
        self._refresh_custom_prompt_display()

    def _selected_repo_id(self) -> int | None:
        if not self._repo_options:
            return None
        value = self.query_one("#custom-prompt-repo", Select).value
        if value is Select.NULL:
            return None
        return int(str(value))

    def _refresh_custom_prompt_display(self) -> None:
        if self._repo_config is None or not self._repo_options:
            return
        repo_id = self._selected_repo_id()
        if repo_id is None:
            return
        versions = self._repo_config.list_repository_prompt_versions(repo_id)
        if not versions:
            self.query_one("#custom-prompt-versions", Static).update(
                "No custom prompt saved for this repository yet."
            )
            return
        lines = [
            f"v{item.version}{' (locked)' if item.locked else ''}: {item.content[:80]}"
            for item in versions
        ]
        self.query_one("#custom-prompt-versions", Static).update("\n".join(lines))

    def _toggle_specialist(self, concern: str) -> None:
        """Write the change straight through, no separate save step.

        The onboarding panel collected every toggle and wrote once at the end, which is
        why this setting was unreachable: that panel is mounted by nothing. Here each
        toggle is its own edit, so there is no half-applied state to lose.
        """
        if concern not in SPECIALIST_CONCERNS or self._repo_config is None:
            return
        repo_id = self._selected_repo_id()
        if repo_id is None:
            return
        enabled = set(get_enabled_specialists(self._repo_config.path, repo_id))
        if concern in enabled:
            enabled.discard(concern)
        else:
            enabled.add(concern)
        set_enabled_specialists(self._repo_config.path, repo_id, tuple(sorted(enabled)))
        self._refresh_specialist_display()

    def _refresh_specialist_display(self) -> None:
        if self._repo_config is None or not self._repo_options:
            return
        repo_id = self._selected_repo_id()
        if repo_id is None:
            return
        enabled = set(get_enabled_specialists(self._repo_config.path, repo_id))
        for concern in SPECIALIST_CONCERNS:
            # Parentheses, not the [x] a checkbox wants: Textual reads square brackets as
            # markup, so "[x] security" renders as "security" styled 'x' and the toggle
            # looks like it did nothing.
            mark = "(on) " if concern in enabled else "(off)"
            self.query_one(f"#specialist-{concern}", PromptAction).update(
                f"> {mark} {concern}"
            )
        notice = specialist_cost_notice(len(enabled))
        self.query_one("#specialist-cost", Static).update(
            notice or "No specialists enabled. Reviews stay at one model call."
        )

    def _set_custom_status(self, message: str) -> None:
        self.query_one("#custom-prompt-status", Static).update(message)
