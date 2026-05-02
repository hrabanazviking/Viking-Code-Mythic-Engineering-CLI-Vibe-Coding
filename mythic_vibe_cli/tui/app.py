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

import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ..core.state import PHASES, ProjectState
from ..persistence.json_store import JsonStateStore
from ..plugins.registry import PluginRegistry
from ..runtime.event_log import (
    EventStreamSnapshot,
    EventTailReader,
    event_log_path_for,
)
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


# ---- Artifact Viewer (PH-04 slice 4.2) ---------------------------------


ARTIFACT_STATUS_PRESENT = "present"
ARTIFACT_STATUS_MISSING = "missing"
ARTIFACT_STATUS_STALE = "stale"

# Single-character markers (ASCII; Windows legacy code page-safe).
_ARTIFACT_GLYPHS: dict[str, str] = {
    ARTIFACT_STATUS_PRESENT: "+",
    ARTIFACT_STATUS_MISSING: "-",
    ARTIFACT_STATUS_STALE: "~",
}

# Per-phase canonical artefact list. Paths are relative to the
# project root. Each phase's entries are a mix of files the
# operator should have authored or updated by the time they reach
# that phase's verify gate.
PHASE_ARTEFACTS: dict[str, list[str]] = {
    "intent": [
        "MYTHIC_ENGINEERING.md",
        "SYSTEM_VISION.md",
        "docs/PHILOSOPHY.md",
    ],
    "constraints": [
        "docs/INVARIANTS.md",
        "docs/RISK_REGISTER.md",
        "docs/PHILOSOPHY.md",
    ],
    "architecture": [
        "docs/ARCHITECTURE.md",
        "docs/DOMAIN_MAP.md",
        "docs/DATA_FLOW.md",
        "docs/ADRS",
    ],
    "plan": [
        "tasks/current_GOALS.md",
        "tasks/backlog.md",
        "docs/INTERFACES",
    ],
    "build": [
        "mythic/codex_prompt.md",
        "mythic/packets",
        "CHANGELOG.md",
    ],
    "verify": [
        "docs/VERIFICATION.md",
        "mythic/verifications",
        "mythic/verifications/latest.json",
    ],
    "reflect": [
        "docs/SESSION_HANDOFF.md",
        "docs/DEVLOG.md",
        "mythic/handoffs",
        "mythic/reflections",
    ],
}

ARTIFACT_STALE_AFTER_DAYS = 14


@dataclass
class ArtifactEntry:
    """One row in the Artifact Viewer panel."""

    relpath: str
    status: str  # one of ARTIFACT_STATUS_*
    marker: str
    age_days: int | None = None  # mtime age in days; None for missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "relpath": self.relpath,
            "status": self.status,
            "marker": self.marker,
            "age_days": self.age_days,
        }


@dataclass
class ArtifactViewerData:
    """The full artefact list for the current phase."""

    phase: str
    entries: list[ArtifactEntry] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "entries": [entry.to_dict() for entry in self.entries],
        }


