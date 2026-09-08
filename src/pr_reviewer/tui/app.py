"""Bare `reviewer` opens this Textual app instead of dumping usage."""

from __future__ import annotations

import sys
import time
import traceback
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Footer, Static

from pr_reviewer.local_store.repo_config import RepoConfigStore, default_repo_config_path
from pr_reviewer.local_store.review_log import ReviewLogStore, default_review_log_path
from pr_reviewer.runner.client import RunnerClient
from pr_reviewer.runner.logout import log_out
from pr_reviewer.runner.secrets import SecretStore, default_config_dir, get_secret_store
from pr_reviewer.tui.auth_state import RUNNER_CREDENTIAL_SECRET, has_model_key, is_github_connected
from pr_reviewer.tui.auto_review import (
    TUI_CLOSED_AUTO_REVIEW_MESSAGE,
    AutoReviewCoordinator,
    AutoReviewEventSource,
    AutoReviewOutcome,
    PullRequestSyncEvent,
)
from pr_reviewer.tui.github_reads import InstallationRepositoriesReader, OpenPullRequestsReader
from pr_reviewer.tui.installation_client import HostedInstallationClient, InstallationClient
from pr_reviewer.tui.installation_snapshot import (
    InstallationSnapshot,
    default_snapshot_path,
    load_installation_snapshot,
    save_installation_snapshot,
)
from pr_reviewer.tui.nav import SECTIONS, SectionNav, SectionSelected
from pr_reviewer.tui.pairing_client import PairingClient
from pr_reviewer.tui.pairing_wait import LocalPairingStatusClient
from pr_reviewer.tui.review_dashboard import ReviewDashboardPanel, dashboard_repositories_from_log
from pr_reviewer.tui.screens.confirm import ConfirmScreen
from pr_reviewer.tui.screens.connect import ConnectPanel, PairingExchangeable, can_start_review
from pr_reviewer.tui.screens.model_access import ModelAccessPanel, ModelKeyStored
from pr_reviewer.tui.screens.profile import ProfilePanel
from pr_reviewer.tui.screens.prompts import AgentPromptsPanel
from pr_reviewer.tui.screens.repositories import PullRequestSelected, RepositoriesPanel
from pr_reviewer.tui.screens.review import ReviewDiffItem, ReviewPanel
from pr_reviewer.tui.theme import REVIEWER_CSS, REVIEWER_THEME


class MainLayout(Horizontal):
    """Holds the sidebar and the content pane.

    Screen binds tab/shift+tab to its own app.focus_next/focus_previous (see
    textual/screen.py), and that binding sits closer to a focused widget than the App's own
    BINDINGS -- so without this, tab only ever walks the flat, whole-app focus order and the
    App-level pane-switch actions below never run. Binding tab/shift+tab again here, one
    level above both panes, intercepts before Screen's default and makes the crossing
    pane-aware instead of accidental.
    """

    BINDINGS = [
        ("tab", "app.focus_next_pane", "Next pane"),
        ("shift+tab", "app.focus_previous_pane", "Prev pane"),
    ]




class _InstallationSnapshotReady(Message):
    """Posted after a background installation fetch finishes."""

    def __init__(
        self,
        snapshot: InstallationSnapshot | None,
        problem: str | None,
        *,
        elapsed_seconds: float,
    ) -> None:
        self.snapshot = snapshot
        self.problem = problem
        self.elapsed_seconds = elapsed_seconds
        super().__init__()

