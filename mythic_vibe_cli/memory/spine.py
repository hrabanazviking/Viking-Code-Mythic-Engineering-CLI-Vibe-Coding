"""SQLite memory spine for companion-shell continuity.

Phase 5 of the reforge roadmap needs durable local memory at
``<root>/.mythic/memory.sqlite`` so the interactive shell can answer
resume questions without depending on terminal scrollback or a remote
provider. This module is intentionally small and provider-neutral:
it stores typed memory entries and renders a deterministic "last time"
brief from the most recent entries.

The older PH-15 conversation log remains under ``mythic/ai``. This
spine is the project-level continuity layer that the companion shell
and handoff machinery can append to.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any, Iterable

from ..runtime.paths import paths_for


MEMORY_DB = (".mythic", "memory.sqlite")
SCHEMA_VERSION = 1

MEMORY_KINDS: tuple[str, ...] = (
    "session_summary",
    "project_decision",
    "task",
    "file_touched",
    "failed_attempt",
    "successful_fix",
    "next_step",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def memory_db_path(root: Path) -> Path:
    return paths_for(root).memory_db


def memory_backup_dir(root: Path) -> Path:
    return paths_for(root).private_state_dir / "backups"


def quarantine_memory_db(root: Path) -> Path | None:
    path = memory_db_path(root)
    if not path.exists():
        return None
    backup_dir = memory_backup_dir(root)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    target = backup_dir / f"memory.sqlite.{stamp}.corrupt"
    suffix = 1
    while target.exists():
        target = backup_dir / f"memory.sqlite.{stamp}.{suffix}.corrupt"
        suffix += 1
    shutil.move(str(path), str(target))
    for sidecar in (
        path.with_name(path.name + "-wal"),
        path.with_name(path.name + "-shm"),
    ):
        if sidecar.exists():
            sidecar_target = target.with_name(target.name + sidecar.name.removeprefix(path.name))
            try:
                shutil.move(str(sidecar), str(sidecar_target))
            except OSError:
                pass
    return target


@dataclass(frozen=True)
class MemoryEntry:
    entry_id: int
    created_at: str
    updated_at: str
    kind: str
    content: str
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "kind": self.kind,
            "content": self.content,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class MemorySnapshot:
    db_path: str
    entries: tuple[MemoryEntry, ...]
    counts: dict[str, int]

    @property
    def has_memory(self) -> bool:
        return bool(self.entries)

    def latest_for(self, kind: str, *, limit: int = 3) -> tuple[MemoryEntry, ...]:
        matches = [entry for entry in self.entries if entry.kind == kind]
        return tuple(matches[: max(0, limit)])

    def to_dict(self) -> dict[str, Any]:
        return {
            "db_path": self.db_path,
            "counts": dict(self.counts),
            "entries": [entry.to_dict() for entry in self.entries],
        }


def _connect_once(root: Path) -> sqlite3.Connection:
    path = memory_db_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _connect(root: Path) -> sqlite3.Connection:
    try:
        return _connect_once(root)
    except sqlite3.DatabaseError:
        quarantine_memory_db(root)
        return _connect_once(root)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS memory_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_kind_created
        ON memory_entries(kind, created_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memory_entries_created
        ON memory_entries(created_at DESC)
        """
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO memory_meta(key, value)
        VALUES('schema_version', ?)
        """,
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def init_memory_spine(root: Path) -> Path:
    with _connect(root):
        pass
    return memory_db_path(root)


def _metadata_json(metadata: dict[str, Any] | None) -> str:
    try:
        return json.dumps(dict(metadata or {}), sort_keys=True)
    except (TypeError, ValueError):
        return "{}"


def _entry_from_row(row: sqlite3.Row) -> MemoryEntry:
    try:
        metadata = json.loads(str(row["metadata_json"] or "{}"))
    except json.JSONDecodeError:
        metadata = {}
    if not isinstance(metadata, dict):
        metadata = {}
    return MemoryEntry(
        entry_id=int(row["entry_id"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        kind=str(row["kind"]),
        content=str(row["content"]),
        source=str(row["source"]),
        metadata=metadata,
    )


def record_memory(
    root: Path,
    kind: str,
    content: str,
    *,
    source: str = "",
    metadata: dict[str, Any] | None = None,
) -> MemoryEntry:
    """Append one typed memory entry to the local SQLite spine."""
    normalized_kind = kind if kind in MEMORY_KINDS else "session_summary"
    text = str(content).strip() or "(empty)"
    now = _utc_now_iso()
    with _connect(root) as conn:
        cursor = conn.execute(
            """
            INSERT INTO memory_entries(
                created_at, updated_at, kind, content, source, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                normalized_kind,
                text,
                str(source or ""),
                _metadata_json(metadata),
            ),
        )
        row = conn.execute(
            "SELECT * FROM memory_entries WHERE entry_id = ?",
            (int(cursor.lastrowid),),
        ).fetchone()
    return _entry_from_row(row)


