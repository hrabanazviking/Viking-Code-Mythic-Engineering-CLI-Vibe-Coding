"""Drift dashboard screen — PH-13 slice 13.4.

Wraps :func:`mythic_vibe_cli.drift.scan_for_drift` in a Textual
screen so the operator can watch drift findings live alongside the
status panels. Refreshed on a longer interval than the main TUI
(drift detectors walk the project tree) but otherwise identical
discipline:

- Uses the slice 4.7 ``HelpOverlayScreen`` for ``?``.
- Uses the slice 4.8 ``app.cycle_theme`` for ``t``.
- ``escape`` / ``q`` pop back to the caller.
- ``r`` triggers an immediate refresh.

Cross-platform: pure Python; no platform branches.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from ..drift import DriftFinding, scan_for_drift, summarize_findings


DRIFT_REFRESH_INTERVAL_SECONDS = 5.0


def _format_drift_panel(findings: list[DriftFinding]) -> str:
    """Render a Rich-tagged summary + per-finding list.

    Severity colour mapping mirrors slice 4.6's diagnostics-channel
    palette: ``error`` red, ``warning`` yellow, ``info`` cyan. The
    pulse-style summary at the top reads in monochrome too — the
    severity word is always present alongside the colour tag.
    """
    summary = summarize_findings(findings)
    pulse = (
        f"[red]{summary['error']} error[/red]  ·  "
        f"[yellow]{summary['warning']} warning[/yellow]  ·  "
        f"[cyan]{summary['info']} info[/cyan]"
    )
    if not findings:
        return f"{pulse}\n\n[dim]No drift detected.[/dim]"

    lines = [pulse, "", f"[b]{len(findings)} finding(s):[/b]"]
    for finding in findings:
        if finding.severity == "error":
            tag = "red"
        elif finding.severity == "warning":
            tag = "yellow"
        elif finding.severity == "info":
            tag = "cyan"
        else:
            tag = "b"
        lines.append(
            f"  [{tag}]{finding.severity}[/{tag}] "
            f"[b]{finding.category}[/b] {finding.path}"
        )
        lines.append(f"      [dim]{finding.description}[/dim]")
    return "\n".join(lines)


class DriftScreen(Screen):
    """Live drift dashboard.

    Caller passes the project root; the screen polls
    :func:`scan_for_drift` every :data:`DRIFT_REFRESH_INTERVAL_SECONDS`.
    Pressing ``r`` forces an immediate refresh; ``escape`` / ``q``
    pop back to the caller.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back", show=False),
        Binding("r", "refresh_now", "Refresh"),
        Binding("question_mark", "show_help", "Help"),
        Binding("t", "app.cycle_theme", "Theme"),
    ]

    DEFAULT_CSS = """
    DriftScreen {
        layout: vertical;
    }

    #drift-body {
        padding: 1 1;
        height: 1fr;
    }

    #drift-card {
        border: round $secondary;
        padding: 1 2;
        height: 1fr;
    }
    """

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self._card: Any = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        self._card = Static(id="drift-card")
        self._card.border_title = "Drift dashboard"
        with Vertical(id="drift-body"):
            yield self._card
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.set_interval(DRIFT_REFRESH_INTERVAL_SECONDS, self._refresh)

    def action_refresh_now(self) -> None:
        self._refresh()

    def action_show_help(self) -> None:
        from .help_overlay import HelpOverlayScreen, binding_help_pairs

        self.app.push_screen(
            HelpOverlayScreen("Drift — keys", binding_help_pairs(self.BINDINGS))
        )

    def _refresh(self) -> None:
        if self._card is None:
            return
        findings = scan_for_drift(self.root)
        self._card.update(_format_drift_panel(findings))


__all__ = [
    "DRIFT_REFRESH_INTERVAL_SECONDS",
    "DriftScreen",
    "_format_drift_panel",
]
