"""Textual TUI for Mythic Vibe CLI.

Optional dependency on ``textual``. Import the public surface lazily so the
rest of the CLI does not pay the import cost or fail when textual is not
installed.
"""

from .app import build_status_data

__all__ = ["build_status_data"]


def __getattr__(name: str):
    """Lazy-import picker symbols so ``test_tui.py``'s missing-textual fallback
    path keeps working — the picker module imports textual at top level."""
    if name in {"CommandPreviewScreen", "PickerEntry", "SlashPickerScreen", "filter_entries", "gather_picker_entries"}:
        from . import picker

        return getattr(picker, name)
    raise AttributeError(name)
