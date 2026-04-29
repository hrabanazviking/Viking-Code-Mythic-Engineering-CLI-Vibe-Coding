# Portions adapted from badlogic/pi-mono (packages/coding-agent/src/core/output-guard.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md at the repo root.
"""Reroute stdout writes to stderr so that protocol-output modes (``--json``,
RPC, print mode) can keep stdout clean for machine-parseable output.

This is the synchronous Python translation of pi's ``output-guard.ts``. Pi
reassigns ``process.stdout.write``; we install a proxy stream into
``sys.stdout`` that delegates ``write`` and ``flush`` to ``sys.stderr``. The
original ``sys.stdout`` is preserved on a module-level state slot so:

- :func:`restore_stdout` can put it back, and
- :func:`write_raw_stdout` can write to the real stdout even while the guard
  is active (so the protocol-output path remains usable).

The state is module-level — there is exactly one stdout, and the guard is
idempotent. Calling :func:`take_over_stdout` while the guard is already active
is a no-op.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import sys
from typing import IO, Iterator, TextIO


@dataclass
class _GuardState:
    original_stdout: TextIO


_state: _GuardState | None = None


class _StderrProxy:
    """Minimal text-stream proxy that forwards writes to ``sys.stderr``.

    It does not implement the entire ``TextIO`` protocol — only the subset
    that the standard library and most logging code actually call:
    ``write``, ``flush``, ``isatty``, ``writable``, and the file-like
    attributes ``encoding``, ``name``, and ``closed``. ``readable`` and the
    read methods correctly report unsupported.
    """

    @property
    def encoding(self) -> str:
        return getattr(sys.stderr, "encoding", "utf-8") or "utf-8"

    @property
    def name(self) -> str:
        return "<stdout-routed-to-stderr>"

    @property
    def closed(self) -> bool:
        return bool(getattr(sys.stderr, "closed", False))

    def write(self, text: str) -> int:
        return sys.stderr.write(text)

    def flush(self) -> None:
        sys.stderr.flush()

    def isatty(self) -> bool:
        try:
            return bool(sys.stderr.isatty())
        except (AttributeError, ValueError):
            return False

    def writable(self) -> bool:
        return True

    def readable(self) -> bool:
        return False

    def fileno(self) -> int:
        return sys.stderr.fileno()


def take_over_stdout() -> None:
    """Install the guard. Subsequent writes to ``sys.stdout`` route to
    ``sys.stderr``. Idempotent."""
    global _state
    if _state is not None:
        return
    _state = _GuardState(original_stdout=sys.stdout)
    sys.stdout = _StderrProxy()  # type: ignore[assignment]


def restore_stdout() -> None:
    """Restore the original ``sys.stdout``. No-op if the guard is not active."""
    global _state
    if _state is None:
        return
    sys.stdout = _state.original_stdout
    _state = None


def is_stdout_taken_over() -> bool:
    """Return whether the guard is currently active."""
    return _state is not None


def write_raw_stdout(text: str) -> int:
    """Write ``text`` to the real stdout regardless of guard state.

    Returns the number of characters written, mirroring ``TextIO.write``.
    """
    target: IO[str] = _state.original_stdout if _state is not None else sys.stdout
    return target.write(text)


def flush_raw_stdout() -> None:
    """Flush the real stdout regardless of guard state."""
    target: IO[str] = _state.original_stdout if _state is not None else sys.stdout
    target.flush()


@contextmanager
def json_output_guard(active: bool) -> Iterator[None]:
    """Optionally activate the stdout guard for the duration of a ``with`` block.

    Pass ``active=True`` to install the guard before the block runs and restore
    the original stdout after, even on exceptions. ``active=False`` makes the
    block a transparent no-op so callers can write ``with json_output_guard(args.json):``
    without branching on the flag.
    """
    if not active:
        yield
        return
    take_over_stdout()
    try:
        yield
    finally:
        restore_stdout()
