"""Theme cycle + validation for the Textual TUI.

PH-04 slice 4.8. Textual ships ~20 built-in themes; this module
exposes:

- a small **curated cycle** the ``t`` keybinding rotates through, so
  the operator can sample dark / light / ANSI / Nord / Gruvbox /
  Monokai with single keypresses;
- a **full allowed set** the ``--theme`` CLI flag accepts, so anyone
  with a strong preference (Dracula, Catppuccin, Solarized…) can land
  there directly from the shell.

The validation surface is intentionally a pure-Python list — it does
not import Textual. That lets the argparse-time `choices=` check
work even if Textual is uninstalled (the user gets a clean error
naming valid themes before the import-time TUI fails).

Cross-platform: pure stdlib, no platform branches.
"""

from __future__ import annotations

DEFAULT_THEME = "textual-dark"


# Curated cycle for the `t` keybinding — six common, broadly-readable
# themes. Ordered so consecutive entries feel like a meaningful step
# (dark → light → ANSI palette → Nord → Gruvbox → Monokai) rather
# than alphabetic noise.
THEME_CYCLE: tuple[str, ...] = (
    "textual-dark",
    "textual-light",
    "textual-ansi",
    "nord",
    "gruvbox",
    "monokai",
)


# Full set the `--theme` CLI flag accepts. Mirrors the names returned
# by ``App().available_themes`` on Textual 8.x. If Textual adds new
# themes upstream this list goes stale and the CLI silently won't
# expose them — but the existing names keep working, so the fallout
# of drift is "user has to wait for an update", not a runtime crash.
TEXTUAL_BUILTIN_THEMES: tuple[str, ...] = (
    "textual-dark",
    "textual-light",
    "textual-ansi",
    "nord",
    "gruvbox",
    "catppuccin-mocha",
    "dracula",
    "tokyo-night",
    "monokai",
    "flexoki",
    "catppuccin-latte",
    "catppuccin-frappe",
    "catppuccin-macchiato",
    "solarized-light",
    "solarized-dark",
    "rose-pine",
    "rose-pine-moon",
    "rose-pine-dawn",
    "atom-one-dark",
    "atom-one-light",
)


def next_theme(current: str) -> str:
    """Return the next theme in :data:`THEME_CYCLE`, wrapping at the end.

    If ``current`` is not in the cycle (e.g. the operator launched with
    ``--theme dracula`` which isn't on the curated cycle), advance to
    the first cycle entry — that gives ``t`` a deterministic anchor
    instead of a no-op.
    """
    try:
        idx = THEME_CYCLE.index(current)
    except ValueError:
        return THEME_CYCLE[0]
    return THEME_CYCLE[(idx + 1) % len(THEME_CYCLE)]


def validate_theme(name: str) -> str:
    """Return ``name`` if it is one of :data:`TEXTUAL_BUILTIN_THEMES`,
    otherwise raise :class:`ValueError` listing the valid choices.

    Used by argparse-style consumers that want a clear error message
    rather than the bare ``choices=`` rejection.
    """
    if name in TEXTUAL_BUILTIN_THEMES:
        return name
    raise ValueError(
        f"Unknown theme {name!r}. Valid choices: "
        + ", ".join(TEXTUAL_BUILTIN_THEMES)
    )


__all__ = [
    "DEFAULT_THEME",
    "THEME_CYCLE",
    "TEXTUAL_BUILTIN_THEMES",
    "next_theme",
    "validate_theme",
]