class ReviewerApp(App[None]):
    TITLE = "reviewer"
    CSS = REVIEWER_CSS

    # tab/shift+tab already move focus between widgets (Screen binds them to
    # app.focus_next/focus_previous), but that alone treats the sidebar and the content
    # pane as one flat list of buttons -- nothing marks "you just crossed into the other
    # pane". These bindings make that crossing a first-class, visible action: the footer
    # names every key, and the CSS above gives the pane that holds focus a distinct
    # background so the crossing is never only a hover effect.
    BINDINGS = [
        Binding("tab", "focus_next_pane", "Next pane", show=True),
        Binding("shift+tab", "focus_previous_pane", "Prev pane", show=True),
        Binding("down", "focus_down", "Down", show=True),
        Binding("up", "focus_up", "Up", show=True),
        Binding("enter", "activate_focused", "Open", show=True),
        Binding("escape", "go_back", "Back", show=True),
        Binding("1", "jump_section(0)", SECTIONS[0], show=True),
        Binding("2", "jump_section(1)", SECTIONS[1], show=True),
        Binding("3", "jump_section(2)", SECTIONS[2], show=True),
        Binding("4", "jump_section(3)", SECTIONS[3], show=True),
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("l", "log_out", "Log out", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(
        self,
        *,
        secrets: SecretStore | None = None,
        pairing_client: PairingClient | None = None,
        installation_client: InstallationClient | None = None,
        installation_snapshot: InstallationSnapshot | None = None,
        repo_config: RepoConfigStore | None = None,
        review_log: ReviewLogStore | None = None,
        config_dir: Path | None = None,
        auto_review_event_source: AutoReviewEventSource | None = None,
        auto_review_poll_interval: float = 1.0,
        local_pairing_status_client: LocalPairingStatusClient | None = None,
        pairing_poll_interval: float = 2.0,
        browser_opener: Callable[[str], None] | None = None,
        repositories_reader: InstallationRepositoriesReader | None = None,
        pull_requests_reader: OpenPullRequestsReader | None = None,
    ) -> None:
        super().__init__()
        self.register_theme(REVIEWER_THEME)
        self.theme = REVIEWER_THEME.name
        self._config_dir = config_dir or default_config_dir()
        self._secrets = secrets or get_secret_store(file_fallback_directory=self._config_dir)
        self._pairing_client = pairing_client
        self._installation_client = installation_client or HostedInstallationClient()
        self._installation_snapshot = installation_snapshot
        self._installation_problem = "Installation details are not available yet."
        self._repo_config = repo_config or RepoConfigStore(
            default_repo_config_path(self._config_dir)
        )
        self._review_log = review_log or ReviewLogStore(
            default_review_log_path(self._config_dir)
        )
        self._auto_review_event_source = auto_review_event_source
        self._auto_review_poll_interval = auto_review_poll_interval
        self._auto_review = AutoReviewCoordinator(on_start_review=self._on_auto_review_start)
        self._auto_review_timer: Any = None
        self._auto_review_was_running = False
        # Deliberately no HttpLocalPairingStatusClient default: that pointed sign-in at the
        # local daemon on 127.0.0.1:8742, which is not running when a new user first types
        # `reviewer`. Left as None, ConnectPanel polls the hosted plane, which is where the
        # pairing state lives and which is reachable before any local setup exists.
        self._local_pairing_status_client = local_pairing_status_client
        self._pairing_poll_interval = pairing_poll_interval
        self._browser_opener = browser_opener
        self._repositories_reader = repositories_reader
        self._pull_requests_reader = pull_requests_reader
        self._awaiting_initial_installation = False

    def _tui_error_log_path(self) -> Path:
        return self._config_dir / "tui-errors.log"

    def _log_tui_error(self, error: Exception, *, context: str) -> None:
        path = self._tui_error_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).isoformat()
        detail = traceback.format_exc()
        if not detail or detail.strip() == "NoneType: None":
            detail = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp} | {context}\n{detail}\n")

    async def _replace_pane_children(
        self,
        pane: Container,
        *widgets: Widget,
    ) -> None:
        async with pane.batch():
            await pane.remove_children()
            if widgets:
                await pane.mount(*widgets)

    def _section_error_message(self) -> Static:
        log_path = self._tui_error_log_path()
        return Static(
            (
                "Something went wrong loading this section. "
                f"Details are in {log_path}. Try again or restart reviewer."
            ),
            id="section-error",
        )

    @property
    def github_connected(self) -> bool:
        return is_github_connected(self._secrets)

    @property
    def model_key_configured(self) -> bool:
        return has_model_key(self._secrets)

    def compose(self) -> ComposeResult:
        if self.github_connected:
            yield MainLayout(
                SectionNav(id="section-nav"),
                Container(
                    Static("checking sign-in...", id="startup-status"),
                    id="section-content",
                ),
                id="main-layout",
            )
            yield Footer()
            return

        yield MainLayout(
            SectionNav(id="section-nav"),
            ConnectPanel(
                pairing_client=self._pairing_client,
                local_status_client=self._local_pairing_status_client,
                browser_opener=self._browser_opener,
                pairing_poll_interval=self._pairing_poll_interval,
                id="connect-screen",
            ),
            id="main-layout",
        )
        yield Footer()

    def on_mount(self) -> None:
        if not self.github_connected:
            return
        if not self.model_key_configured:
            self._mount_model_access_panel()
            return
        self._begin_connected_startup()

    def on_unmount(self) -> None:
        self._stop_auto_review()


    def on_pairing_exchangeable(self, message: PairingExchangeable) -> None:
        # self._pairing_client is a test-injection seam, not the client that ran this
        # pairing attempt: in real use it is None and ConnectPanel built its own
        # HostedPairingClient, which lives on that widget, not on this App. Reusing it
        # here would need a widget reference this handler has no business holding, so a
        # fresh client for the same hosted_origin is built instead -- message.hosted_origin
        # exists on PairingExchangeable for exactly this.
        if self._pairing_client is not None:
            client = self._pairing_client
        else:
            from pr_reviewer.tui.pairing_client import HostedPairingClient

            client = HostedPairingClient(message.hosted_origin)
        try:
            credential = client.exchange(message.code, message.verifier)
        except Exception as exc:  # noqa: BLE001 - a failed exchange must never crash the TUI
            # Textual's default reaction to an uncaught exception here is to panic and exit
            # the whole app, with the ConnectPanel still saying "signed in" as the last thing
            # on screen -- indistinguishable from a random crash right after a real sign-in.
            self._report_exchange_failure(exc)
            return
        # The credential is stored -- this is the real "signed in", not the premature one
        # ConnectPanel used to show on approval alone, before the exchange that can still
        # fail (a 409 from an already-held repository, say) had even been attempted.
        self._secrets.set(RUNNER_CREDENTIAL_SECRET, credential)
        try:
            connect_panel = self.query_one(ConnectPanel)
        except NoMatches:
            connect_panel = None
        if connect_panel is not None:
            connect_panel.show_signed_in()
        # A beat to actually see the green "signed in" and the Sign in button gone before
        # the screen changes underneath it -- rebuilding in the same tick made that
        # confirmation invisible, since the whole panel it appeared on was removed in the
        # same breath it was shown. The countdown is what makes that beat visible rather
        # than just a pause nobody can see happening.
        self._start_post_sign_in_countdown(connect_panel)

    def _start_post_sign_in_countdown(
        self, connect_panel: ConnectPanel | None, seconds: int = 5
    ) -> None:
        remaining = seconds

        def tick() -> None:
            nonlocal remaining
            remaining -= 1
            if connect_panel is not None:
                connect_panel.pairing_status = (
                    f"signed in -- continuing in {remaining}s..." if remaining > 0 else "signed in"
                )
            if remaining <= 0:
                timer.stop()
                self._rebuild_after_pairing()

        timer = self.set_interval(1.0, tick)

    def _report_exchange_failure(self, exc: Exception) -> None:
        reason = _exchange_failure_reason(exc)
        self.notify(f"Sign-in did not complete: {reason}", severity="error", timeout=10)
        try:
            connect_panel = self.query_one(ConnectPanel)
        except NoMatches:
            return
        connect_panel.pairing_status = f"pairing failed: {reason}"

    def _rebuild_after_pairing(self) -> None:
        layout = self.query_one("#main-layout")
        self.query_one("#connect-screen").remove()
        layout.mount(Container(id="section-content"))
        if not self.model_key_configured:
            self._mount_model_access_panel()
            return
        self._begin_connected_startup()

    async def on_model_key_stored(self, _message: ModelKeyStored) -> None:
        pane = self.query_one("#section-content", Container)
        await self._replace_pane_children(pane)
        self._begin_connected_startup()

    async def on_pull_request_selected(self, message: PullRequestSelected) -> None:
        snapshot = self._resolve_installation_snapshot()
        if snapshot is None:
            return
        self.query_one(SectionNav).current_section = "reviews"
        await self._show_section(
            "reviews",
            snapshot,
            review_id=f"pr-{message.pull_request_number}",
        )

    async def on_section_selected(self, message: SectionSelected) -> None:
        if message.section_id == "reviews" and not can_start_review(
            self.github_connected,
            model_key_present=self.model_key_configured,
        ):
            if not self.github_connected:
                self.notify("Connect GitHub before starting a review.", severity="warning")
            else:
                self.notify("Add a model key before starting a review.", severity="warning")
            return
        if not self.github_connected or not self.model_key_configured:
            return
        snapshot = self._resolve_installation_snapshot()
        if snapshot is None:
            # Leaving whichever section was on screen before looked identical to this
            # section having loaded and having nothing to show -- the whole point of
            # _installation_problem is to say why, not to be read only on first connect.
            pane = self.query_one("#section-content", Container)
            await self._replace_pane_children(
                pane,
                Static(self._installation_problem, id="installation-missing"),
            )
            return
        await self._show_section(message.section_id, snapshot)

    def _mount_model_access_panel(self) -> None:
        self.query_one("#section-content", Container).mount(
            ModelAccessPanel(secrets=self._secrets, id="model-access-screen")
        )

    def _mount_default_section(self) -> None:
        self.call_next(self._mount_default_section_async)

    async def _mount_default_section_async(self) -> None:
        snapshot = self._resolve_installation_snapshot()
        if snapshot is None:
            pane = self.query_one("#section-content", Container)
            await self._replace_pane_children(
                pane,
                Static(self._installation_problem, id="installation-missing"),
            )
            return
        await self._show_section("repositories", snapshot)

    def _begin_connected_startup(self) -> None:
        cached = self._load_cached_installation_snapshot()
        if cached is not None:
            self._installation_snapshot = cached
            self._mount_default_section()
            self._start_auto_review()
        else:
            self._awaiting_initial_installation = True
            try:
                self.query_one("#startup-status", Static).update("checking sign-in...")
            except NoMatches:
                self._show_startup_status("checking sign-in...")
        self._refresh_installation_snapshot_async()

    def _show_startup_status(self, message: str) -> None:
        try:
            self.query_one("#startup-status", Static).update(message)
            return
        except NoMatches:
            pass
        self.call_next(self._show_startup_status_async, message)

    async def _show_startup_status_async(self, message: str) -> None:
        try:
            pane = self.query_one("#section-content", Container)
        except NoMatches:
            return
        await self._replace_pane_children(pane, Static(message, id="startup-status"))

    def _load_cached_installation_snapshot(self) -> InstallationSnapshot | None:
        if self._installation_snapshot is not None:
            return self._installation_snapshot
        return load_installation_snapshot(default_snapshot_path(self._config_dir))

    @work(thread=True, exclusive=True)
    def _refresh_installation_snapshot_async(self) -> None:
        started = time.monotonic()
        snapshot, problem = self._fetch_installation_snapshot_from_network()
        elapsed = time.monotonic() - started
        self.post_message(
            _InstallationSnapshotReady(
                snapshot,
                problem,
                elapsed_seconds=elapsed,
            )
        )

    def on__installation_snapshot_ready(self, message: _InstallationSnapshotReady) -> None:
        if message.problem and self._installation_snapshot is None:
            self._installation_problem = message.problem
            self._show_startup_status(message.problem)
            return
        if message.snapshot is not None:
            save_installation_snapshot(
                default_snapshot_path(self._config_dir),
                message.snapshot,
            )
            self._installation_snapshot = message.snapshot
        if not self._awaiting_initial_installation:
            return
        self._awaiting_initial_installation = False
        if self._installation_snapshot is not None:
            self._mount_default_section()
            self._start_auto_review()

    def _fetch_installation_snapshot_from_network(
        self,
    ) -> tuple[InstallationSnapshot | None, str | None]:
        credential = self._secrets.get(RUNNER_CREDENTIAL_SECRET)
        hosted_origin = _hosted_origin_from_env()
        if not credential:
            return None, "This terminal is not paired yet. Sign in to connect it."
        if hosted_origin is None:
            return None, "No hosted plane is configured for this terminal."
        try:
            fetched = self._installation_client.fetch(hosted_origin, credential)
        except Exception as exc:  # noqa: BLE001 - every failure has to reach the screen in words
            if "401" in str(exc) or "unknown_credential" in str(exc):
                return None, (
                    "This terminal's pairing is no longer recognised by reviewer.niresh.tech. "
                    "Sign in again to re-pair it."
                )
            return None, f"Could not reach reviewer.niresh.tech ({exc})."
        return fetched, None

    def _resolve_installation_snapshot(self) -> InstallationSnapshot | None:
        if self._installation_snapshot is not None:
            return self._installation_snapshot
        cached = self._load_cached_installation_snapshot()
        if cached is not None:
            self._installation_snapshot = cached
            return cached
        return None

    def _start_auto_review(self) -> None:
        if not self.github_connected or not self.model_key_configured:
            return
        if self._auto_review.running:
            return
        self._auto_review.start()
        self._auto_review_was_running = True
        if self._auto_review_event_source is None:
            return
        self._auto_review_timer = self.set_interval(
            self._auto_review_poll_interval,
            self._poll_auto_review_events,
        )

    def _stop_auto_review(self) -> None:
        if self._auto_review_timer is not None:
            self._auto_review_timer.stop()
            self._auto_review_timer = None
        if self._auto_review.running:
            self._auto_review.stop()

    def _poll_auto_review_events(self) -> None:
        if self._auto_review_event_source is None:
            return
        for event in self._auto_review_event_source.poll():
            self._auto_review.handle(event)

    def _on_auto_review_start(
        self,
        event: PullRequestSyncEvent,
        superseded: bool,
        _previous_head_sha: str,
    ) -> None:
        outcome = AutoReviewOutcome(
            kind="superseded" if superseded else "started",
            pull_request_number=event.pull_request_number,
            head_sha=event.head_sha,
        )
        self._show_auto_review(outcome)

    def _show_auto_review(self, outcome: AutoReviewOutcome) -> None:
        if outcome.kind not in {"started", "superseded"}:
            return
        message = f"Reviewing PR #{outcome.pull_request_number}"
        if outcome.kind == "superseded":
            message += " (superseded previous run)"
        self.notify(message)
        snapshot = self._resolve_installation_snapshot()
        if snapshot is None:
            return
        if "section-nav" in {widget.id for widget in self.query("#section-nav")}:
            # Set the reactive directly rather than select_section(): that also posts
            # SectionSelected, which on_section_selected would handle by calling
            # _show_section again with the default review_id, clobbering the
            # PR-scoped ReviewPanel this method is about to mount below.
            self.query_one(SectionNav).current_section = "reviews"
        self.call_next(
            self._show_section,
            "reviews",
            snapshot,
            review_id=f"pr-{outcome.pull_request_number}",
        )

    async def _show_section(
        self,
        section_id: str,
        snapshot: InstallationSnapshot,
        *,
        review_id: str = "live-review",
    ) -> None:
        pane = self.query_one("#section-content", Container)
        try:
            if section_id not in SECTIONS:
                await self._replace_pane_children(
                    pane,
                    Static(section_id, id="section-placeholder"),
                )
                return
            if section_id == "reviews" and (
                not self.github_connected or not self.model_key_configured
            ):
                return
            if section_id == "profile":
                await self._replace_pane_children(pane, ProfilePanel(snapshot))
                return
            if section_id == "repositories":
                await self._replace_pane_children(
                    pane,
                    RepositoriesPanel(
                        snapshot.installation_id,
                        repositories_reader=self._repositories_reader,
                        pull_requests_reader=self._pull_requests_reader,
                    ),
                )
                return
            if section_id == "agent-prompts":
                await self._replace_pane_children(
                    pane,
                    AgentPromptsPanel(snapshot, repo_config=self._repo_config),
                )
                return
            if section_id == "reviews":
                if review_id != "live-review":
                    await self._replace_pane_children(
                        pane,
                        ReviewPanel(
                            (
                                ReviewDiffItem(
                                    "app.py",
                                    "@@ -1,1 +1,2 @@\n-old\n+new\n",
                                ),
                                ReviewDiffItem(
                                    "README.md",
                                    "@@ -1,1 +1,2 @@\n # Widgets\n+More docs\n",
                                ),
                            ),
                            review_log=self._review_log,
                            review_id=review_id,
                        ),
                    )
                    return
                await self._replace_pane_children(
                    pane,
                    ReviewDashboardPanel(
                        dashboard_repositories_from_log(snapshot, self._review_log),
                        id="reviews-dashboard",
                    ),
                )
                return
            await self._replace_pane_children(
                pane,
                Static(section_id, id="section-placeholder"),
            )
        except Exception as exc:  # noqa: BLE001 - section failures must stay in the UI
            self._log_tui_error(exc, context=f"mount section {section_id}")
            await self._replace_pane_children(pane, self._section_error_message())

    def _handle_exception(self, error: Exception) -> None:
        """Log and close without dumping Rich tracebacks or locals to the terminal."""
        self._return_code = 1
        if self._exception is None:
            self._exception = error
            self._exception_event.set()
        self._log_tui_error(error, context="unhandled tui error")
        self._exit_renderables.clear()
        self._close_messages_no_wait()

    # -- keyboard model: move focus between the sidebar and the content pane, move within
    # whichever pane holds focus, jump straight to a section, and help/quit. tab/shift+tab
    # already move focus widget-by-widget (Screen binds those to focus_next/focus_previous),
    # but that treats the whole app as one flat list -- these actions instead treat the
    # sidebar and the content pane as exactly two panes, and only ever move within or
    # between those two, so "which pane is live" stays a deliberate, visible choice (see the
    # :focus-within backgrounds in theme.py and nav.py) rather than an accident of tab order.

    def _panes(self) -> tuple[Widget, Widget] | None:
        try:
            nav = self.query_one("#section-nav", Widget)
            content = self.query_one("#section-content", Widget)
        except NoMatches:
            return None
        return nav, content

    def _focusables(self, pane: Widget) -> list[Widget]:
        return [widget for widget in pane.query("*") if widget.can_focus]

    def _pane_holding_focus(self) -> Widget | None:
        panes = self._panes()
        focused = self.focused
        if panes is None or focused is None:
            return None
        for pane in panes:
            if any(focused is widget for widget in pane.query("*")):
                return pane
        return None

    def action_focus_next_pane(self) -> None:
        self._switch_pane()

    def action_focus_previous_pane(self) -> None:
        self._switch_pane()

    def _switch_pane(self) -> None:
        panes = self._panes()
        if panes is None:
            return
        nav, content = panes
        current = self._pane_holding_focus()
        target = content if current is nav else nav
        focusables = self._focusables(target)
        if focusables:
            focusables[0].focus()

    def action_focus_down(self) -> None:
        self._move_within_pane(1)

    def action_focus_up(self) -> None:
        self._move_within_pane(-1)

    def _move_within_pane(self, offset: int) -> None:
        pane = self._pane_holding_focus()
        if pane is None:
            return
        focusables = self._focusables(pane)
        if not focusables:
            return
        focused = self.focused
        try:
            index = next(i for i, widget in enumerate(focusables) if widget is focused)
        except StopIteration:
            index = 0
        focusables[(index + offset) % len(focusables)].focus()

    def action_activate_focused(self) -> None:
        focused = self.focused
        if focused is not None and hasattr(focused, "press"):
            focused.press()

    def action_go_back(self) -> None:
        panes = self._panes()
        if panes is None:
            return
        try:
            dashboard = self.query_one(ReviewDashboardPanel)
        except NoMatches:
            dashboard = None
        if dashboard is not None and dashboard.back_to_table():
            return
        nav, _content = panes
        focusables = self._focusables(nav)
        if focusables:
            focusables[0].focus()

    def action_jump_section(self, index: int) -> None:
        if not 0 <= index < len(SECTIONS):
            return
        try:
            self.query_one(SectionNav).select_section(SECTIONS[index])
        except NoMatches:
            return

    def action_show_help(self) -> None:
        self.notify(
            "tab/shift+tab: switch pane  up/down: move  enter: open  escape: back to nav  "
            "1-4: jump to a section  l: log out  q: quit",
            title="Keys",
            timeout=8,
        )

    def action_log_out(self) -> None:
        if not self.github_connected:
            self.notify("Not signed in.", severity="warning")
            return
        # Revoking is not something a stray keypress or an accidental click on the
        # footer's own "Log out" hint gets to do by itself: pairing.py has no way to
        # un-revoke a runner, so this session is genuinely gone once confirmed.
        # push_screen's own wait_for_dismiss=True requires running inside a worker,
        # which an action is not, so the continuation is a callback instead.
        self.push_screen(
            ConfirmScreen(
                "Log out of this terminal? You will need to sign in again to review.",
                confirm_label="Log out",
            ),
            self._log_out_if_confirmed,
        )

    async def _log_out_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        credential = self._secrets.get(RUNNER_CREDENTIAL_SECRET)
        hosted_origin = _hosted_origin_from_env()
        runner_client: RunnerClient | None = None
        if credential and hosted_origin:
            runner_client = RunnerClient(hosted_origin, credential)
        log_out(self._secrets, runner_client=runner_client)
        # The cached snapshot names the installation and repositories the credential just
        # deleted was scoped to -- leaving it on disk would show a signed-out terminal
        # someone else's profile and repository list the moment they pair a new account.
        default_snapshot_path(self._config_dir).unlink(missing_ok=True)
        self._stop_auto_review()
        self.notify("Signed out.")
        await self.recompose()


