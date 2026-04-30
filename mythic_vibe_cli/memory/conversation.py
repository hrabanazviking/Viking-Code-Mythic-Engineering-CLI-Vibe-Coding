"""Conversation log data layer (PH-15 slice 15.1).

Append-and-update primitive over JSON files in
``<root>/mythic/ai/conversations/``. The schema is intentionally
minimal — full per-provider response payloads belong in the
existing ``mythic/ai/`` audit trail; this module captures the
**conversation** (turn-by-turn user/assistant exchange) so future
sessions can replay or summarise the reasoning trail.

Public surface:

- :class:`ConversationTurn` — one role/content pair plus a
  timestamp and optional metadata dict.
- :class:`ConversationRecord` — full conversation: id, provider,
  model, created_at, updated_at, ordered tuple of turns, metadata.
- :func:`record_turn(root, conversation_id, role, content, *, ...)`
  — append-and-update primitive.
- :func:`read_conversation(root, conversation_id)` — typed loader,
  returns ``None`` for missing/corrupt records.
- :func:`list_conversations(root)` — sorted list of records (newest
  first by ``updated_at``).
- :func:`conversation_path_for(root, conversation_id)` — canonical
  path helper.
- :func:`new_conversation_id()` — ``CV-<6 hex>`` generator.

Cross-platform: stdlib only (``pathlib``, ``json``, ``secrets``,
``datetime``). Best-effort: file errors / JSON decode errors
return empty/None; never raise.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


CONVERSATION_DIR = ("mythic", "ai", "conversations")
CONVERSATION_ID_PREFIX = "CV-"

ConversationRole = Literal["user", "assistant", "system", "tool"]
_VALID_ROLES: tuple[ConversationRole, ...] = (
    "user",
    "assistant",
    "system",
    "tool",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_conversation_id() -> str:
    """Generate a fresh ``CV-<6 hex>`` id. Uses ``secrets.token_hex``
    so concurrent callers don't collide on a wall-clock timestamp."""
    return f"{CONVERSATION_ID_PREFIX}{secrets.token_hex(3).upper()}"


def conversation_path_for(root: Path, conversation_id: str) -> Path:
    """Canonical path for a conversation id under ``<root>/mythic/ai/``."""
    return Path(root).joinpath(*CONVERSATION_DIR, f"{conversation_id}.json")


@dataclass(frozen=True)
class ConversationTurn:
    role: ConversationRole
    content: str
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ConversationTurn":
        role_raw = str(payload.get("role", "user"))
        role: ConversationRole = (
            role_raw if role_raw in _VALID_ROLES else "user"  # type: ignore[assignment]
        )
        return cls(
            role=role,
            content=str(payload.get("content", "")),
            timestamp=str(payload.get("timestamp", "")),
            metadata=(
                dict(payload["metadata"])
                if isinstance(payload.get("metadata"), dict)
                else {}
            ),
        )


