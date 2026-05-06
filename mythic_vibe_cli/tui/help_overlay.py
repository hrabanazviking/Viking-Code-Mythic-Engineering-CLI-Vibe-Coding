"""Shared help-overlay screen and binding-extraction helpers.

PH-04 slice 4.7. Every TUI screen exposes a ``?`` key that pushes a
``HelpOverlayScreen`` listing that screen's bindings — replacing the
slice-4.5-era inline help text on ``DiffReviewScreen`` with a uniform
overlay so the operator's "how do I drive this thing" reflex is one
key, every screen, no exceptions.

The module is intentionally Textual-only (no parser-style data layer)
because it has no consumer outside the TUI. Tests import ``Binding``
directly to construct fixtures.

Cross-platform: Textual is pure Python; no platform branches.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


def binding_help_pairs(bindings: list[Binding]) -> list[tuple[str, str]]:
    """Extract visible ``(key, description)`` pairs from a screen's
    ``BINDINGS`` list.

    Bindings with ``show=False`` (typically aliases like ``ctrl+c``
    duplicating ``q`` Quit) are dropped — they'd just clutter the
    help table. The screen's canonical key is what the operator
    needs to learn.
    """
    pairs: list[tuple[str, str]] = []
    for binding in bindings:
        if not getattr(binding, "show", True):
            continue
        pairs.append((binding.key, binding.description or ""))
    return pairs


def format_help_table(title: str, pairs: list[tuple[str, str]]) -> str:
    """Render a Rich-tagged help table.

    The empty-pairs case still renders the title plus a placeholder so
    the overlay has something visible (any screen reaching this state
    has a bug — but the overlay shouldn't crash on it).
    """
    if not pairs:
        return f"[b]{title}[/b]\n\n[dim](no bindings registered)[/dim]"
    width = max(len(key) for key, _ in pairs)
    lines = [f"[b]{title}[/b]", ""]
    for key, desc in pairs:
        lines.append(f"  [cyan]{key.ljust(width)}[/cyan]  {desc}")
    return "\n".join(lines)


class HelpOverlayScreen(Screen):
    """Centred read-only overlay listing a screen's bindings.

    Stateless — the caller passes title text and `(key, description)`
    pairs; the overlay just renders. Press ``escape``, ``q``, or ``?``
    to dismiss back to the screen that pushed it.
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Close"),
        Binding("q", "app.pop_screen", "Close", show=False),
        Binding("question_mark", "app.pop_screen", "Close", show=False),
        Binding("t", "app.cycle_theme", "Theme"),
    ]

    DEFAULT_CSS = """
    HelpOverlayScreen {
        layout: vertical;
        align: center middle;
    }

    #help-overlay-card {
        width: 70%;
        max-width: 80;
        border: round $secondary;
        padding: 1 2;
    }
    """

    def __init__(self, title: str, pairs: list[tuple[str, str]]) -> None:
        super().__init__()
        self.title_text = title
        self.pairs = list(pairs)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        body = Static(id="help-overlay-card")
        body.border_title = "Help"
        body.update(format_help_table(self.title_text, self.pairs))
        yield body
        yield Footer()


__all__ = [
    "HelpOverlayScreen",
    "binding_help_pairs",
    "format_help_table",
]