def _classify_artifact(
    target: Path,
    *,
    now: float,
    stale_after_seconds: float,
) -> tuple[str, int | None]:
    """Return ``(status, age_days)`` for one artefact path.

    A path is ``present`` when it exists; ``missing`` otherwise.
    A present path is further marked ``stale`` when its mtime is
    older than ``stale_after_seconds`` ago. Directories are checked
    against the most recent mtime of their immediate contents
    (recursive walk would be too slow on large dirs).
    """
    if not target.exists():
        return ARTIFACT_STATUS_MISSING, None
    try:
        if target.is_dir():
            # For directories, use the most recent mtime among the
            # directory itself and its immediate contents. Empty dirs
            # use the dir mtime.
            candidate_times: list[float] = [target.stat().st_mtime]
            for child in target.iterdir():
                try:
                    candidate_times.append(child.stat().st_mtime)
                except OSError:
                    continue
            mtime = max(candidate_times)
        else:
            mtime = target.stat().st_mtime
    except OSError:
        return ARTIFACT_STATUS_MISSING, None

    age_seconds = max(0.0, now - mtime)
    age_days = int(age_seconds // 86400)
    if age_seconds > stale_after_seconds:
        return ARTIFACT_STATUS_STALE, age_days
    return ARTIFACT_STATUS_PRESENT, age_days


def build_artifact_viewer_data(
    root: Path,
    phase: str,
    *,
    stale_after_days: int = ARTIFACT_STALE_AFTER_DAYS,
    now: float | None = None,
) -> ArtifactViewerData:
    """Pure function (no Textual deps) that classifies every artefact
    declared for ``phase`` against the project state on disk.

    Falls back to an empty entry list when ``phase`` is unknown
    (operator-edited status.json with a bogus phase name shouldn't
    crash the TUI). The ``now`` keyword exists for tests; production
    callers leave it as None and use ``time.time()``.
    """
    expected_paths = PHASE_ARTEFACTS.get(phase, [])
    if now is None:
        now = time.time()
    stale_after_seconds = float(stale_after_days * 86400)

    entries: list[ArtifactEntry] = []
    for relpath in expected_paths:
        target = root / relpath
        status, age_days = _classify_artifact(
            target,
            now=now,
            stale_after_seconds=stale_after_seconds,
        )
        entries.append(
            ArtifactEntry(
                relpath=relpath,
                status=status,
                marker=_ARTIFACT_GLYPHS[status],
                age_days=age_days,
            )
        )
    return ArtifactViewerData(phase=phase, entries=entries)


def _format_artifact_viewer(data: ArtifactViewerData) -> str:
    """Render the artefact list as Rich-tagged markup.

    Present artefacts keep default colour; missing ones tagged red
    (Rich ``$error`` colour); stale ones tagged yellow (``$warning``).
    Each row carries the relative path and, for present files, the
    age in days.
    """
    if not data.phase:
        return "[dim](no phase set; nothing to track)[/dim]"
    if not data.entries:
        return f"[dim](no canonical artefacts declared for phase '{data.phase}')[/dim]"
    lines: list[str] = []
    for entry in data.entries:
        suffix = ""
        if entry.age_days is not None:
            suffix = f" [dim]({entry.age_days}d)[/dim]"
        if entry.status == ARTIFACT_STATUS_MISSING:
            lines.append(f"[red]{entry.marker}[/red] {entry.relpath}{suffix}")
        elif entry.status == ARTIFACT_STATUS_STALE:
            lines.append(f"[yellow]{entry.marker}[/yellow] {entry.relpath}{suffix}")
        else:
            lines.append(f"[green]{entry.marker}[/green] {entry.relpath}{suffix}")
    return "\n".join(lines)


# ---- Packet Viewer (PH-04 slice 4.3) -----------------------------------


PACKET_PREVIEW_LINES = 12


@dataclass
class PacketViewerData:
    """Snapshot of the current codex packet for the TUI panel.

    A packet exists in three forms on disk:

    1. ``mythic/codex_prompt.md`` — the operator-facing "current"
       packet (rewritten by every ``packet create`` /
       ``codex-pack`` /``forge plan`` invocation).
    2. ``mythic/packets/PKT-NNNN.md`` — durable historical packets
       (slice-2.6 of the production roadmap).
    3. ``mythic/packets/PKT-NNNN.meta.json`` — metadata sidecar.

    The viewer prefers the operator-facing copy first, falling back
    to the most recently written historical packet so the TUI keeps
    showing useful context after a transient ``codex_prompt.md``
    overwrite.
    """

    packet_id: str = ""
    relpath: str = ""
    line_count: int = 0
    byte_size: int = 0
    modified_at: str = ""
    preview_lines: list[str] = field(default_factory=list)
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            "relpath": self.relpath,
            "line_count": self.line_count,
            "byte_size": self.byte_size,
            "modified_at": self.modified_at,
            "preview_lines": list(self.preview_lines),
            "truncated": self.truncated,
        }


