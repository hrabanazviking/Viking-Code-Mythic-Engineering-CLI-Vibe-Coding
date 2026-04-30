"""Running-command screen with live elapsed time.

Spawns the requested command via ``subprocess.Popen`` (cross-platform stdlib
— no Unix-only signal handlers, no platform branches) and refreshes a panel
every 0.2 seconds with elapsed time and the latest output tail. When the
process exits, the screen renders the final exit code plus a longer tail
and waits for the user to press Esc.

Plugin-contributed slash commands are intentionally **not dispatched** in
this slice — that contract belongs to a follow-on. The preview screen sends
only built-in entries to the runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import time

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


@dataclass(frozen=True)
class RunSpec:
    """Concrete subprocess invocation for a builtin slash command."""

    label: str
    argv: list[str]


def command_for_builtin(name: str, *, project_root: Path | None = None) -> RunSpec:
    """Return the subprocess argv that runs ``mythic-vibe <name>`` via the
    current Python interpreter. Using ``sys.executable -m mythic_vibe_cli``
    avoids PATH / venv resolution issues on every platform.
    """
    base = [sys.executable, "-m", "mythic_vibe_cli", name]
    if project_root is not None and name in {
        "status",
        "scan",
        "verify",
        "reflect",
        "resume",
        "method",
        "handoff",
        "workflow",
        "plugin",
        "grimoire",
        "provider",
        "audit",
        "drift",
        "graph",
        "memory",
        "hardware",
    }:
        base.extend(["--path", str(project_root)])
    return RunSpec(label=f"/{name}", argv=base)


class RunningCommandScreen(Screen):
    """Run a subprocess and show live elapsed time, then exit code + tail."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back", show=False),
        Binding("question_mark", "show_help", "Help"),
        Binding("t", "app.cycle_theme", "Theme"),
    ]

    DEFAULT_CSS = """
    RunningCommandScreen {
        layout: vertical;
        padding: 1 2;
    }

    #runner-card {
        border: round $secondary;
        padding: 1 2;
        height: 1fr;
    }
    """

    POLL_INTERVAL_SECONDS = 0.2
    OUTPUT_TAIL_BYTES = 4096

    def __init__(self, spec: RunSpec, *, cwd: Path) -> None:
        super().__init__()
        self.spec = spec
        self.cwd = cwd
        self._proc: subprocess.Popen[str] | None = None
        self._started_at = 0.0
        self._exit_code: int | None = None
        self._captured_stdout = ""
        self._captured_stderr = ""
        self._card = Static(id="runner-card")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        self._card.border_title = "Running command"
        yield self._card
        yield Footer()

    def on_mount(self) -> None:
        self._launch()
        self._refresh_card()
        self.set_interval(self.POLL_INTERVAL_SECONDS, self._tick)

    def on_unmount(self) -> None:
        """Ensure the spawned subprocess is reaped when the screen tears down.

        Without this, on Windows the subprocess may still hold ``cwd`` as a
        live handle, blocking cleanup of any temp dir the caller used. We
        terminate gracefully, fall back to kill, and swallow OSError so a
        dead process never raises during teardown.
        """
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
        except OSError:
            # See on_unmount docstring: a dead/already-reaped process must not raise during teardown.
            pass

    def _launch(self) -> None:
        try:
            self._proc = subprocess.Popen(
                self.spec.argv,
                cwd=str(self.cwd),
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
            )
            self._started_at = time.perf_counter()
        except FileNotFoundError as exc:
            self._exit_code = 127
            self._captured_stderr = str(exc)

    def _tick(self) -> None:
        if self._proc is None:
            self._refresh_card()
            return
        if self._exit_code is not None:
            self._refresh_card()
            return
        if self._proc.poll() is None:
            self._refresh_card()
            return
        # Process has exited — drain stdout/stderr.
        try:
            stdout, stderr = self._proc.communicate(timeout=1.0)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            stdout, stderr = self._proc.communicate()
        self._captured_stdout = stdout or ""
        self._captured_stderr = stderr or ""
        self._exit_code = self._proc.returncode if self._proc.returncode is not None else 0
        self._refresh_card()

    def _refresh_card(self) -> None:
        elapsed = time.perf_counter() - self._started_at if self._started_at else 0.0
        body_lines: list[str] = [
            f"[b]Command:[/b] {self.spec.label}",
            f"[b]Argv:[/b]    {' '.join(self.spec.argv)}",
            f"[b]Cwd:[/b]     {self.cwd}",
            f"[b]Elapsed:[/b] {elapsed:.1f}s",
            "",
        ]
        if self._exit_code is None:
            body_lines.append("[dim]Running…[/dim]")
        else:
            body_lines.append(f"[b]Exit code:[/b] {self._exit_code}")
            tail = self._tail(self._captured_stdout, label="stdout")
            err_tail = self._tail(self._captured_stderr, label="stderr")
            body_lines.extend(["", tail, "", err_tail])
            body_lines.append("")
            body_lines.append("[dim]Press Esc to return.[/dim]")
        self._card.update("\n".join(body_lines))

    def _tail(self, text: str, *, label: str) -> str:
        if not text:
            return f"[b]{label}:[/b] (empty)"
        snippet = text[-self.OUTPUT_TAIL_BYTES :]
        return f"[b]{label}:[/b]\n{snippet}"

    def action_show_help(self) -> None:
        from .help_overlay import HelpOverlayScreen, binding_help_pairs

        self.app.push_screen(
            HelpOverlayScreen(
                "Running command — keys", binding_help_pairs(self.BINDINGS)
            )
        )
