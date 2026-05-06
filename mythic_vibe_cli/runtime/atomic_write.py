"""Atomic-write helper (Phase 19.0 / L-10, audit remediation 2026-05-02).

Routes ``Path.write_text`` calls through a write-tmp + ``os.replace``
pattern so a process kill mid-write leaves either the prior good
file or the new one — never a half-written truncated artifact.

Pre-Phase-19, several artifact-writing call-sites used
``Path.write_text`` directly:

- ``verify/__init__.py:81,83`` — verification artifacts +
  ``latest.json``
- ``handoff.py:260-263`` — handoff JSON + markdown records
- ``forge_reflection.py:386,388`` — forge reflection artifacts

These are observational artifacts (not primary state), so the
impact of a kill-mid-write was bounded data loss of one record
rather than corruption of project state — but unnecessary
corruption nonetheless. This helper closes the gap without
changing the files' on-disk shape.

The same pattern is also used in:
- ``persistence/json_store.py:write_state`` (the primary state
  store; predates this helper).
- ``forge_ledger.py:_write_entries`` (BS-5 fix; uses an inlined
  variant with retry).

Future writers should prefer this helper.

Cross-platform: pure stdlib (``os``, ``secrets``, ``time``).
``os.replace`` is atomic on POSIX (``rename(2)``) and on Windows
(``MoveFileEx`` with ``MOVEFILE_REPLACE_EXISTING``).
"""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path


def atomic_write_text(
    path: str | os.PathLike[str],
    text: str,
    *,
    encoding: str = "utf-8",
    retries: int = 5,
    base_delay: float = 0.05,
) -> None:
    """Write ``text`` to ``path`` atomically via tmp file + os.replace.

    The parent directory is created if missing. The tmp filename
    includes a random hex suffix per write to avoid any contention
    on a shared ``.tmp`` name. On Windows-specific
    ``PermissionError`` from antivirus / indexing-service handle
    contention, the ``os.replace`` is retried with exponential
    backoff (50ms → 100ms → 200ms → 400ms → 800ms by default).
    POSIX never hits the retry branch — ``rename(2)`` doesn't
    suffer from this class of failure.

    On any exception, the tmp file is best-effort cleaned up so we
    don't leave junk behind.

    Args:
        path: Target file path.
        text: Text content to write.
        encoding: File encoding (default utf-8).
        retries: Max ``os.replace`` retry attempts on
            PermissionError. Default 5.
        base_delay: Initial retry delay in seconds. Doubled on each
            attempt up to ~``base_delay * 2**(retries-1)``. Default
            50ms.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.{secrets.token_hex(6)}.tmp")
    try:
        # PH-24.4 (cross-platform regression sweep, 2026-05-05):
        # ``newline=""`` disables Python's text-mode newline
        # translation. Without it, ``Path.write_text`` would convert
        # every ``\n`` to ``\r\n`` on Windows — producing artifacts
        # that are byte-different from the same content written on
        # POSIX, which breaks Sigstore/SLSA hashing, attestation
        # signatures, and JSONL diffs across release machines.
        tmp.write_text(text, encoding=encoding, newline="")
        _replace_with_retry(tmp, target, retries=retries, base_delay=base_delay)
    except BaseException:
        # Best-effort cleanup of the tmp file on ANY exit path —
        # ``BaseException`` covers KeyboardInterrupt + SystemExit
        # as well as ``Exception`` subclasses, so a Ctrl+C
        # mid-write doesn't leave orphan .tmp files behind.
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _replace_with_retry(
    src: Path, dst: Path, *, retries: int = 5, base_delay: float = 0.05
) -> None:
    """``os.replace`` with a brief retry loop on Windows-specific
    ``PermissionError`` from transient handle contention. Internal
    helper — most callers use :func:`atomic_write_text` instead."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError as exc:
            last_exc = exc
            if attempt + 1 < retries:
                time.sleep(base_delay * (1 << attempt))
                continue
            raise
    if last_exc is not None:  # pragma: no cover — unreachable
        raise last_exc


__all__ = [
    "atomic_write_text",
]
