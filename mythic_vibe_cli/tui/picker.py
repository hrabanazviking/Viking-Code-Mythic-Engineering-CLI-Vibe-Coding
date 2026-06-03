"""Slash-commands picker screen + command preview screen.

Pressing ``/`` from the main TUI status screen opens a picker that shows
the slash-command catalog (built-in plus plugin-contributed entries via
``PluginHookDispatcher.discover_slash_commands()``). Typing filters the
list by substring; pressing Enter pushes a preview screen showing the
selected command's description and source provenance.

This slice does *not* dispatch the selected command — that is slice 3.

Cross-platform: Textual is pure Python (MIT). No platform branches.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from ..plugins.dispatcher import PluginHookDispatcher
from ..runtime.command_catalog import iter_builtin_slash_commands
from ..runtime.slash_commands import (
    BuiltinSlashCommand,
    SlashCommandInfo,
)


@dataclass(frozen=True)
class PickerEntry:
    """Catalog entry the picker displays. Source is one of:
    ``"builtin"`` | ``"extension"`` | ``"prompt"`` | ``"skill"`` | ``"plugin"``.

    PH-02 slice 2.6: ``argv`` is the dispatch payload for non-builtin
    entries (a contributed slash command can supply the exact argv
    list to subprocess-launch). Empty for builtins (the dispatcher
    constructs ``[python, -m, mythic_vibe_cli, <name>]`` from the
    name) and for contributed entries that haven't opted into
    runnability.

    Phase C 2026-05-02 (audit remediation): ``runnable`` indicates the
    contributing plugin opted into the in-process ``run_slash`` protocol
    (see :class:`SlashRunResult` in plugins/api.py). When ``runnable``
    is True the picker dispatches via the plugin dispatcher instead of
    a subprocess; ``argv`` is independent — a plugin may opt into either
    or both paths.
    """

    name: str
    description: str
    source: str
    source_info_path: str = ""
    argv: tuple[str, ...] = ()
    runnable: bool = False

    @classmethod
    def from_builtin(cls, item: BuiltinSlashCommand) -> "PickerEntry":
        return cls(name=item.name, description=item.description, source="builtin")

    @classmethod
    def from_contributed(cls, item: SlashCommandInfo) -> "PickerEntry":
        return cls(
            name=item.name,
            description=item.description,
            source=item.source,
            source_info_path=item.source_info.path if item.source_info else "",
            argv=item.argv,
            runnable=getattr(item, "runnable", False),
        )

    @property
    def is_dispatchable(self) -> bool:
        """Whether the picker has enough information to dispatch this
        entry. Builtins are always dispatchable (argv is reconstructed
        from the name). Contributed entries are dispatchable when
        they supplied an explicit argv at registration time **or**
        opted into the in-process run_slash protocol via
        ``runnable=True`` (Phase C 2026-05-02)."""
        return self.source == "builtin" or bool(self.argv) or self.runnable

    @property
    def dispatch_mode(self) -> str:
        """How the picker will dispatch this entry: ``"builtin"`` →
        runtime.command_for_builtin, ``"argv"`` → subprocess from the
        contributed argv list, ``"run_slash"`` → in-process plugin
        dispatcher (Phase C 2026-05-02), or ``"none"`` when the entry
        is not dispatchable."""
        if self.source == "builtin":
            return "builtin"
        if self.argv:
            return "argv"
        if self.runnable:
            return "run_slash"
        return "none"

    def render_label(self) -> str:
        tag = f"[dim]\\[{self.source}][/dim]"
        desc = self.description or "(no description)"
        return f"/{self.name}  {tag}  {desc}"


def gather_picker_entries(root: Path) -> list[PickerEntry]:
    """Aggregate built-in and plugin-contributed slash commands for the picker.

    Plugin contributions go through the same ``discover_slash_commands()``
    machinery used by ``mythic-vibe slash list`` so the picker and the CLI
    surface stay consistent. Plugins that fail to import or whose
    ``slash_commands()`` raises are skipped silently per dispatcher contract.
    """
    entries: list[PickerEntry] = [
        PickerEntry.from_builtin(item) for item in iter_builtin_slash_commands()
    ]
    try:
        with PluginHookDispatcher(root) as dispatcher:
            dispatcher.load_and_subscribe()
            for item in dispatcher.discover_slash_commands():
                entries.append(PickerEntry.from_contributed(item))
    except Exception:  # noqa: BLE001 - picker should never crash on a bad plugin
        pass
    return entries


def filter_entries(entries: list[PickerEntry], query: str) -> list[PickerEntry]:
    """Filter the catalog to entries whose name OR description contains the
    (case-insensitive) substring."""
    if not query:
        return list(entries)
    needle = query.strip().lower()
    if not needle:
        return list(entries)
    return [
        entry
        for entry in entries
        if needle in entry.name.lower() or needle in entry.description.lower()
    ]


class CommandPreviewScreen(Screen):
    """Read-only preview of a single picker entry. Builtins can be dispatched
    via the ``r`` / Enter binding, which pushes a ``RunningCommandScreen``.
    Non-builtin (plugin / extension / skill / prompt) entries display a notice
    that this slice does not yet dispatch them."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back", show=False),
        Binding("r", "run_command", "Run"),
        Binding("enter", "run_command", "Run", show=False),
        Binding("question_mark", "show_help", "Help"),
        Binding("t", "app.cycle_theme", "Theme"),
    ]

    DEFAULT_CSS = """
    CommandPreviewScreen {
        layout: vertical;
        align: center middle;
    }

    #preview-card {
        width: 80%;
        max-width: 100;
        border: round $secondary;
        padding: 1 2;
    }
    """

    def __init__(self, entry: PickerEntry, *, project_root: Path | None = None) -> None:
        super().__init__()
        self.entry = entry
        self.project_root = project_root

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        body = Static(id="preview-card")
        body.border_title = f"/{self.entry.name}"
        body.update(self._format_body())
        yield body
        yield Footer()

    def _format_body(self) -> str:
        description = self.entry.description or "(no description)"
        path = self.entry.source_info_path or "(builtin)"
        mode = self.entry.dispatch_mode
        if mode == "run_slash":
            # Phase C 2026-05-02: plugin opted into in-process run_slash
            # protocol — distinct from the argv subprocess path.
            run_hint = (
                "[b]Press r[/b] to run this plugin slash command "
                "(in-process)."
            )
        elif self.entry.is_dispatchable:
            run_hint = "[b]Press r[/b] to run this command."
        else:
            # Final fallback for plugin-contributed entries that
            # supplied neither argv nor the runnable=True opt-in.
            # Preserved verbatim per additive-only rule (Phase C).
            run_hint = (
                "[dim](plugin dispatch not yet implemented; "
                "press Esc to return.)[/dim]"
            )
        return (
            f"[b]Source:[/b]      {self.entry.source}\n"
            f"[b]Source info:[/b] {path}\n\n"
            f"[b]Description[/b]\n{description}\n\n"
            f"{run_hint}\n[dim]Press Esc to return.[/dim]"
        )

    def action_run_command(self) -> None:
        if not self.entry.is_dispatchable:
            return

        cwd = self.project_root if self.project_root is not None else Path.cwd()
        mode = self.entry.dispatch_mode

        # Phase C 2026-05-02: in-process plugin run_slash dispatch path.
        # The argv-based subprocess path below is preserved unchanged
        # for plugins that opted into argv-style dispatch in slice 2.6.
        if mode == "run_slash":
            self.app.push_screen(
                PluginSlashRunScreen(self.entry, project_root=cwd)
            )
            return

        from .runner import RunningCommandScreen, RunSpec, command_for_builtin

        if self.entry.source == "builtin":
            spec = command_for_builtin(self.entry.name, project_root=cwd)
        else:
            # Slice 2.6: contributed slash with an explicit argv list.
            # The plugin owns the invocation shape — no --path injection,
            # no Python-interpreter wrapping; the argv is taken as-is.
            spec = RunSpec(label=f"/{self.entry.name}", argv=list(self.entry.argv))
        self.app.push_screen(RunningCommandScreen(spec, cwd=cwd))

    def action_show_help(self) -> None:
        from .help_overlay import HelpOverlayScreen, binding_help_pairs

        self.app.push_screen(
            HelpOverlayScreen(
                "Command preview — keys", binding_help_pairs(self.BINDINGS)
            )
        )