def list_memory(
    root: Path,
    *,
    kinds: Iterable[str] | None = None,
    limit: int = 20,
) -> list[MemoryEntry]:
    selected = [kind for kind in (kinds or ()) if kind in MEMORY_KINDS]
    capped = max(1, min(200, int(limit or 20)))
    with _connect(root) as conn:
        if selected:
            placeholders = ",".join("?" for _ in selected)
            rows = conn.execute(
                f"""
                SELECT * FROM memory_entries
                WHERE kind IN ({placeholders})
                ORDER BY created_at DESC, entry_id DESC
                LIMIT ?
                """,
                (*selected, capped),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM memory_entries
                ORDER BY created_at DESC, entry_id DESC
                LIMIT ?
                """,
                (capped,),
            ).fetchall()
    return [_entry_from_row(row) for row in rows]


def count_memory_by_kind(root: Path) -> dict[str, int]:
    with _connect(root) as conn:
        rows = conn.execute(
            """
            SELECT kind, COUNT(*) AS count
            FROM memory_entries
            GROUP BY kind
            """
        ).fetchall()
    counts = {kind: 0 for kind in MEMORY_KINDS}
    for row in rows:
        kind = str(row["kind"])
        if kind in counts:
            counts[kind] = int(row["count"])
    return counts


def build_memory_snapshot(root: Path, *, limit: int = 30) -> MemorySnapshot:
    return MemorySnapshot(
        db_path=str(memory_db_path(root)),
        entries=tuple(list_memory(root, limit=limit)),
        counts=count_memory_by_kind(root),
    )


def record_session_summary(
    root: Path,
    *,
    summary: str,
    decisions: Iterable[str] = (),
    tasks: Iterable[str] = (),
    files_touched: Iterable[str] = (),
    failed_attempts: Iterable[str] = (),
    successful_fixes: Iterable[str] = (),
    next_steps: Iterable[str] = (),
    source: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Record a complete session summary plus its structured facets."""
    record_memory(root, "session_summary", summary, source=source, metadata=metadata)
    for kind, values in (
        ("project_decision", decisions),
        ("task", tasks),
        ("file_touched", files_touched),
        ("failed_attempt", failed_attempts),
        ("successful_fix", successful_fixes),
        ("next_step", next_steps),
    ):
        for value in values:
            text = str(value).strip()
            if text:
                record_memory(root, kind, text, source=source, metadata=metadata)


def record_shell_exchange(
    root: Path,
    *,
    prompt: str,
    response: str,
    provider: str,
    model: str,
    context_kind: str = "conversation",
) -> None:
    """Persist a companion-shell natural prompt and response."""
    prompt_text = str(prompt).strip()
    response_text = str(response).strip()
    if not prompt_text and not response_text:
        return
    metadata = {
        "provider": provider,
        "model": model,
        "context_kind": context_kind,
    }
    if prompt_text:
        record_memory(
            root,
            "task",
            prompt_text,
            source="companion-shell",
            metadata=metadata,
        )
    summary = f"User: {prompt_text}\nAssistant: {response_text or '(no response)'}"
    record_memory(
        root,
        "session_summary",
        summary,
        source="companion-shell",
        metadata=metadata,
    )


def record_handoff_memory(root: Path, handoff: object) -> None:
    """Fold an existing handoff record into the SQLite spine."""
    objective = str(getattr(handoff, "objective", "") or "").strip()
    timestamp = str(getattr(handoff, "timestamp", "") or "").strip()
    handoff_id = str(getattr(handoff, "handoff_id", "") or "").strip()
    verification = str(getattr(handoff, "verification_result", "") or "").strip()
    summary_parts = []
    if objective:
        summary_parts.append(objective)
    if timestamp:
        summary_parts.append(f"recorded at {timestamp}")
    summary = "; ".join(summary_parts) or "Session handoff recorded."
    metadata = {
        "handoff_id": handoff_id,
        "timestamp": timestamp,
        "verification_result": verification,
    }
    successful_fixes = ()
    if verification == "pass" and objective:
        successful_fixes = (objective,)
    record_session_summary(
        root,
        summary=summary,
        decisions=getattr(handoff, "decisions", ()) or (),
        tasks=(objective,) if objective else (),
        files_touched=getattr(handoff, "files_changed", ()) or (),
        failed_attempts=getattr(handoff, "failures", ()) or (),
        successful_fixes=successful_fixes,
        next_steps=getattr(handoff, "next_steps", ()) or (),
        source="handoff",
        metadata=metadata,
    )


def render_last_time(root: Path) -> str:
    """Render a deterministic resume answer from the memory spine."""
    snapshot = build_memory_snapshot(root)
    if not snapshot.has_memory:
        return (
            "Memory spine\n"
            "  No recorded session memory yet.\n"
            "  Natural shell prompts and handoffs will be stored in .mythic/memory.sqlite."
        )

    lines = ["Last remembered work", f"  Storage: {'.mythic/memory.sqlite'}"]

    latest_summary = snapshot.latest_for("session_summary", limit=1)
    if latest_summary:
        entry = latest_summary[0]
        lines.extend(
            [
                "",
                "Summary:",
                f"  {entry.content}",
            ]
        )

    sections = (
        ("Recent tasks", "task"),
        ("Project decisions", "project_decision"),
        ("Files touched", "file_touched"),
        ("Failed attempts", "failed_attempt"),
        ("Successful fixes", "successful_fix"),
        ("Next steps", "next_step"),
    )
    for title, kind in sections:
        entries = snapshot.latest_for(kind, limit=3)
        if not entries:
            continue
        lines.extend(["", f"{title}:"])
        for entry in entries:
            lines.append(f"  - {entry.content}")

    return "\n".join(lines)


__all__ = [
    "MEMORY_DB",
    "MEMORY_KINDS",
    "MemoryEntry",
    "MemorySnapshot",
    "build_memory_snapshot",
    "count_memory_by_kind",
    "init_memory_spine",
    "list_memory",
    "memory_db_path",
    "record_handoff_memory",
    "record_memory",
    "record_session_summary",
    "record_shell_exchange",
    "render_last_time",
]
