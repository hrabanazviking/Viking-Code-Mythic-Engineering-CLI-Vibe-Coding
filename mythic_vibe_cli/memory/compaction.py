"""Conversation compaction (PH-15 slice 15.2).

Compress long conversation histories into a running summary so the
context window stays well-used without losing the reasoning trail.

Algorithm v1 (intentionally pure-Python, no LLM):

1. **Salient line preservation.** Every line in every turn is
   inspected; lines whose lowercase prefix matches one of the
   :data:`SALIENT_PREFIXES` (decision / constraint / invariant /
   risk / rule / policy / TODO / note / "must" / "should") is
   preserved verbatim under a heading specific to that prefix.
   Slice 15.4 (rehydrate) leans on this — these are the lines a
   future session will most want to remember.

2. **Recent-turn passthrough.** The last ``keep_recent`` turns are
   reproduced verbatim — they're the operator's working context.

3. **Bulk summary.** Everything else folds into a single
   "Earlier turns" paragraph that records turn count + provider /
   model + character total. No LLM call — the goal is "context
   collapse", not "natural-language summary".

A future PH-15 slice (or PH-08 routing) can layer an LLM-driven
abstractive summary on top; that work is gated on a configurable
provider being available without blocking the operator. Until
then, the deterministic algorithm here covers the rehydrator's
needs.

Public surface:

- :func:`summarize_conversation(record, *, keep_recent=3)` — pure
  function returning a markdown summary string.
- :func:`compact_conversation(root, conversation_id, *, keep_recent,
  dry_run)` — writes the summary + JSON sidecar; idempotent; never
  mutates the original conversation file.
- :data:`SALIENT_PREFIXES` — table of (prefix, heading) tuples;
  exposed for tests + future tuning.

Cross-platform: stdlib only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .conversation import ConversationRecord, read_conversation


SUMMARY_DIR = ("mythic", "ai", "summaries")
DEFAULT_KEEP_RECENT = 3


# Each entry: (case-insensitive prefix string, target heading).
# Order matters — earlier entries win when a line matches multiple
# prefixes (e.g. "must" inside a "decision:" line is captured under
# Decisions, not Imperatives).
SALIENT_PREFIXES: tuple[tuple[str, str], ...] = (
    ("decision:", "Decisions"),
    ("decided:", "Decisions"),
    ("constraint:", "Constraints"),
    ("invariant:", "Invariants"),
    ("rule:", "Constraints"),
    ("policy:", "Constraints"),
    ("risk:", "Risks"),
    ("todo:", "Open items"),
    ("note:", "Notes"),
    ("must ", "Imperatives"),
    ("should ", "Imperatives"),
)


@dataclass(frozen=True)
class CompactionPayload:
    """Everything :func:`compact_conversation` returns. The slice 15.3
    `memory show --summary` action and the slice 15.4 rehydrator
    both consume this payload."""

    conversation_id: str
    generated_at: str
    keep_recent: int
    salient_buckets: dict[str, list[str]]
    recent_turns_count: int
    earlier_turns_count: int
    markdown_path: str
    json_path: str
    written: bool = False
    dry_run: bool = False
    summary_markdown: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "generated_at": self.generated_at,
            "keep_recent": self.keep_recent,
            "salient_buckets": {k: list(v) for k, v in self.salient_buckets.items()},
            "recent_turns_count": self.recent_turns_count,
            "earlier_turns_count": self.earlier_turns_count,
            "markdown_path": self.markdown_path,
            "json_path": self.json_path,
            "written": self.written,
            "dry_run": self.dry_run,
            "summary_markdown": self.summary_markdown,
            "metadata": dict(self.metadata),
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _classify_line(line: str) -> str | None:
    """Return the salient heading for ``line`` (case-insensitive
    prefix match), or ``None`` if no rule applies."""
    lowered = line.lower().lstrip()
    for prefix, heading in SALIENT_PREFIXES:
        if lowered.startswith(prefix):
            return heading
    return None


def _extract_salient(record: ConversationRecord, *, keep_recent: int) -> dict[str, list[str]]:
    """Walk every line of every non-recent turn, bucketing salient
    lines by their classified heading. Recent turns are excluded so
    the rendered summary doesn't duplicate content the
    "Recent turns" section already shows verbatim."""
    if record.turn_count == 0:
        return {}
    cutoff = max(0, record.turn_count - max(0, keep_recent))
    older = record.turns[:cutoff]
    buckets: dict[str, list[str]] = {}
    for turn in older:
        for line in turn.content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            heading = _classify_line(stripped)
            if heading is None:
                continue
            bucket = buckets.setdefault(heading, [])
            if stripped not in bucket:  # de-dupe within a heading
                bucket.append(stripped)
    return buckets


def summarize_conversation(
    record: ConversationRecord,
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
) -> str:
    """Render the markdown summary for a conversation record.

    Empty conversations produce a clean placeholder so the caller's
    rendering code never has to special-case them.
    """
    if record.turn_count == 0:
        return (
            f"# Compacted summary — {record.conversation_id}\n\n"
            f"_Conversation has no turns yet._\n"
        )

    cutoff = max(0, record.turn_count - max(0, keep_recent))
    older = record.turns[:cutoff]
    recent = record.turns[cutoff:]
    salient = _extract_salient(record, keep_recent=keep_recent)
    earlier_chars = sum(len(turn.content) for turn in older)

    lines: list[str] = [
        f"# Compacted summary — {record.conversation_id}",
        "",
        f"- provider: {record.provider or '(none)'}",
        f"- model: {record.model or '(none)'}",
        f"- created: {record.created_at}",
        f"- updated: {record.updated_at}",
        f"- total turns: {record.turn_count}",
        f"- recent (kept verbatim): {len(recent)}",
        f"- earlier (collapsed): {len(older)} turns / "
        f"{earlier_chars} chars",
        "",
    ]

    if salient:
        for heading in sorted(salient):
            lines.append(f"## {heading}")
            lines.append("")
            for entry in salient[heading]:
                lines.append(f"- {entry}")
            lines.append("")

    if older:
        lines.append("## Earlier turns (collapsed)")
        lines.append("")
        lines.append(
            f"_{len(older)} earlier turn(s) totalling {earlier_chars} "
            "characters; salient lines preserved above._"
        )
        lines.append("")

    if recent:
        lines.append(f"## Recent {len(recent)} turn(s)")
        lines.append("")
        for turn in recent:
            lines.append(f"### [{turn.role}] {turn.timestamp}")
            lines.append("")
            lines.append(turn.content)
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _summary_dir(root: Path) -> Path:
    return Path(root).joinpath(*SUMMARY_DIR)


def compact_conversation(
    root: Path,
    conversation_id: str,
    *,
    keep_recent: int = DEFAULT_KEEP_RECENT,
    dry_run: bool = False,
) -> CompactionPayload:
    """Generate a summary for ``conversation_id`` and write it to
    ``mythic/ai/summaries/<id>.md`` plus a JSON sidecar.

    The original conversation file is **never** mutated — slice
    15.2's contract is purely additive. Re-running over an already-
    compacted conversation produces a fresh summary (idempotent on
    on-disk state, not necessarily byte-identical because timestamps
    advance).

    Returns a :class:`CompactionPayload` describing what was written.
    Missing-conversation case still returns a payload with
    ``written=False`` and an explanatory ``metadata["error"]`` so the
    caller can emit a clean error without re-querying.
    """
    record = read_conversation(root, conversation_id)
    target_dir = _summary_dir(root)
    md_path = target_dir / f"{conversation_id}.md"
    json_path = target_dir / f"{conversation_id}.json"
    generated_at = _utc_now_iso()

    if record is None:
        return CompactionPayload(
            conversation_id=conversation_id,
            generated_at=generated_at,
            keep_recent=keep_recent,
            salient_buckets={},
            recent_turns_count=0,
            earlier_turns_count=0,
            markdown_path=str(md_path),
            json_path=str(json_path),
            written=False,
            dry_run=dry_run,
            summary_markdown="",
            metadata={"error": "conversation not found"},
        )

    summary_md = summarize_conversation(record, keep_recent=keep_recent)
    salient = _extract_salient(record, keep_recent=keep_recent)
    cutoff = max(0, record.turn_count - max(0, keep_recent))

    payload = CompactionPayload(
        conversation_id=conversation_id,
        generated_at=generated_at,
        keep_recent=keep_recent,
        salient_buckets=salient,
        recent_turns_count=record.turn_count - cutoff,
        earlier_turns_count=cutoff,
        markdown_path=str(md_path),
        json_path=str(json_path),
        written=False,
        dry_run=dry_run,
        summary_markdown=summary_md,
        metadata={
            "provider": record.provider,
            "model": record.model,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        },
    )

    if dry_run:
        return payload

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        md_path.write_text(summary_md, encoding="utf-8")
        json_path.write_text(
            json.dumps(payload.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        return CompactionPayload(
            conversation_id=conversation_id,
            generated_at=generated_at,
            keep_recent=keep_recent,
            salient_buckets=salient,
            recent_turns_count=payload.recent_turns_count,
            earlier_turns_count=payload.earlier_turns_count,
            markdown_path=str(md_path),
            json_path=str(json_path),
            written=False,
            dry_run=False,
            summary_markdown=summary_md,
            metadata={"error": str(exc)},
        )

    return CompactionPayload(
        conversation_id=conversation_id,
        generated_at=generated_at,
        keep_recent=keep_recent,
        salient_buckets=salient,
        recent_turns_count=payload.recent_turns_count,
        earlier_turns_count=payload.earlier_turns_count,
        markdown_path=str(md_path),
        json_path=str(json_path),
        written=True,
        dry_run=False,
        summary_markdown=summary_md,
        metadata=payload.metadata,
    )


def latest_summary_for(root: Path, conversation_id: str) -> str:
    """Return the most recent summary markdown for ``conversation_id``,
    or empty string if no summary has been written yet. Used by the
    slice 15.4 rehydrator."""
    md_path = _summary_dir(root) / f"{conversation_id}.md"
    if not md_path.is_file():
        return ""
    try:
        return md_path.read_text(encoding="utf-8")
    except OSError:
        return ""


__all__ = [
    "DEFAULT_KEEP_RECENT",
    "SALIENT_PREFIXES",
    "SUMMARY_DIR",
    "CompactionPayload",
    "compact_conversation",
    "latest_summary_for",
    "summarize_conversation",
]