def _select_packet_path(root: Path) -> Path | None:
    """Pick the packet to display.

    Preference order:
    1. ``mythic/codex_prompt.md`` (operator-facing current packet).
    2. Most recently modified ``mythic/packets/*.md`` (historical).

    Returns ``None`` when neither exists. Defensive against ``OSError``
    while iterating the packets dir.
    """
    current = root / "mythic" / "codex_prompt.md"
    if current.is_file():
        return current

    packets_dir = root / "mythic" / "packets"
    if not packets_dir.is_dir():
        return None
    try:
        candidates = [p for p in packets_dir.glob("*.md") if p.is_file()]
    except OSError:
        return None
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _packet_id_from_filename(path: Path) -> str:
    """Extract a stable id for the panel header.

    For historical packets at ``mythic/packets/PKT-NNNN.md`` we use
    the stem. For the operator-facing ``codex_prompt.md`` we use a
    fixed sentinel ``codex_prompt`` so the operator can tell which
    packet the panel is rendering.
    """
    if path.name == "codex_prompt.md":
        return "codex_prompt"
    return path.stem


def build_packet_viewer_data(
    root: Path,
    *,
    preview_lines: int = PACKET_PREVIEW_LINES,
) -> PacketViewerData:
    """Pure function (no Textual deps) that snapshots the current
    packet for the panel.

    Returns an empty :class:`PacketViewerData` when no packet exists
    on disk. Truncates the preview to ``preview_lines`` and records a
    ``truncated`` flag when the file has more lines than the cap.

    Defensive: I/O errors fall back to an empty result; the TUI
    must never crash because a packet file disappeared mid-refresh.
    """
    target = _select_packet_path(root)
    if target is None:
        return PacketViewerData()

    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return PacketViewerData()

    lines = text.splitlines()
    snippet = lines[:preview_lines]
    try:
        stat = target.stat()
        modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
        byte_size = stat.st_size
    except OSError:
        modified_at = ""
        byte_size = 0

    try:
        relpath = str(target.relative_to(root))
    except ValueError:
        relpath = str(target)

    return PacketViewerData(
        packet_id=_packet_id_from_filename(target),
        relpath=relpath,
        line_count=len(lines),
        byte_size=byte_size,
        modified_at=modified_at,
        preview_lines=snippet,
        truncated=len(lines) > preview_lines,
    )


def _format_packet_viewer(data: PacketViewerData) -> str:
    """Render the packet preview as Rich-tagged markup.

    Header lines (relpath / line count / modified) are dim; preview
    body is the file's literal text. When no packet exists the panel
    shows a placeholder pointing at ``codex-pack`` / ``forge plan``.
    """
    if not data.relpath:
        return (
            "[dim](no packet on disk yet — run `mythic-vibe codex-pack` "
            "or `forge plan` to create one)[/dim]"
        )

    header_lines = [
        f"[b]{data.packet_id}[/b]",
        f"[dim]{data.relpath}  ·  {data.line_count} lines  ·  {data.byte_size}B[/dim]",
    ]
    if data.modified_at:
        header_lines.append(f"[dim]modified {data.modified_at}[/dim]")
    header_lines.append("")

    body_lines = list(data.preview_lines)
    if data.truncated:
        body_lines.append(f"[dim]... ({data.line_count - len(data.preview_lines)} more lines)[/dim]")

    return "\n".join(header_lines + body_lines)


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


def _format_status_bar(data: StatusData) -> str:
    """Render the consolidated status bar (PH-04 slice 4.4).

    A single dense line replacing the previous 2x2 grid of Status /
    Verify / Handoff / Plugins panels. Sections are separated by
    middle-dot bullets; the warnings tail is colour-coded so the
    operator sees red / yellow / green at a glance.

    Sections in order:
      project basename · phase · verify · handoff · plugins · warnings
    """
    project_name = Path(data.path).name or "(no project)"
    phase = data.phase or "(none)"

    if not data.last_verification_id or data.last_verification_id == "(none)":
        verify = "verify: -"
    else:
        verify = f"verify: {data.last_verification_result} ({data.last_verification_id})"

    if data.latest_handoff_id == "(none)" or not data.latest_handoff_id:
        handoff = "handoff: -"
    else:
        handoff = f"handoff: {data.latest_handoff_id}"

    plugins = f"plugins: {data.plugins_enabled}+{data.plugins_disabled}"

    warnings_parts: list[str] = []
    if data.last_verification_result == "fail":
        warnings_parts.append("[red]verify-failed[/red]")
    if data.plugins_disabled > 0:
        warnings_parts.append(
            f"[yellow]{data.plugins_disabled} plugin(s) disabled[/yellow]"
        )
    warnings = " · ".join(warnings_parts) if warnings_parts else "[green]ok[/green]"

    return (
        f"[b]{project_name}[/b]  ·  "
        f"[dim]phase:[/dim] {phase}  ·  "
        f"[dim]{verify}[/dim]  ·  "
        f"[dim]{handoff}[/dim]  ·  "
        f"[dim]{plugins}[/dim]  ·  "
        f"{warnings}"
    )