# Additive 2026-05-02 (Phase C of audit remediation): screen that
# drives in-process plugin slash dispatch and displays the result.
# Mirrors the shape of CommandPreviewScreen but runs the plugin's
# ``run_slash`` via :meth:`PluginHookDispatcher.dispatch_slash`
# instead of pushing a subprocess RunningCommandScreen. Plugin
# misbehaviour (raise / non-SlashRunResult / no handler) all
# surface here as a clean error/fallback message rather than a
# crashed TUI.
class PluginSlashRunScreen(Screen):
    """In-process dispatch screen for plugin-contributed slash
    commands that opted into the ``run_slash`` protocol via
    ``SlashCommandInfo(runnable=True)``."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back", show=False),
        Binding("question_mark", "show_help", "Help"),
        Binding("t", "app.cycle_theme", "Theme"),
    ]

    DEFAULT_CSS = """
    PluginSlashRunScreen {
        layout: vertical;
        align: center middle;
    }

    #plugin-slash-card {
        width: 90%;
        max-width: 120;
        border: round $secondary;
        padding: 1 2;
    }
    """

    def __init__(
        self, entry: PickerEntry, *, project_root: Path | None = None
    ) -> None:
        super().__init__()
        self.entry = entry
        self.project_root = project_root or Path.cwd()
        self._result_text: str = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        body = Static(id="plugin-slash-card")
        body.border_title = f"/{self.entry.name}  (plugin run_slash)"
        body.update(self._initial_text())
        yield body
        yield Footer()

    def on_mount(self) -> None:
        # Run the dispatch on mount so the user sees a quick render
        # before the plugin code executes. Anything that raises or
        # mis-types is contained inside dispatch_slash via safe_call.
        result = self._dispatch()
        self._render_result(result)

    def _initial_text(self) -> str:
        return (
            f"[b]Plugin:[/b]   {self.entry.source_info_path or '(unknown)'}\n"
            f"[b]Source:[/b]   {self.entry.source}\n\n"
            "Dispatching…"
        )

    def _dispatch(self) -> object:
        """Invoke the plugin dispatcher's ``dispatch_slash`` and
        return either a SlashRunResult, None, or an Exception (for
        the very-rare case the dispatcher itself raises before its
        own contained except path)."""
        # Late-import to keep the module light when the TUI surface
        # never displays a runnable plugin entry.
        from ..plugins.dispatcher import PluginHookDispatcher

        try:
            with PluginHookDispatcher(self.project_root) as dispatcher:
                dispatcher.load_and_subscribe()
                return dispatcher.dispatch_slash(self.entry.name, ())
        except Exception as exc:  # noqa: BLE001 - never crash the TUI on plugin error
            return exc

    def _render_result(self, result: object) -> None:
        body = self.query_one("#plugin-slash-card", Static)
        if isinstance(result, Exception):
            body.update(
                f"[b]Plugin:[/b]   {self.entry.source_info_path or '(unknown)'}\n"
                f"[b]Source:[/b]   {self.entry.source}\n\n"
                f"[b red]Error:[/b red] dispatcher raised: {result}\n\n"
                "[dim]Press Esc to return.[/dim]"
            )
            return
        if result is None:
            # No plugin handled the slash (no run_slash, or all returned
            # handled=False). Surface the same fallback message the
            # preview screen shows for not-yet-runnable entries.
            body.update(
                f"[b]Plugin:[/b]   {self.entry.source_info_path or '(unknown)'}\n"
                f"[b]Source:[/b]   {self.entry.source}\n\n"
                "[dim](plugin dispatch returned no handler — "
                "no plugin claimed this slash with handled=True.)[/dim]\n\n"
                "[dim]Press Esc to return.[/dim]"
            )
            return
        # Real SlashRunResult.
        # Late-import for symmetry with _dispatch + to keep the
        # module light at import time.
        from ..plugins.api import SlashRunResult  # noqa: F401  - type narrowing only
        exit_code = getattr(result, "exit_code", 0)
        output = getattr(result, "output", "") or ""
        error = getattr(result, "error", "") or ""
        status_color = "green" if exit_code == 0 and not error else "yellow"
        status_label = "ok" if exit_code == 0 and not error else "warning"
        text = (
            f"[b]Plugin:[/b]    {self.entry.source_info_path or '(unknown)'}\n"
            f"[b]Source:[/b]    {self.entry.source}\n"
            f"[b]Exit code:[/b] {exit_code}  "
            f"[{status_color}]({status_label})[/{status_color}]\n\n"
        )
        if output:
            text += f"[b]Output[/b]\n{output}\n\n"
        if error:
            text += f"[b red]Error[/b red]\n{error}\n\n"
        if not output and not error:
            text += "[dim](plugin returned no output)[/dim]\n\n"
        text += "[dim]Press Esc to return.[/dim]"
        body.update(text)

    def action_show_help(self) -> None:
        from .help_overlay import HelpOverlayScreen, binding_help_pairs

        self.app.push_screen(
            HelpOverlayScreen(
                "Plugin slash run — keys", binding_help_pairs(self.BINDINGS)
            )
        )


class SlashPickerScreen(Screen):
    """Filterable list of slash commands. Pushes ``CommandPreviewScreen`` on
    selection. Esc cancels back to the prior screen."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Cancel"),
        Binding("question_mark", "show_help", "Help"),
        Binding("t", "app.cycle_theme", "Theme"),
    ]

    DEFAULT_CSS = """
    SlashPickerScreen {
        layout: vertical;
    }

    #picker-body {
        padding: 1 1;
        height: 1fr;
    }

    Input {
        margin: 0 0 1 0;
    }

    OptionList {
        height: 1fr;
        border: round $secondary;
    }
    """

    def __init__(self, root: Path, entries: list[PickerEntry] | None = None) -> None:
        super().__init__()
        self.root = root
        self._entries: list[PickerEntry] = (
            list(entries) if entries is not None else gather_picker_entries(root)
        )
        self._option_list = OptionList(id="picker-list")
        self._search_input = Input(placeholder="filter (substring)…", id="picker-search")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="picker-body"):
            yield self._search_input
            yield self._option_list
        yield Footer()

    def on_mount(self) -> None:
        self._option_list.border_title = "Slash commands"
        self._render_options(self._entries)
        self._search_input.focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input is not self._search_input:
            return
        filtered = filter_entries(self._entries, event.value)
        self._render_options(filtered)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input is not self._search_input:
            return
        filtered = filter_entries(self._entries, event.value)
        if filtered:
            self._select_entry(filtered[0])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        index = event.option_index
        filtered = filter_entries(self._entries, self._search_input.value)
        if 0 <= index < len(filtered):
            self._select_entry(filtered[index])

    def _render_options(self, entries: list[PickerEntry]) -> None:
        self._option_list.clear_options()
        if not entries:
            self._option_list.add_option(Option("(no matches)", id="__none__", disabled=True))
            return
        for entry in entries:
            self._option_list.add_option(Option(entry.render_label(), id=f"slash:{entry.name}"))

    def _select_entry(self, entry: PickerEntry) -> None:
        self.app.push_screen(CommandPreviewScreen(entry, project_root=self.root))

    def action_show_help(self) -> None:
        from .help_overlay import HelpOverlayScreen, binding_help_pairs

        self.app.push_screen(
            HelpOverlayScreen(
                "Slash picker — keys", binding_help_pairs(self.BINDINGS)
            )
        )
