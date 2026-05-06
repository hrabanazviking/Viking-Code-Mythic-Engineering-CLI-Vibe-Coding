"""Bounded append-and-tail event log.

Every plugin-hook event the dispatcher fires is also appended here as a
single JSON line. The log is best-effort — we don't lock across processes,
so concurrent CLI runs may interleave entries. That's acceptable: the log
is for observation, not coordination.

The file is bounded by line count (default 200). When the cap is exceeded,
we rewrite the file with only the most recent N lines. The cost of the
rewrite is amortized across the next N appends.

Cross-platform: pure Python `pathlib`, `json`, `tempfile` — no platform
branches.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable

DEFAULT_EVENT_LOG_FILENAME = "events.jsonl"
DEFAULT_MAX_ENTRIES = 200

EVENT_LOG_LIMIT_ENV = "MYTHIC_EVENT_LOG_LIMIT"


def resolve_max_entries(default: int = DEFAULT_MAX_ENTRIES) -> int:
    """Resolve the bounded-event-log cap from ``MYTHIC_EVENT_LOG_LIMIT``.

    The env var, when set to a positive integer, overrides the built-in
    200-entry default. Any non-positive or non-integer value is ignored
    silently (the function is best-effort, matching the rest of the
    event-log surface). Larger projects with high-frequency plugin emits
    can raise the cap; tests can lower it.
    """
    raw = os.environ.get(EVENT_LOG_LIMIT_ENV)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


@dataclass(frozen=True)
class EventLogEntry:
    timestamp: str
    channel: str
    summary: str

    def to_dict(self) -> dict[str, str]:
        return {"timestamp": self.timestamp, "channel": self.channel, "summary": self.summary}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _summarize(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("path", "task", "verification_id", "handoff_id", "packet_id"):
            value = payload.get(key)
            if value:
                return f"{key}={value}"
        if payload:
            first_key = next(iter(payload), "")
            return f"{first_key}={payload.get(first_key, '')}"
        return ""
    if payload is None:
        return ""
    return str(payload)[:120]


def append_event(
    log_path: Path,
    channel: str,
    payload: Any,
    *,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> EventLogEntry:
    """Append one event line and rotate if we've exceeded ``max_entries``.

    Returns the appended entry. Best-effort — IO errors are swallowed and the
    returned entry is still constructed (caller may inspect it for tests).
    """
    entry = EventLogEntry(timestamp=_utc_now_iso(), channel=channel, summary=_summarize(payload))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # PH-24.4 cross-platform sweep: ``newline=""`` keeps the
        # JSONL byte-stable across Windows + POSIX. Without it,
        # ``\n`` is translated to ``\r\n`` on Windows, which would
        # break ``read_recent`` consumers that line-split on ``\n``
        # if a Windows-written log were later read on a strict
        # binary-mode reader.
        with log_path.open("a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")
    except OSError:
        return entry

    try:
        line_count = _count_lines(log_path)
    except OSError:
        return entry

    if line_count > max_entries:
        try:
            _rewrite_with_tail(log_path, max_entries)
        except OSError:
            return entry

    return entry


def read_recent(log_path: Path, *, limit: int = 20) -> list[EventLogEntry]:
    """Return up to ``limit`` most recent entries (newest last)."""
    if not log_path.exists():
        return []
    try:
        with log_path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except OSError:
        return []

    recent_lines = lines[-limit:]
    out: list[EventLogEntry] = []
    for raw in recent_lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        out.append(
            EventLogEntry(
                timestamp=str(payload.get("timestamp", "")),
                channel=str(payload.get("channel", "")),
                summary=str(payload.get("summary", "")),
            )
        )
    return out


def _count_lines(path: Path) -> int:
    count = 0
    with path.open("rb") as fh:
        for _line in fh:
            count += 1
    return count


def _rewrite_with_tail(path: Path, keep: int) -> None:
    # PH-24.4: ``newline=""`` on both read + write preserves the
    # exact byte stream so a rotation cycle never silently mutates
    # the trailing lines.
    with path.open("r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()
    tail = lines[-keep:]
    fd, tmp_name = tempfile.mkstemp(prefix=".events.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.writelines(tail)
        os.replace(tmp_name, path)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            # Temp file may already be gone if os.replace partially succeeded; cleanup is best-effort.
            pass
        raise


def event_log_path_for(root: Path) -> Path:
    return Path(root) / "mythic" / DEFAULT_EVENT_LOG_FILENAME


def write_entries(log_path: Path, entries: Iterable[EventLogEntry]) -> None:
    """Replace the log contents with the provided entries (used by tests)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry.to_dict()) + "\n")