def _classify_channel(channel: str) -> str:
    """Map an event channel name to a Rich colour tag.

    Heuristics-only — no central registry to keep in sync. ``error`` /
    ``fail`` words turn the channel red; ``warn`` turns it yellow;
    Mythic's symmetric ``before_*`` / ``after_*`` channels get cyan /
    green so the operator sees the lifecycle bracket at a glance. Any
    other channel keeps the bold-default styling the panel had before
    slice 4.6.
    """
    lowered = channel.lower()
    if "error" in lowered or "fail" in lowered:
        return "red"
    if "warn" in lowered:
        return "yellow"
    if lowered.startswith("before_"):
        return "cyan"
    if lowered.startswith("after_"):
        return "green"
    return "b"


def _format_diagnostics_panel(snapshot: EventStreamSnapshot) -> str:
    """Render a tail-style diagnostics view.

    The first line is a pulse + counter — green ``● live +N new`` when
    the most recent poll delivered new events, otherwise dim ``○ idle``.
    Followed by the sliding window of entries, newest first, with
    channel-class colour coding.
    """
    if snapshot.new_in_last_poll > 0:
        pulse = f"[green]● live[/green]  +{snapshot.new_in_last_poll} new"
    else:
        pulse = "[dim]○ idle[/dim]"
    header = f"{pulse}  ·  [dim]seen: {snapshot.total_seen}[/dim]"

    if not snapshot.entries:
        return f"{header}\n[dim](no events recorded yet)[/dim]"

    lines: list[str] = [header, ""]
    for entry in reversed(snapshot.entries):
        time_token = (
            entry.timestamp[11:19] if len(entry.timestamp) >= 19 else entry.timestamp
        )
        summary = entry.summary or "(empty)"
        tag = _classify_channel(entry.channel)
        lines.append(
            f"[dim]{time_token}[/dim] [{tag}]{entry.channel}[/{tag}] {summary}"
        )
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
        Binding("question_mark", "show_help", "Help"),
        Binding("t", "app.cycle_theme", "Theme"),
        Binding("d", "open_drift", "Drift"),
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

    #mid-row {
        layout: horizontal;
        height: 1fr;
        margin: 1 1 1 1;
    }

    #events-panel {
        border: round $secondary;
        padding: 1 2;
        width: 1fr;
        margin: 0 1 0 0;
    }

    #artifact-panel {
        border: round $secondary;
        padding: 1 2;
        width: 1fr;
        margin: 0 1 0 0;
    }

    #packet-panel {
        border: round $secondary;
        padding: 1 2;
        width: 1fr;
    }

    #status-bar {
        padding: 0 2;
        height: 1;
        background: $panel;
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
        self._events_widget = Static(id="events-panel")
        self._artifact_widget = Static(id="artifact-panel")
        self._packet_widget = Static(id="packet-panel")
        self._status_bar_widget = Static(id="status-bar")
        self._footer_widget = Static(id="footer-line")
        # Tail reader is constructed once per screen lifetime (slice 4.6).
        # Warm-starts from any existing entries so the panel populates
        # immediately, but only counts truly-new events as "live".
        self._event_reader = EventTailReader(event_log_path_for(self.root))

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-row"):
            yield self._loop_nav_widget
            with Vertical(id="right-column"):
                with Horizontal(id="mid-row"):
                    yield self._events_widget
                    yield self._artifact_widget
                    yield self._packet_widget
        yield self._status_bar_widget
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

    def action_show_help(self) -> None:
        from .help_overlay import HelpOverlayScreen, binding_help_pairs

        self.app.push_screen(
            HelpOverlayScreen("Status — keys", binding_help_pairs(self.BINDINGS))
        )

    def action_open_drift(self) -> None:
        from .drift_panel import DriftScreen

        self.app.push_screen(DriftScreen(self.root))

    def _refresh_panels(self) -> None:
        data = build_status_data(self.root)
        loop_nav_data = build_loop_navigator_data(self.root)
        artifact_data = build_artifact_viewer_data(self.root, loop_nav_data.current_phase)
        packet_data = build_packet_viewer_data(self.root)
        diagnostics = self._event_reader.poll()
        self._loop_nav_widget.border_title = "Loop"
        self._events_widget.border_title = "Diagnostics"
        artifact_phase = artifact_data.phase or "(none)"
        self._artifact_widget.border_title = f"Artefacts ({artifact_phase})"
        self._packet_widget.border_title = (
            f"Packet ({packet_data.packet_id})" if packet_data.packet_id else "Packet"
        )
        self._loop_nav_widget.update(_format_loop_navigator(loop_nav_data))
        self._events_widget.update(_format_diagnostics_panel(diagnostics))
        self._artifact_widget.update(_format_artifact_viewer(artifact_data))
        self._packet_widget.update(_format_packet_viewer(packet_data))
        self._status_bar_widget.update(_format_status_bar(data))
        self._footer_widget.update(_format_footer_line(data))


