"""Per-agent forge handoff ledger.

PH-03 slice 3.2. Pure persistence layer — no orchestrator, no CLI
command, no provider call. Records every individual agent step that
the future ``mythic-vibe forge`` orchestrator runs, with the typed
:class:`AgentInput` / :class:`AgentOutput` payloads from
:mod:`mythic_vibe_cli.workflow_agents` plus status / timing
metadata.

Why this is separate from ``workflow_history.json``:

The existing :data:`mythic_vibe_cli.workflow_engine.WORKFLOW_HISTORY_FILENAME`
records one entry per generated *plan* (workflow_id, task,
created_at, plan_path, role_sequence). It is consumed by
``mythic-vibe workflow history``.

The new ``forge_ledger.json`` records one entry per *step* — finer
granularity. The two ledgers serve different purposes and live in
different files so neither has to grow a discriminator field. Slice
3.3 will add a ``forge ledger`` inspection subcommand for the new
file (the existing ``workflow history`` command continues to read
the plan-level ledger).

Concurrent writes to the same ledger file are serialised through
:func:`mythic_vibe_cli.runtime.file_mutation_queue.file_mutation_queue`
so two simultaneous forge runs cannot corrupt each other's writes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .runtime.file_mutation_queue import file_mutation_queue
from .workflow_agents import AgentInput, AgentOutput


FORGE_LEDGER_FILENAME = "forge_ledger.json"
FORGE_LEDGER_LIMIT = 200
FORGE_LEDGER_SCHEMA_VERSION = 1

# Step lifecycle:
#   pending   — entry written; agent has not started yet
#   running   — agent has started; output not yet captured
#   succeeded — agent finished; all gates passed
#   failed    — agent finished; one or more gates failed
#   blocked   — orchestrator refused to advance (e.g., contract validation
#              against AgentInput/AgentOutput failed structurally)
FORGE_STEP_STATUSES: tuple[str, ...] = (
    "pending",
    "running",
    "succeeded",
    "failed",
    "blocked",
)


@dataclass(frozen=True)
class ForgeLedgerEntry:
    """One row in the forge ledger.

    ``agent_input`` is required (a step always has an input). ``agent_output``
    is None until the step completes. ``duration_ms`` is None until the step
    has both started_at and completed_at recorded.
    """

    workflow_id: str
    step_id: str
    role: str
    status: str
    started_at: str
    agent_input: AgentInput
    completed_at: str | None = None
    duration_ms: int | None = None
    agent_output: AgentOutput | None = None
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "role": self.role,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "agent_input": self.agent_input.to_dict(),
            "agent_output": self.agent_output.to_dict() if self.agent_output else None,
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ForgeLedgerEntry":
        agent_input_payload = payload.get("agent_input")
        if not isinstance(agent_input_payload, dict):
            raise ValueError("ForgeLedgerEntry.agent_input must be an object")
        agent_input = AgentInput.from_dict(agent_input_payload)

        agent_output: AgentOutput | None = None
        agent_output_payload = payload.get("agent_output")
        if isinstance(agent_output_payload, dict):
            agent_output = AgentOutput.from_dict(agent_output_payload)

        duration_raw = payload.get("duration_ms")
        try:
            duration_ms = int(duration_raw) if duration_raw is not None else None
        except (TypeError, ValueError):
            duration_ms = None

        return cls(
            workflow_id=str(payload.get("workflow_id") or ""),
            step_id=str(payload.get("step_id") or ""),
            role=str(payload.get("role") or ""),
            status=str(payload.get("status") or "pending"),
            started_at=str(payload.get("started_at") or ""),
            completed_at=str(payload["completed_at"]) if payload.get("completed_at") else None,
            duration_ms=duration_ms,
            agent_input=agent_input,
            agent_output=agent_output,
            notes=tuple(str(n) for n in payload.get("notes", []) if isinstance(n, str)),
        )

    def with_status(
        self,
        status: str,
        *,
        completed_at: str | None = None,
        duration_ms: int | None = None,
        agent_output: AgentOutput | None = None,
        notes: tuple[str, ...] | None = None,
    ) -> "ForgeLedgerEntry":
        """Return a copy with selected fields replaced.

        Frozen dataclasses are immutable, so updates are by replacement.
        Used by :meth:`ForgeLedger.update_step` to record status
        transitions (pending → running → succeeded/failed/blocked) without
        mutating the original record.
        """
        if status not in FORGE_STEP_STATUSES:
            raise ValueError(
                f"Unknown forge step status: {status!r}. "
                f"Valid: {', '.join(FORGE_STEP_STATUSES)}"
            )
        return ForgeLedgerEntry(
            workflow_id=self.workflow_id,
            step_id=self.step_id,
            role=self.role,
            status=status,
            started_at=self.started_at,
            agent_input=self.agent_input,
            completed_at=completed_at if completed_at is not None else self.completed_at,
            duration_ms=duration_ms if duration_ms is not None else self.duration_ms,
            agent_output=agent_output if agent_output is not None else self.agent_output,
            notes=notes if notes is not None else self.notes,
        )


@dataclass
class ForgeLedger:
    """Per-project handle to ``mythic/forge_ledger.json``.

    Keeps no in-memory state beyond the project root — every read
    re-loads from disk so concurrent forge runs see each other's
    writes. Writes are atomic per-path through ``file_mutation_queue``
    (Pi-derived primitive); the ledger file itself is rewritten in
    full each time, capped at :data:`FORGE_LEDGER_LIMIT` entries.
    """

    root: Path

    @property
    def path(self) -> Path:
        return self.root / "mythic" / FORGE_LEDGER_FILENAME

    def load(self) -> list[ForgeLedgerEntry]:
        """Read and parse the ledger. Empty list on missing file or
        malformed JSON — defensive by design so a corrupt ledger never
        blocks a forge run."""
        target = self.path
        if not target.exists():
            return []
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, dict):
            return []
        entries_payload = payload.get("entries", [])
        if not isinstance(entries_payload, list):
            return []
        out: list[ForgeLedgerEntry] = []
        for item in entries_payload:
            if not isinstance(item, dict):
                continue
            try:
                out.append(ForgeLedgerEntry.from_dict(item))
            except ValueError:
                # Skip malformed rows but keep the others; never crash
                # the loader on one bad row.
                continue
        return out

    def append(self, entry: ForgeLedgerEntry) -> ForgeLedgerEntry:
        """Append ``entry`` to the ledger and rotate to keep the file
        bounded at :data:`FORGE_LEDGER_LIMIT`."""
        target = self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        with file_mutation_queue(target):
            entries = self.load()
            entries.append(entry)
            if len(entries) > FORGE_LEDGER_LIMIT:
                entries = entries[-FORGE_LEDGER_LIMIT:]
            self._write_entries(target, entries)
        return entry

    def update_step(
        self,
        workflow_id: str,
        step_id: str,
        *,
        status: str,
        completed_at: str | None = None,
        duration_ms: int | None = None,
        agent_output: AgentOutput | None = None,
        notes: tuple[str, ...] | None = None,
    ) -> ForgeLedgerEntry:
        """Replace the latest entry matching ``(workflow_id, step_id)`` with
        a new entry carrying the supplied status / timing / output.

        Raises :class:`ValueError` if no matching entry exists.
        """
        target = self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        with file_mutation_queue(target):
            entries = self.load()
            for index in range(len(entries) - 1, -1, -1):
                candidate = entries[index]
                if candidate.workflow_id == workflow_id and candidate.step_id == step_id:
                    updated = candidate.with_status(
                        status,
                        completed_at=completed_at,
                        duration_ms=duration_ms,
                        agent_output=agent_output,
                        notes=notes,
                    )
                    entries[index] = updated
                    self._write_entries(target, entries)
                    return updated
            raise ValueError(
                f"No forge ledger entry found for workflow_id={workflow_id!r} "
                f"step_id={step_id!r}"
            )

    def latest(self, *, limit: int = 20) -> list[ForgeLedgerEntry]:
        """Return up to ``limit`` most recent entries (newest last)."""
        entries = self.load()
        if limit <= 0:
            return []
        return entries[-limit:]

    def find_by_workflow(self, workflow_id: str) -> list[ForgeLedgerEntry]:
        """Return every entry for ``workflow_id`` in append order."""
        return [e for e in self.load() if e.workflow_id == workflow_id]

    def find_step(self, workflow_id: str, step_id: str) -> ForgeLedgerEntry | None:
        """Return the most recent entry for ``(workflow_id, step_id)`` or None."""
        entries = self.load()
        for entry in reversed(entries):
            if entry.workflow_id == workflow_id and entry.step_id == step_id:
                return entry
        return None

    @staticmethod
    def _write_entries(target: Path, entries: list[ForgeLedgerEntry]) -> None:
        payload = {
            "version": FORGE_LEDGER_SCHEMA_VERSION,
            "entries": [entry.to_dict() for entry in entries],
        }
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "FORGE_LEDGER_FILENAME",
    "FORGE_LEDGER_LIMIT",
    "FORGE_LEDGER_SCHEMA_VERSION",
    "FORGE_STEP_STATUSES",
    "ForgeLedger",
    "ForgeLedgerEntry",
]
