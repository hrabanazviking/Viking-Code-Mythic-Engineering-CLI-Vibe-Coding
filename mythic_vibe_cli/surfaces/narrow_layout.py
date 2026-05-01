"""Mobile-friendly narrow-layout helper (PH-17 Slice 17.2).

Detects when the active terminal is too narrow for the default
multi-pane TUI layout and reports whether a single-column
fallback should activate. The TUI consumes this via
:func:`should_use_narrow_layout`; tests drive it with explicit
``columns`` overrides.

The threshold (78 columns) is tuned for 80-wide mobile SSH
clients leaving room for a 2-col gutter.

Cross-platform: pure stdlib (``shutil.get_terminal_size``).
"""

from __future__ import annotations

import os
import shutil


# Threshold below which the TUI collapses to a single column.
# 78 leaves a 2-col gutter on an 80-wide terminal — the most
# common mobile SSH client width.
NARROW_LAYOUT_THRESHOLD = 78

# Override env var; operators can force narrow layout for
# testing on a wide terminal.
FORCE_NARROW_ENV = "MYTHIC_TUI_NARROW"


def detect_columns(*, fallback: int = 80) -> int:
    """Best-effort terminal width detection. Falls back to
    ``fallback`` when the OS reports an unusable size."""
    try:
        size = shutil.get_terminal_size(fallback=(fallback, 24))
    except OSError:
        return fallback
    columns = int(size.columns or fallback)
    return columns if columns > 0 else fallback


def is_force_narrow_env() -> bool:
    """Read :data:`FORCE_NARROW_ENV`. Truthy values force the
    narrow layout regardless of terminal width — used by tests
    + operators on wide screens who want the mobile rendering."""
    raw = os.environ.get(FORCE_NARROW_ENV, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def should_use_narrow_layout(
    *,
    columns: int | None = None,
    threshold: int = NARROW_LAYOUT_THRESHOLD,
) -> bool:
    """Return True when the TUI should render its single-column
    layout. ``columns`` overrides the live terminal probe (tests
    pass an explicit value).

    Resolution order:
    1. ``MYTHIC_TUI_NARROW=1`` env override → True.
    2. Explicit ``columns`` arg → compare to ``threshold``.
    3. Live ``shutil.get_terminal_size`` probe → compare.
    """
    if is_force_narrow_env():
        return True
    width = columns if columns is not None else detect_columns()
    return width < threshold


__all__ = [
    "FORCE_NARROW_ENV",
    "NARROW_LAYOUT_THRESHOLD",
    "detect_columns",
    "is_force_narrow_env",
    "should_use_narrow_layout",
]
