"""Mythic Vibe CLI — thin module-level entry point.

This file owns nothing but the public re-exports. It is the stable
target of ``python -m mythic_vibe_cli.cli`` and external imports such
as ``from mythic_vibe_cli.cli import main``. All argparse construction,
runtime-flag handling, command dispatch, and timing instrumentation
live in :mod:`mythic_vibe_cli.app`. Keep this file under ten lines so
it never accumulates logic and never needs to be touched in normal
feature work.

If you need to add a new command, edit ``app.py`` (parser) and
``commands.py`` (handler). If you need to extend runtime flags or
output policy, edit ``app.py``. If you only need to expose a new
public symbol to importers of ``mythic_vibe_cli.cli``, add it to
``__all__`` here.
"""

from __future__ import annotations

from .app import COMMAND_HANDLERS, build_parser, main

__all__ = ["COMMAND_HANDLERS", "build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