def _exchange_failure_reason(exc: Exception) -> str:
    """A word a person can act on, not a stack trace.

    The one exchange failure worth naming specifically is 409: exchange_pairing_code_route
    returns it with a detail saying exactly which other runner already holds the
    repository (see control_plane/repository_policy.assign_repository_to_runner) -- that
    is actionable in a way "HTTP 409" alone is not.
    """
    import httpx

    if isinstance(exc, httpx.HTTPStatusError):
        try:
            detail = exc.response.json().get("detail")
        except Exception:  # noqa: BLE001 - a malformed error body must not itself raise
            detail = None
        if isinstance(detail, str) and detail:
            return detail
        return f"the hosted plane returned {exc.response.status_code}"
    return str(exc)


def _hosted_origin_from_env() -> str | None:
    """The hosted origin this runner talks to, defaulting to production.

    This used to read PR_REVIEWER_HOSTED_ORIGIN and return None when it was unset. A real
    install never sets it, so the snapshot fetch was skipped, the cached snapshot did not
    exist either, and every section rendered "Installation details are not available yet."
    """
    from pr_reviewer.tui.github_connect import HostedOriginError, resolved_hosted_origin

    try:
        return resolved_hosted_origin()
    except HostedOriginError:
        return None


def run_tui() -> int:
    app = ReviewerApp()
    app.run()
    if app._auto_review_was_running:
        print(TUI_CLOSED_AUTO_REVIEW_MESSAGE, file=sys.stderr)
    return 0
