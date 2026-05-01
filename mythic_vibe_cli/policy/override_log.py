"""Override audit log (PH-14 Slice 14.3).

Append-only JSONL ledger at ``mythic/policy_overrides.jsonl``.
One entry per ``--override "<reason>"``-flagged command. The
slice-14.4 ``mythic-vibe policy report`` command reads this
ledger to render override history.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


OVERRIDE_LOG_PATH = Path("mythic") / "policy_overrides.jsonl"


@dataclass(frozen=True)
class OverrideRecord:
    """One audit-log entry."""

    timestamp: str
    action: str
    command: str
    reason: str
    actor: str
    host: str
    violation_ids: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "command": self.command,
            "reason": self.reason,
            "actor": self.actor,
            "host": self.host,
            "violation_ids": list(self.violation_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OverrideRecord":
        violations = payload.get("violation_ids") or []
        if not isinstance(violations, list):
            violations = []
        return cls(
            timestamp=str(payload.get("timestamp") or ""),
            action=str(payload.get("action") or ""),
            command=str(payload.get("command") or ""),
            reason=str(payload.get("reason") or ""),
            actor=str(payload.get("actor") or ""),
            host=str(payload.get("host") or ""),
            violation_ids=tuple(str(v) for v in violations if v),
        )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_actor() -> str:
    for env_var in ("USER", "USERNAME", "LOGNAME"):
        value = os.environ.get(env_var, "").strip()
        if value:
            return value
    return "unknown"


def _resolve_host() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


def append_override(
    root: Path,
    *,
    action: str,
    command: str,
    reason: str,
    violation_ids: Iterable[str] = (),
    actor: str | None = None,
    host: str | None = None,
    timestamp: str | None = None,
) -> Path:
    """Append a new :class:`OverrideRecord` to the ledger.
    Returns the ledger path. Best-effort — disk failures
    propagate so the gate caller can decide whether to swallow."""
    ledger = Path(root) / OVERRIDE_LOG_PATH
    ledger.parent.mkdir(parents=True, exist_ok=True)
    record = OverrideRecord(
        timestamp=timestamp or _utc_now_iso(),
        action=action,
        command=command,
        reason=reason,
        actor=actor or _resolve_actor(),
        host=host or _resolve_host(),
        violation_ids=tuple(str(v) for v in violation_ids if v),
    )
    line = json.dumps(record.to_dict(), ensure_ascii=False) + "\n"
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(line)
    return ledger


def read_overrides(root: Path) -> list[OverrideRecord]:
    """Load all override records from the ledger. Missing file →
    empty list. Malformed lines skipped silently."""
    ledger = Path(root) / OVERRIDE_LOG_PATH
    if not ledger.is_file():
        return []
    records: list[OverrideRecord] = []
    try:
        body = ledger.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        records.append(OverrideRecord.from_dict(payload))
    return records


__all__ = [
    "OVERRIDE_LOG_PATH",
    "OverrideRecord",
    "append_override",
    "read_overrides",
]