class MythicTuiApp(App):
    TITLE = "Mythic Vibe TUI"
    SUB_TITLE = "Project status"

    def __init__(self, root: Path, *, theme: str | None = None) -> None:
        super().__init__()
        self.root = root
        self._initial_theme = theme
        # Phase 19.0 / L-8 (additive 2026-05-02 audit remediation):
        # detect narrow-terminal mode at construction so downstream
        # screens / panels can adapt their rendering. The detection
        # honours the MYTHIC_TUI_NARROW env override, an explicit
        # ``columns`` arg (not exposed here — tests can patch
        # ``should_use_narrow_layout`` directly), and the live
        # ``shutil.get_terminal_size`` probe. Pre-Phase-19 the
        # ``surfaces/narrow_layout.should_use_narrow_layout`` helper
        # was exported in __all__ and tested but never imported by
        # production — the audit (L-8) caught it as a dead
        # integration point.
        from ..surfaces.narrow_layout import should_use_narrow_layout

        self.narrow_mode: bool = should_use_narrow_layout()

    def on_mount(self) -> None:
        if self._initial_theme is not None:
            # Defer to Textual's setter, which will raise on unknown
            # names. ``cmd_tui`` already validates via argparse choices,
            # so this should not normally fire — guarded so a direct
            # in-process caller (tests, embeddings) can't crash the app.
            try:
                self.theme = self._initial_theme
            except Exception:  # noqa: BLE001 — never crash the TUI on a bad theme name
                self._initial_theme = None
        # Phase 19.0 / L-8 (additive): annotate the sub-title when
        # narrow mode is active so operators can confirm at a
        # glance which layout the TUI is rendering for.
        if self.narrow_mode:
            self.sub_title = f"{self.SUB_TITLE}  ·  narrow"
        self.push_screen(StatusScreen(self.root))

    def action_cycle_theme(self) -> None:
        """Advance to the next entry in :data:`THEME_CYCLE`. Bound to ``t``
        on every screen via ``Binding("t", "app.cycle_theme", ...)``."""
        from .themes import next_theme

        try:
            self.theme = next_theme(self.theme)
        except Exception:  # noqa: BLE001 — never crash the TUI on a theme bug
            return


def run_tui(root: Path, *, theme: str | None = None) -> int:
    """Entry point invoked by ``cmd_tui`` — opens the app and blocks until quit."""
    MythicTuiApp(root, theme=theme).run()
    return 0
