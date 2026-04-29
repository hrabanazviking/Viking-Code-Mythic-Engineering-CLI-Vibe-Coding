# Portions adapted from badlogic/pi-mono (packages/coding-agent/src/core/tools/file-mutation-queue.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md at the repo root.
"""Serialize file mutation operations targeting the same resolved path.

Operations for different files still run in parallel. Symlink aliases that
resolve to the same target share the same queue, mirroring pi's
``getMutationQueueKey`` semantics.

This is the synchronous Python translation of pi's async TypeScript queue.
Pi uses chained Promises; we use ``threading.Lock`` instances keyed by
``os.path.realpath``. Reference counting drops the lock entry when the last
waiter exits, matching pi's "delete on empty queue" cleanup.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import os
import threading
from pathlib import Path
from typing import Callable, Iterator, TypeVar


T = TypeVar("T")


@dataclass
class _QueueEntry:
    lock: threading.Lock = field(default_factory=threading.Lock)
    refcount: int = 0


_locks: dict[str, _QueueEntry] = {}
_locks_guard = threading.Lock()


def _mutation_queue_key(file_path: str | os.PathLike[str]) -> str:
    resolved = Path(file_path).resolve()
    try:
        return os.path.realpath(str(resolved))
    except OSError:
        return str(resolved)


@contextmanager
def file_mutation_queue(file_path: str | os.PathLike[str]) -> Iterator[None]:
    """Acquire the per-path mutation lock for the duration of the ``with`` block.

    Operations for different resolved paths proceed in parallel. Operations on
    the same resolved path are serialized in arrival order. Symlink aliases
    that resolve to the same target share a single queue.
    """
    key = _mutation_queue_key(file_path)
    with _locks_guard:
        entry = _locks.get(key)
        if entry is None:
            entry = _QueueEntry()
            _locks[key] = entry
        entry.refcount += 1

    entry.lock.acquire()
    try:
        yield
    finally:
        entry.lock.release()
        with _locks_guard:
            entry.refcount -= 1
            if entry.refcount == 0 and _locks.get(key) is entry:
                del _locks[key]


def with_file_mutation_queue(
    file_path: str | os.PathLike[str],
    fn: Callable[[], T],
) -> T:
    """Functional form of :func:`file_mutation_queue` mirroring pi's TS API."""
    with file_mutation_queue(file_path):
        return fn()
