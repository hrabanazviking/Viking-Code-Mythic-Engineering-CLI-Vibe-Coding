"""Chaquopy-side runner for the mythic-vibe Android wrapper (PH-22.2).

The Kotlin activity calls into this module via Chaquopy's Python
interop. The runner captures the CLI's stdout + stderr into a
string buffer so the activity can drop the result into a Compose
Text composable.

Foundation-level: synchronous runs only — we wait for the CLI
to return, then emit the full captured output. A future session
splits this into a line-streaming generator that the Kotlin
side can poll for incremental updates.
"""

from __future__ import annotations

import contextlib
import io
import sys
from typing import Iterable


def run_cli(argv: Iterable[str]) -> str:
    """Run mythic_vibe_cli with the given argv and return the
    captured stdout + stderr as a single string.

    Errors during the run are caught and returned in the output
    text rather than raised — the Kotlin caller already has a
    try/catch around the JNI boundary, but a controlled string
    return is friendlier to the UI.
    """
    # Lazy import so the module's top-level isn't punished for
    # full CLI initialization on import. Chaquopy's first
    # `getModule` call would otherwise feel sluggish.
    from mythic_vibe_cli.cli import main as cli_main

    argv_list = [str(arg) for arg in argv]

    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    exit_code: int | None = None
    error_text = ""

    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            exit_code = cli_main(argv_list)
    except SystemExit as exc:
        # The CLI's exit() calls land here on argparse errors;
        # surface them as the exit code and continue.
        exit_code = exc.code if isinstance(exc.code, int) else 2
    except Exception as exc:  # noqa: BLE001 — surface any error to the UI
        error_text = f"\nUnhandled exception: {exc!r}\n"

    out = stdout_buf.getvalue()
    err = stderr_buf.getvalue()

    parts: list[str] = []
    if out:
        parts.append(out.rstrip())
    if err:
        parts.append(f"\n--- stderr ---\n{err.rstrip()}")
    if error_text:
        parts.append(error_text)
    parts.append(f"\n[exit code: {exit_code}]")

    return "\n".join(parts)


__all__ = ["run_cli"]


if __name__ == "__main__":
    # Manual smoke for testing the runner from a desktop Python:
    #   python -m packaging.android.app.src.main.python.mythic_vibe_cli_android_runner --version
    print(run_cli(sys.argv[1:]))
