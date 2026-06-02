"""Canonical interactive companion shell entrypoint.

The historical REPL implementation lives in :mod:`mythic_vibe_cli.repl`.
This module gives the reforge roadmap a stable, product-named import
surface while preserving the older ``repl`` module for compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import IO, Callable

from .repl import BANNER, PROMPT, run_shell


def run_interactive_shell(
    *,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
    stderr: IO[str] | None = None,
    main: Callable[[list[str]], int] | None = None,
    project_root: Path | None = None,
) -> int:
    """Run the interactive companion shell."""
    return run_shell(
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        main=main,
        project_root=project_root,
    )


__all__ = ["BANNER", "PROMPT", "run_interactive_shell", "run_shell"]
