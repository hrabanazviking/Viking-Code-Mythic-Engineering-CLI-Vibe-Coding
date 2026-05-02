"""Cross-process file lock (Phase 19.0 / BS-6, audit remediation 2026-05-02).

The existing :mod:`mythic_vibe_cli.runtime.file_mutation_queue` uses
``threading.Lock`` keyed by ``os.path.realpath`` — provides
**intra-process** serialisation only. Two simultaneous CLI
invocations in different processes (e.g. an operator running
``mythic-vibe forge run`` in two terminals) can still race on
shared state files because each process has its own dict of locks.

This module adds a **cross-process** lock primitive built on stdlib
OS-level file locking:

- POSIX (Linux / macOS): ``fcntl.flock(fd, fcntl.LOCK_EX | LOCK_NB)``
  with a poll loop until acquired or the deadline expires.
- Windows: ``msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)`` with the same
  poll loop.

Both primitives **release automatically when the holding process
dies** (the OS releases all open file descriptors / handles, which
implicitly releases the lock). This is the load-bearing crash-
safety property — a crashed CLI can never leave the lock held.

The lock is keyed off a separate ``<target>.lock`` file rather than
the data file itself. Locking the data file directly works on POSIX
but interacts badly with Windows file-replacement (the file being
replaced may have a lock on it). A sidecar lock file dodges both
issues.

Cross-platform: stdlib only (``fcntl`` on POSIX, ``msvcrt`` on
Windows). Both are part of CPython's standard library.

Usage::

    from mythic_vibe_cli.runtime.cross_process_lock import cross_process_lock

    with cross_process_lock("mythic/forge_ledger.json.lock", deadline=30.0):
        # ... read-modify-write the protected resource ...

The lock auto-releases when the ``with`` block exits OR when the
process dies (whichever comes first).
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_DEADLINE_SECONDS = 30.0
DEFAULT_POLL_INTERVAL = 0.05


class CrossProcessLockTimeoutError(TimeoutError):
    """Raised when a cross-process lock cannot be acquired within
    the deadline. Subclass of ``TimeoutError`` so callers that
    catch ``TimeoutError`` (or its parent ``OSError``) get this
    naturally."""


# Platform branching: bind ``_try_acquire`` and ``_release`` once
# at import time so the hot path doesn't pay for ``os.name``
# checks per call.
if os.name == "nt":
    import msvcrt

    def _try_acquire(fd: int) -> bool:
        """Non-blocking exclusive lock attempt on Windows.
        ``LK_NBLCK`` returns immediately with ``OSError`` if the
        region is held by another process."""
        try:
            # Lock 1 byte at offset 0. Windows file locks are
            # mandatory; the byte range needs to match between
            # acquire and release.
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False

    def _release(fd: int) -> None:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            # Lock release is best-effort — process death also
            # releases the lock via OS handle cleanup.
            pass

else:
    import fcntl

    def _try_acquire(fd: int) -> bool:
        """Non-blocking exclusive lock attempt on POSIX.
        ``LOCK_EX | LOCK_NB`` raises ``BlockingIOError`` (a
        subclass of ``OSError``) when the lock is held."""
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, BlockingIOError):
            return False

    def _release(fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass


@contextmanager
def cross_process_lock(
    lock_path: str | os.PathLike[str],
    *,
    deadline: float = DEFAULT_DEADLINE_SECONDS,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> Iterator[None]:
    """Acquire an exclusive cross-process lock for the duration of
    the ``with`` block.

    Args:
        lock_path: Path to the lock file. Created if missing. The
            file's contents are unused — only the OS-level lock on
            its file descriptor matters.
        deadline: Maximum seconds to wait for the lock before
            raising :class:`CrossProcessLockTimeoutError`. Default
            30 seconds.
        poll_interval: Seconds to sleep between non-blocking
            acquisition attempts. Default 50ms — small enough that
            uncontended locks acquire instantly, large enough that
            contention doesn't busy-spin a core.

    Raises:
        :class:`CrossProcessLockTimeoutError` when the deadline
            elapses without acquiring the lock.

    The lock is **automatically released** when:
    - The ``with`` block exits normally or via exception, OR
    - The holding process dies (the OS closes the file descriptor,
      which releases the lock).

    Cross-platform: works the same way on POSIX (``fcntl.flock``)
    and Windows (``msvcrt.locking``).
    """
    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create or open the lock file. We use ``os.open`` so we have
    # the raw fd needed for the platform-specific lock primitives.
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)

    start = time.perf_counter()
    acquired = False
    try:
        while True:
            if _try_acquire(fd):
                acquired = True
                break
            elapsed = time.perf_counter() - start
            if elapsed >= deadline:
                raise CrossProcessLockTimeoutError(
                    f"Could not acquire cross-process lock on "
                    f"{path} within {deadline:.1f}s"
                )
            # Sleep at most until the deadline (don't overshoot
            # by a full poll_interval at the end).
            remaining = deadline - elapsed
            time.sleep(min(poll_interval, remaining))
        yield
    finally:
        if acquired:
            _release(fd)
        try:
            os.close(fd)
        except OSError:
            pass


__all__ = [
    "CrossProcessLockTimeoutError",
    "DEFAULT_DEADLINE_SECONDS",
    "DEFAULT_POLL_INTERVAL",
    "cross_process_lock",
]
