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
        with log_path.open("a", encoding="utf-8") as fh:
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
    with path.open("r", encoding="utf-8") as fh:
        lines = fh.readlines()
    tail = lines[-keep:]
    fd, tmp_name = tempfile.mkstemp(prefix=".events.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
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