# ---- Tail-style streaming (PH-04 slice 4.6) ----------------------------


DEFAULT_TAIL_WINDOW = 14


@dataclass(frozen=True)
class EventStreamSnapshot:
    """Immutable view returned by :meth:`EventTailReader.poll`.

    ``entries`` is the current sliding window (newest last). ``new_in_last_poll``
    is the count of entries that were appended since the previous poll —
    a "live pulse" indicator the TUI uses. ``total_seen`` is cumulative
    across the reader's lifetime, useful for a "+N since open" counter.
    """

    entries: tuple[EventLogEntry, ...]
    new_in_last_poll: int
    total_seen: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "new_in_last_poll": self.new_in_last_poll,
            "total_seen": self.total_seen,
        }


def _parse_event_lines(text: str) -> list[EventLogEntry]:
    """Best-effort JSON-line decode. Malformed lines are silently skipped
    (matching :func:`read_recent`'s contract)."""
    out: list[EventLogEntry] = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        out.append(
            EventLogEntry(
                timestamp=str(payload.get("timestamp", "")),
                channel=str(payload.get("channel", "")),
                summary=str(payload.get("summary", "")),
            )
        )
    return out


class EventTailReader:
    """Stateful tail-style reader for ``events.jsonl``.

    On construction, seeds its buffer from the current tail of the file
    (warm start — existing entries are visible but **don't** count as
    "new"). Each :meth:`poll` reads only the bytes appended since the
    last poll, decodes them, appends to the buffer, and trims the
    buffer back to the configured window.

    Robust to:

    - file not yet existing (poll returns an empty snapshot)
    - no growth between polls (poll returns ``new_in_last_poll == 0``)
    - file rotation / truncation (size shrinks → re-seed buffer from the
      new contents and report ``new_in_last_poll == 0`` because rotation
      is bookkeeping, not a real event)
    - malformed JSON lines (skipped)

    Cross-platform: relies only on ``Path.stat()`` and a single seekable
    text read; no fcntl, no inode tracking, no platform branches.
    """

    def __init__(
        self,
        log_path: Path,
        *,
        window: int = DEFAULT_TAIL_WINDOW,
    ) -> None:
        self.log_path = log_path
        self.window = max(1, window)
        self._buffer: list[EventLogEntry] = []
        self._last_size: int = 0
        self._total_seen: int = 0
        self._seed_from_disk()

    def _seed_from_disk(self) -> None:
        """Populate the buffer with the latest ``window`` entries on open
        and remember the file size, so subsequent polls only see truly
        new bytes."""
        if not self.log_path.exists():
            return
        try:
            self._last_size = self.log_path.stat().st_size
        except OSError:
            self._last_size = 0
            return
        self._buffer = read_recent(self.log_path, limit=self.window)

    def _empty_snapshot(self) -> EventStreamSnapshot:
        return EventStreamSnapshot(
            entries=tuple(self._buffer),
            new_in_last_poll=0,
            total_seen=self._total_seen,
        )

    def poll(self) -> EventStreamSnapshot:
        """Read newly appended bytes (if any) and return the current snapshot."""
        if not self.log_path.exists():
            return self._empty_snapshot()

        try:
            current_size = self.log_path.stat().st_size
        except OSError:
            return self._empty_snapshot()

        if current_size < self._last_size:
            # File rotated / truncated. Re-seed without claiming new events.
            self._buffer = read_recent(self.log_path, limit=self.window)
            self._last_size = current_size
            return self._empty_snapshot()

        if current_size == self._last_size:
            return self._empty_snapshot()

        try:
            with self.log_path.open("r", encoding="utf-8") as fh:
                fh.seek(self._last_size)
                new_text = fh.read()
        except OSError:
            return self._empty_snapshot()

        new_entries = _parse_event_lines(new_text)
        self._last_size = current_size
        if not new_entries:
            return self._empty_snapshot()

        self._buffer.extend(new_entries)
        if len(self._buffer) > self.window:
            self._buffer = self._buffer[-self.window:]
        self._total_seen += len(new_entries)
        return EventStreamSnapshot(
            entries=tuple(self._buffer),
            new_in_last_poll=len(new_entries),
            total_seen=self._total_seen,
        )
