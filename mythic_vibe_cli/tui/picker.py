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

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from ..plugins.dispatcher import PluginHookDispatcher
from ..runtime.slash_commands import (
    BUILTIN_SLASH_COMMANDS,
    BuiltinSlashCommand,
    SlashCommandInfo,
)


@dataclass(frozen=True)
class PickerEntry:
    """Catalog entry the picker displays. Source is one of:
    ``"builtin"`` | ``"extension"`` | ``"prompt"`` | ``"skill"`` | ``"plugin"``.
    """

    name: str
    description: str
    source: str
    source_info_path: str = ""

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
        )

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
        PickerEntry.from_builtin(item) for item in BUILTIN_SLASH_COMMANDS
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
    """Read-only preview of a single picker entry."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back", show=False),
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

    def __init__(self, entry: PickerEntry) -> None:
        super().__init__()
        self.entry = entry

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
        return (
            f"[b]Source:[/b]      {self.entry.source}\n"
            f"[b]Source info:[/b] {path}\n\n"
            f"[b]Description[/b]\n{description}\n\n"
            f"[dim]Press Esc to return.[/dim]"
        )


class SlashPickerScreen(Screen):
    """Filterable list of slash commands. Pushes ``CommandPreviewScreen`` on
    selection. Esc cancels back to the prior screen."""

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Cancel"),
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
        self.app.push_screen(CommandPreviewScreen(entry))
