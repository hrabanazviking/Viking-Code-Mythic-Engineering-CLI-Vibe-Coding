# Portions adapted from badlogic/pi-mono (packages/coding-agent/src/core/timings.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md at the repo root.
"""Lightweight elapsed-time instrumentation.

Pi gates the primitive on the ``PI_TIMING`` environment variable; we use
``MYTHIC_TIMING`` and accept the same permissive truthy values as the rest
of the codebase (``1`` / ``true`` / ``yes`` / ``on``). Default: disabled.

Three public functions:

- :func:`reset_timings` clears the in-memory record list and re-baselines.
- :func:`record` appends a labelled delta in milliseconds since the last
  ``record`` (or ``reset_timings``) call.
- :func:`print_timings` flushes the recorded entries to ``sys.stderr`` in
  pi-style format with a TOTAL footer.

When the env var is unset, all three functions are inexpensive no-ops. Call
sites can sprinkle ``record("label")`` calls without conditional gating.

The clock uses ``time.perf_counter`` for sub-millisecond resolution; output
is rounded to one decimal of a millisecond.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import sys
import time as _time


@dataclass
class _TimingEntry:
    label: str
    ms: float


_entries: list[_TimingEntry] = []
_last_perf: float = _time.perf_counter()


def _is_enabled() -> bool:
    raw = os.environ.get("MYTHIC_TIMING", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def reset_timings() -> None:
    """Clear all recorded entries and re-baseline the elapsed clock."""
    if not _is_enabled():
        return
    _entries.clear()
    global _last_perf
    _last_perf = _time.perf_counter()


def record(label: str) -> None:
    """Append a labelled millisecond delta since the previous ``record`` call.

    A no-op when ``MYTHIC_TIMING`` is not set to a truthy value.
    """
    if not _is_enabled():
        return
    now = _time.perf_counter()
    global _last_perf
    delta_ms = (now - _last_perf) * 1000.0
    _entries.append(_TimingEntry(label=str(label), ms=delta_ms))
    _last_perf = now


def print_timings() -> None:
    """Flush recorded entries to stderr in pi-style format. No-op when
    disabled or when no entries are present."""
    if not _is_enabled() or not _entries:
        return
    print("\n--- Mythic Timings ---", file=sys.stderr)
    total = 0.0
    for entry in _entries:
        print(f"  {entry.label}: {entry.ms:.1f}ms", file=sys.stderr)
        total += entry.ms
    print(f"  TOTAL: {total:.1f}ms", file=sys.stderr)
    print("------------------------\n", file=sys.stderr)