@dataclass(frozen=True)
class ConversationRecord:
    conversation_id: str
    provider: str
    model: str
    created_at: str
    updated_at: str
    turns: tuple[ConversationTurn, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "provider": self.provider,
            "model": self.model,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turns": [turn.to_dict() for turn in self.turns],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ConversationRecord":
        raw_turns = payload.get("turns")
        turns: list[ConversationTurn] = []
        if isinstance(raw_turns, list):
            for item in raw_turns:
                if isinstance(item, dict):
                    turns.append(ConversationTurn.from_dict(item))
        return cls(
            conversation_id=str(payload.get("conversation_id", "")),
            provider=str(payload.get("provider", "")),
            model=str(payload.get("model", "")),
            created_at=str(payload.get("created_at", "")),
            updated_at=str(payload.get("updated_at", "")),
            turns=tuple(turns),
            metadata=(
                dict(payload["metadata"])
                if isinstance(payload.get("metadata"), dict)
                else {}
            ),
        )


def _conversations_dir(root: Path) -> Path:
    return Path(root).joinpath(*CONVERSATION_DIR)


def record_turn(
    root: Path,
    conversation_id: str,
    role: ConversationRole,
    content: str,
    *,
    provider: str = "",
    model: str = "",
    metadata: dict[str, Any] | None = None,
) -> ConversationRecord:
    """Append a single turn to a conversation, creating the record on
    first call and updating ``updated_at`` on subsequent calls.

    Args:
        root: Project directory.
        conversation_id: ``CV-XXXXXX`` id; reuse the same id across
            calls in the same conversation.
        role: One of ``user`` / ``assistant`` / ``system`` / ``tool``.
            Unknown roles fall back to ``user``.
        content: The turn's text.
        provider / model: Recorded once on the first turn; subsequent
            calls preserve the original values unless either is non-
            empty (in which case the new value updates the record's
            top-level fields — useful for multi-provider conversations
            where the model can change mid-session).
        metadata: Optional turn-level metadata (e.g. tokens, latency,
            packet_id). Record-level metadata is *not* mutated by
            ``record_turn`` — use a separate updater for that if
            needed.

    Returns:
        The freshly-written :class:`ConversationRecord`.

    Raises:
        Never. File errors swallow the write but still return a
        well-formed record (the caller can still inspect it).
    """
    if role not in _VALID_ROLES:
        role = "user"

    now = _utc_now_iso()
    target_dir = _conversations_dir(root)
    path = target_dir / f"{conversation_id}.json"
    target_dir.mkdir(parents=True, exist_ok=True)

    existing = read_conversation(root, conversation_id)
    if existing is None:
        record = ConversationRecord(
            conversation_id=conversation_id,
            provider=provider,
            model=model,
            created_at=now,
            updated_at=now,
            turns=(
                ConversationTurn(
                    role=role,
                    content=content,
                    timestamp=now,
                    metadata=dict(metadata or {}),
                ),
            ),
            metadata={},
        )
    else:
        new_turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=now,
            metadata=dict(metadata or {}),
        )
        record = ConversationRecord(
            conversation_id=existing.conversation_id,
            provider=provider or existing.provider,
            model=model or existing.model,
            created_at=existing.created_at,
            updated_at=now,
            turns=existing.turns + (new_turn,),
            metadata=dict(existing.metadata),
        )

    try:
        path.write_text(
            json.dumps(record.to_dict(), indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        # Best-effort: still return the record so the caller can keep
        # operating, but the on-disk copy might be stale.
        return record
    return record


def read_conversation(root: Path, conversation_id: str) -> ConversationRecord | None:
    """Load a conversation record by id. Returns ``None`` for
    missing files or unparseable JSON."""
    path = conversation_path_for(root, conversation_id)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return ConversationRecord.from_dict(payload)


def list_conversations(root: Path) -> list[ConversationRecord]:
    """Return every readable conversation record in the project,
    sorted by ``updated_at`` descending (newest first). Malformed
    files are silently skipped."""
    target_dir = _conversations_dir(root)
    if not target_dir.is_dir():
        return []
    records: list[ConversationRecord] = []
    for path in sorted(target_dir.glob(f"{CONVERSATION_ID_PREFIX}*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        records.append(ConversationRecord.from_dict(payload))
    records.sort(key=lambda r: r.updated_at, reverse=True)
    return records


def latest_conversation(root: Path) -> ConversationRecord | None:
    """Convenience: return the most recently updated conversation, or
    ``None`` if the project has no conversations yet. Used by the
    slice 15.4 rehydrator."""
    records = list_conversations(root)
    return records[0] if records else None


def render_record_text(record: ConversationRecord) -> str:
    """Human-readable text rendering — used by the slice 15.3 CLI."""
    lines = [
        f"Conversation {record.conversation_id}",
        f"  provider: {record.provider or '(none)'}",
        f"  model: {record.model or '(none)'}",
        f"  created: {record.created_at}",
        f"  updated: {record.updated_at}",
        f"  turns: {record.turn_count}",
        "",
    ]
    for idx, turn in enumerate(record.turns, start=1):
        lines.append(f"--- turn {idx} [{turn.role}] {turn.timestamp} ---")
        lines.append(turn.content)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "CONVERSATION_DIR",
    "CONVERSATION_ID_PREFIX",
    "ConversationRecord",
    "ConversationRole",
    "ConversationTurn",
    "conversation_path_for",
    "latest_conversation",
    "list_conversations",
    "new_conversation_id",
    "read_conversation",
    "record_turn",
    "render_record_text",
]
