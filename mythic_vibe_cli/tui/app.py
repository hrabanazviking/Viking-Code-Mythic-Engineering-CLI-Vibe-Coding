"""Textual TUI app for Mythic Vibe CLI.

Cross-platform: Textual is pure Python (MIT) and handles terminal differences
across Windows / macOS / Linux without per-OS branches. This module imports
``textual`` at module load; callers that need to handle a missing-textual
case must catch ``ImportError`` at the call site.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ..core.state import PHASES, ProjectState
from ..persistence.json_store import JsonStateStore
from ..plugins.registry import PluginRegistry
from ..runtime.event_log import EventLogEntry, event_log_path_for, read_recent
from ..verify import load_latest_verification


REFRESH_INTERVAL_SECONDS = 2.0


# ---- Loop Navigator (PH-04 slice 4.1) -----------------------------------


PHASE_STATE_CURRENT = "current"
PHASE_STATE_COMPLETED = "completed"
PHASE_STATE_PENDING = "pending"

# Map state markers to single-character glyphs that render in any
# terminal (no emoji, no fancy unicode that confuses Windows
# consoles with the legacy code page). Cross-platform safe.
_PHASE_GLYPHS: dict[str, str] = {
    PHASE_STATE_CURRENT: ">",
    PHASE_STATE_COMPLETED: "x",
    PHASE_STATE_PENDING: ".",
}


@dataclass
class LoopNavigatorEntry:
    """One row in the Loop Navigator panel."""

    phase: str
    state: str  # one of PHASE_STATE_*
    marker: str  # rendered glyph

    def to_dict(self) -> dict[str, str]:
        return {"phase": self.phase, "state": self.state, "marker": self.marker}


@dataclass
class LoopNavigatorData:
    """The full set of phase rows the panel renders."""

    entries: list[LoopNavigatorEntry] = field(default_factory=list)
    current_phase: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [entry.to_dict() for entry in self.entries],
            "current_phase": self.current_phase,
        }


def build_loop_navigator_data(root: Path) -> LoopNavigatorData:
    """Pure function (no Textual deps) that classifies every Mythic
    phase as current / completed / pending given the project state.

    Falls back to a default ProjectState (every phase pending) when
    the on-disk state cannot be loaded — never raises.
    """
    state = _safe_load_state(root)
    completed_set = {phase for phase in state.completed_phases if phase in PHASES}
    current_phase = state.current_phase if state.current_phase in PHASES else ""

    entries: list[LoopNavigatorEntry] = []
    for phase in PHASES:
        if phase == current_phase:
            phase_state = PHASE_STATE_CURRENT
        elif phase in completed_set:
            phase_state = PHASE_STATE_COMPLETED
        else:
            phase_state = PHASE_STATE_PENDING
        entries.append(
            LoopNavigatorEntry(
                phase=phase,
                state=phase_state,
                marker=_PHASE_GLYPHS[phase_state],
            )
        )
    return LoopNavigatorData(entries=entries, current_phase=current_phase)


def _format_loop_navigator(data: LoopNavigatorData) -> str:
    """Render the Loop Navigator panel as Rich-tagged markup.

    The current phase is bolded and tagged ``$accent``; completed
    phases are dimmed; pending phases keep default colour.
    """
    if not data.entries:
        return "[dim](no phases configured)[/dim]"
    lines: list[str] = []
    for entry in data.entries:
        if entry.state == PHASE_STATE_CURRENT:
            lines.append(f"[b]{entry.marker} {entry.phase}[/b]")
        elif entry.state == PHASE_STATE_COMPLETED:
            lines.append(f"[dim]{entry.marker} {entry.phase}[/dim]")
        else:
            lines.append(f"{entry.marker} {entry.phase}")
    return "\n".join(lines)


@dataclass
class StatusData:
    path: str
    phase: str
    active_task_id: str
    last_verification_id: str
    last_verification_result: str
    last_verification_level: str
    latest_handoff_id: str
    latest_handoff_created_at: str
    latest_handoff_next_step: str
    plugins_enabled: int
    plugins_disabled: int
    refreshed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "phase": self.phase,
            "active_task_id": self.active_task_id,
            "last_verification_id": self.last_verification_id,
            "last_verification_result": self.last_verification_result,
            "last_verification_level": self.last_verification_level,
            "latest_handoff_id": self.latest_handoff_id,
            "latest_handoff_created_at": self.latest_handoff_created_at,
            "latest_handoff_next_step": self.latest_handoff_next_step,
            "plugins_enabled": self.plugins_enabled,
            "plugins_disabled": self.plugins_disabled,
            "refreshed_at": self.refreshed_at,
        }


def _safe_load_state(root: Path) -> ProjectState:
    try:
        return JsonStateStore(root).load_state()
    except (OSError, ValueError):
        return ProjectState()


def _safe_load_handoff_summary(root: Path) -> tuple[str, str, str]:
    try:
        from ..handoff import load_latest_handoff
    except ImportError:
        return ("(none)", "", "")
    try:
        record = load_latest_handoff(root)
    except (OSError, ValueError):
        return ("(none)", "", "")
    if record is None:
        return ("(none)", "", "")
    next_step = record.next_steps[0] if record.next_steps else ""
    return (record.handoff_id, record.created_at, next_step)


def _safe_load_plugin_counts(root: Path) -> tuple[int, int]:
    try:
        records = PluginRegistry(root).load()
    except (OSError, ValueError):
        return (0, 0)
    enabled = sum(1 for r in records if r.enabled)
    disabled = sum(1 for r in records if not r.enabled)
    return (enabled, disabled)


def build_status_data(root: Path) -> StatusData:
    """Pure function (no Textual deps) that gathers project status snapshot.

    Used by the TUI screen on each refresh, and tested directly in unit tests.
    """
    state = _safe_load_state(root)
    handoff_id, handoff_created_at, handoff_next_step = _safe_load_handoff_summary(root)
    enabled, disabled = _safe_load_plugin_counts(root)

    last_verification_id = state.last_verification_id or "(none)"
    last_verification_result = "(unknown)"
    last_verification_level = "(unknown)"
    record = load_latest_verification(root)
    if record is not None:
        last_verification_id = record.verification_id
        last_verification_result = record.result
        last_verification_level = record.level

    return StatusData(
        path=str(root),
        phase=state.current_phase or "(none)",
        active_task_id=state.active_task_id or "(none)",
        last_verification_id=last_verification_id,
        last_verification_result=last_verification_result,
        last_verification_level=last_verification_level,
        latest_handoff_id=handoff_id,
        latest_handoff_created_at=handoff_created_at,
        latest_handoff_next_step=handoff_next_step or "(none)",
        plugins_enabled=enabled,
        plugins_disabled=disabled,
    )


def _format_status_panel(data: StatusData) -> str:
    return (
        f"[b]Path:[/b]        {data.path}\n"
        f"[b]Phase:[/b]       {data.phase}\n"
        f"[b]Active task:[/b] {data.active_task_id}"
    )


def _format_verify_panel(data: StatusData) -> str:
    return (
        f"[b]Result:[/b] {data.last_verification_result}\n"
        f"[b]ID:[/b]     {data.last_verification_id}\n"
        f"[b]Level:[/b]  {data.last_verification_level}"
    )


def _format_handoff_panel(data: StatusData) -> str:
    next_step = data.latest_handoff_next_step
    if len(next_step) > 60:
        next_step = next_step[:57] + "..."
    return (
        f"[b]ID:[/b]        {data.latest_handoff_id}\n"
        f"[b]Created:[/b]   {data.latest_handoff_created_at or '(n/a)'}\n"
        f"[b]Next step:[/b] {next_step}"
    )


def _format_plugins_panel(data: StatusData) -> str:
    return f"[b]{data.plugins_enabled} enabled[/b], {data.plugins_disabled} disabled"


def _format_events_panel(entries: list[EventLogEntry]) -> str:
    if not entries:
        return "[dim](no events recorded yet)[/dim]"
    lines: list[str] = []
    # Display newest first so the latest event sits at the top of the panel.
    for entry in reversed(entries):
        time_token = entry.timestamp[11:19] if len(entry.timestamp) >= 19 else entry.timestamp
        summary = entry.summary or "(empty)"
        lines.append(f"[dim]{time_token}[/dim] [b]{entry.channel}[/b] {summary}")
    return "\n".join(lines)


def _format_footer_line(data: StatusData) -> str:
    return f"Last refresh: {data.refreshed_at}"


class StatusScreen(Screen):
    """Single screen showing four status panels with auto-refresh."""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("r", "refresh_now", "Refresh"),
        Binding("slash", "open_picker", "/  Slash picker"),
    ]

    DEFAULT_CSS = """
    StatusScreen {
        layout: vertical;
    }

    #main-row {
        layout: horizontal;
        height: 1fr;
    }

    #loop-nav-panel {
        border: round $secondary;
        padding: 1 2;
        margin: 1 0 1 1;
        width: 26;
    }

    #right-column {
        layout: vertical;
        width: 1fr;
    }

    #grid {
        layout: grid;
        grid-size: 2 2;
        grid-gutter: 1;
        padding: 1;
        height: 14;
    }

    #events-panel {
        border: round $secondary;
        padding: 1 2;
        margin: 0 1 1 1;
        height: 1fr;
    }

    .panel {
        border: round $secondary;
        padding: 1 2;
        height: 100%;
    }

    #footer-line {
        padding: 0 2;
        height: 1;
        color: $text-muted;
    }
    """

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self._loop_nav_widget = Static(id="loop-nav-panel")
        self._status_widget = Static(id="panel-status", classes="panel")
        self._verify_widget = Static(id="panel-verify", classes="panel")
        self._handoff_widget = Static(id="panel-handoff", classes="panel")
        self._plugins_widget = Static(id="panel-plugins", classes="panel")
        self._events_widget = Static(id="events-panel")
        self._footer_widget = Static(id="footer-line")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-row"):
            yield self._loop_nav_widget
            with Vertical(id="right-column"):
                with Grid(id="grid"):
                    yield self._status_widget
                    yield self._verify_widget
                    yield self._handoff_widget
                    yield self._plugins_widget
                yield self._events_widget
        yield self._footer_widget
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_panels()
        self.set_interval(REFRESH_INTERVAL_SECONDS, self._refresh_panels)

    def action_refresh_now(self) -> None:
        self._refresh_panels()

    def action_open_picker(self) -> None:
        from .picker import SlashPickerScreen

        self.app.push_screen(SlashPickerScreen(self.root))

    def _refresh_panels(self) -> None:
        data = build_status_data(self.root)
        loop_nav_data = build_loop_navigator_data(self.root)
        events = read_recent(event_log_path_for(self.root), limit=12)
        self._loop_nav_widget.border_title = "Loop"
        self._status_widget.border_title = "Status"
        self._verify_widget.border_title = "Verification"
        self._handoff_widget.border_title = "Latest Handoff"
        self._plugins_widget.border_title = "Plugins"
        self._events_widget.border_title = "Recent Events"
        self._loop_nav_widget.update(_format_loop_navigator(loop_nav_data))
        self._status_widget.update(_format_status_panel(data))
        self._verify_widget.update(_format_verify_panel(data))
        self._handoff_widget.update(_format_handoff_panel(data))
        self._plugins_widget.update(_format_plugins_panel(data))
        self._events_widget.update(_format_events_panel(events))
        self._footer_widget.update(_format_footer_line(data))


class MythicTuiApp(App):
    TITLE = "Mythic Vibe TUI"
    SUB_TITLE = "Project status"

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root

    def on_mount(self) -> None:
        self.push_screen(StatusScreen(self.root))


def run_tui(root: Path) -> int:
    """Entry point invoked by ``cmd_tui`` — opens the app and blocks until quit."""
    MythicTuiApp(root).run()
    return 0
