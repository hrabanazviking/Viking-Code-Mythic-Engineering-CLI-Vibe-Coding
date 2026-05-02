"""Per-cycle forge reflection artefact (PH-03 slice 3.7).

After a forge run completes — success, failure, or operator abort —
the orchestrator writes a structured reflection summarising what the
cycle did. The reflection is the Scribe's permanent contribution to
project memory: future operators reading
``mythic/reflections/<workflow_id>.md`` should be able to reconstruct
what happened, what failed, and what to do next without trawling
the per-step ledger.

Two artefacts per workflow:

- ``mythic/reflections/<workflow_id>.md`` — human-readable rendering
  for ``cat`` / editors / docs sites.
- ``mythic/reflections/<workflow_id>.json`` — round-trippable
  structured data for programmatic reads (``forge reflection show``,
  future TUI panels, drift detection in PH-13).

Both files contain the same information; the markdown is generated
from the JSON via :func:`render_forge_reflection_markdown` so the
two cannot drift.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .core.state import utc_now
from .forge_ledger import ForgeLedger, ForgeLedgerEntry
from .runtime.file_mutation_queue import file_mutation_queue
from .workflow_engine import WorkflowPlan


REFLECTIONS_DIRNAME = "reflections"
REFLECTION_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ForgeStepReflection:
    """One step's contribution to the reflection.

    ``summary`` is the AgentOutput.summary if the provider responded
    (slice 3.5); empty string otherwise. ``failed_gates`` only carries
    entries for the Auditor when slice-3.6 verifier gates failed;
    empty for every other step.
    """

    step_id: str
    role: str
    phase: str
    status: str
    summary: str = ""
    failed_gates: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    duration_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "role": self.role,
            "phase": self.phase,
            "status": self.status,
            "summary": self.summary,
            "failed_gates": list(self.failed_gates),
            "notes": list(self.notes),
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ForgeStepReflection":
        duration_raw = payload.get("duration_ms")
        try:
            duration = int(duration_raw) if duration_raw is not None else None
        except (TypeError, ValueError):
            duration = None
        return cls(
            step_id=str(payload.get("step_id") or ""),
            role=str(payload.get("role") or ""),
            phase=str(payload.get("phase") or ""),
            status=str(payload.get("status") or "unknown"),
            summary=str(payload.get("summary") or ""),
            failed_gates=tuple(
                str(g) for g in payload.get("failed_gates", []) if isinstance(g, str)
            ),
            notes=tuple(str(n) for n in payload.get("notes", []) if isinstance(n, str)),
            duration_ms=duration,
        )


@dataclass(frozen=True)
class ForgeReflection:
    """Aggregate reflection for one forge run."""

    schema_version: int
    workflow_id: str
    task: str
    created_at: str
    completed_at: str
    final_status: str  # "success" | "failure" | "aborted" | "no-steps"
    success_count: int
    failure_count: int
    blocked_count: int
    aborted: bool
    steps: tuple[ForgeStepReflection, ...]
    next_step_recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "workflow_id": self.workflow_id,
            "task": self.task,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "final_status": self.final_status,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "blocked_count": self.blocked_count,
            "aborted": self.aborted,
            "steps": [step.to_dict() for step in self.steps],
            "next_step_recommendation": self.next_step_recommendation,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ForgeReflection":
        steps_payload = payload.get("steps", [])
        steps = tuple(
            ForgeStepReflection.from_dict(item)
            for item in steps_payload
            if isinstance(item, dict)
        )
        return cls(
            schema_version=int(payload.get("schema_version") or REFLECTION_SCHEMA_VERSION),
            workflow_id=str(payload.get("workflow_id") or ""),
            task=str(payload.get("task") or ""),
            created_at=str(payload.get("created_at") or ""),
            completed_at=str(payload.get("completed_at") or ""),
            final_status=str(payload.get("final_status") or "unknown"),
            success_count=int(payload.get("success_count") or 0),
            failure_count=int(payload.get("failure_count") or 0),
            blocked_count=int(payload.get("blocked_count") or 0),
            aborted=bool(payload.get("aborted", False)),
            steps=steps,
            next_step_recommendation=str(payload.get("next_step_recommendation") or ""),
        )


# ---- Build from ledger --------------------------------------------------


def _failed_gates_from_entry(entry: ForgeLedgerEntry) -> tuple[str, ...]:
    """Extract the names of any failed verification gates from the
    Auditor's AgentOutput. Returns empty tuple for non-Auditor entries
    or when no verification results were recorded."""
    if entry.role != "Auditor" or entry.agent_output is None:
        return ()
    return tuple(
        result.name
        for result in entry.agent_output.verification_results
        if not result.passed
    )


def _step_reflection_from_entry(entry: ForgeLedgerEntry, *, phase: str) -> ForgeStepReflection:
    summary = entry.agent_output.summary if entry.agent_output is not None else ""
    return ForgeStepReflection(
        step_id=entry.step_id,
        role=entry.role,
        phase=phase,
        status=entry.status,
        summary=summary,
        failed_gates=_failed_gates_from_entry(entry),
        notes=entry.notes,
        duration_ms=entry.duration_ms,
    )


def _next_step_recommendation(
    final_status: str,
    aborted: bool,
    failed_step_id: str | None,
    failed_role: str | None,
) -> str:
    if aborted:
        marker = f" after {failed_step_id} ({failed_role})" if failed_step_id else ""
        return (
            f"Run aborted at gate{marker}. Address the operator's concerns "
            "and rerun with `mythic-vibe forge run`."
        )
    if final_status == "failure":
        marker = f"{failed_step_id} ({failed_role})" if failed_step_id else "an unknown step"
        return (
            f"Step {marker} failed. Review the notes in "
            "`mythic/forge_ledger.json` and rerun with `forge resume` "
            "(slice 3.8) once the failure is addressed."
        )
    if final_status == "no-steps":
        return "No steps were recorded. Check the workflow plan and rerun."
    return (
        "Cycle completed with every step succeeded. Review the per-agent "
        "artefacts and start the next forge cycle when ready."
    )


def build_forge_reflection(
    plan: WorkflowPlan,
    ledger: ForgeLedger,
    *,
    aborted: bool = False,
    completed_at: str | None = None,
) -> ForgeReflection:
    """Build a :class:`ForgeReflection` by reading every entry for
    ``plan.workflow_id`` from ``ledger`` (the most-recent entry wins
    when a step appears multiple times — e.g. running → succeeded
    transitions go through ``ledger.update_step``).

    Counts are computed from the resolved per-step statuses, not from
    raw entry counts, so the reflection reports what the orchestrator
    decided rather than the wire-level transitions.
    """
    workflow_id = plan.workflow_id or ""
    phase_by_step = {step.step_id: step.phase for step in plan.steps}

    # Resolve to most-recent entry per (workflow_id, step_id).
    resolved: dict[str, ForgeLedgerEntry] = {}
    for entry in ledger.find_by_workflow(workflow_id):
        resolved[entry.step_id] = entry

    steps: list[ForgeStepReflection] = []
    success_count = 0
    failure_count = 0
    blocked_count = 0
    failed_step_id: str | None = None
    failed_role: str | None = None

    for plan_step in plan.steps:
        entry = resolved.get(plan_step.step_id)
        if entry is None:
            # No ledger entry — treat as blocked-no-record.
            steps.append(
                ForgeStepReflection(
                    step_id=plan_step.step_id,
                    role=plan_step.role,
                    phase=plan_step.phase,
                    status="not-run",
                    notes=("no ledger entry recorded for this step",),
                )
            )
            blocked_count += 1
            continue

        phase = phase_by_step.get(plan_step.step_id, plan_step.phase)
        step_reflection = _step_reflection_from_entry(entry, phase=phase)
        steps.append(step_reflection)
        if step_reflection.status == "succeeded":
            success_count += 1
        elif step_reflection.status == "failed":
            failure_count += 1
            if failed_step_id is None:
                failed_step_id = step_reflection.step_id
                failed_role = step_reflection.role
        elif step_reflection.status == "blocked":
            blocked_count += 1

    if not steps:
        final_status = "no-steps"
    elif aborted:
        final_status = "aborted"
    elif failure_count > 0:
        final_status = "failure"
    else:
        final_status = "success"

    return ForgeReflection(
        schema_version=REFLECTION_SCHEMA_VERSION,
        workflow_id=workflow_id,
        task=plan.task,
        created_at=plan.created_at,
        completed_at=completed_at or utc_now(),
        final_status=final_status,
        success_count=success_count,
        failure_count=failure_count,
        blocked_count=blocked_count,
        aborted=aborted,
        steps=tuple(steps),
        next_step_recommendation=_next_step_recommendation(
            final_status, aborted, failed_step_id, failed_role
        ),
    )


# ---- Markdown rendering -------------------------------------------------


def render_forge_reflection_markdown(reflection: ForgeReflection) -> str:
    """Render a :class:`ForgeReflection` as Markdown.

    Mirror of the JSON shape; if the operator only ever reads the
    markdown they should still be able to reconstruct every relevant
    detail of the run.
    """
    lines: list[str] = [
        "# Forge Reflection",
        "",
        f"- Workflow: {reflection.workflow_id or '(no id)'}",
        f"- Task: {reflection.task}",
        f"- Created at: {reflection.created_at}",
        f"- Completed at: {reflection.completed_at}",
        f"- Final status: **{reflection.final_status}**",
        f"- Steps: {len(reflection.steps)} "
        f"(succeeded={reflection.success_count}, "
        f"failed={reflection.failure_count}, "
        f"blocked={reflection.blocked_count})",
    ]
    if reflection.aborted:
        lines.append("- Aborted: yes (operator declined a gate)")

    lines.extend(
        [
            "",
            "## Per-role outcomes",
            "",
        ]
    )

    for step in reflection.steps:
        lines.append(f"### {step.step_id} :: {step.role} ({step.phase}) — {step.status}")
        if step.summary:
            lines.append("")
            lines.append(f"> {step.summary}")
        if step.duration_ms is not None:
            lines.append("")
            lines.append(f"- Duration: {step.duration_ms} ms")
        if step.failed_gates:
            lines.append("")
            lines.append("- Failed gates:")
            for gate in step.failed_gates:
                lines.append(f"  - {gate}")
        if step.notes:
            lines.append("")
            lines.append("- Notes:")
            for note in step.notes:
                lines.append(f"  - {note}")
        lines.append("")

    lines.extend(
        [
            "## Next step",
            "",
            reflection.next_step_recommendation,
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


# ---- Persistence --------------------------------------------------------


def reflection_dir(root: Path) -> Path:
    return root / "mythic" / REFLECTIONS_DIRNAME


def reflection_paths(root: Path, workflow_id: str) -> tuple[Path, Path]:
    """Return ``(json_path, markdown_path)`` for the given workflow id."""
    base = reflection_dir(root)
    safe_id = workflow_id or "no-workflow-id"
    return base / f"{safe_id}.json", base / f"{safe_id}.md"


def write_forge_reflection(root: Path, reflection: ForgeReflection) -> tuple[Path, Path]:
    """Atomically write both the JSON and markdown reflection files.

    Returns ``(json_path, markdown_path)``. Both writes go through
    ``file_mutation_queue`` so concurrent forge runs don't trample
    each other.
    """
    # Phase 19.0 / L-10 (additive 2026-05-02 audit remediation):
    # route reflection writes through atomic_write_text so a kill
    # mid-write doesn't truncate the JSON sidecar or markdown
    # report. See runtime/atomic_write.py for rationale.
    from .runtime.atomic_write import atomic_write_text

    json_path, md_path = reflection_paths(root, reflection.workflow_id)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(reflection.to_dict(), indent=2) + "\n"
    rendered = render_forge_reflection_markdown(reflection)

    with file_mutation_queue(json_path):
        atomic_write_text(json_path, payload)
    with file_mutation_queue(md_path):
        atomic_write_text(md_path, rendered)
    return json_path, md_path


def load_forge_reflection(root: Path, workflow_id: str) -> ForgeReflection | None:
    """Read the JSON sidecar for ``workflow_id``. Returns ``None`` if
    the file is missing or malformed (defensive — never crashes the
    caller)."""
    json_path, _ = reflection_paths(root, workflow_id)
    if not json_path.exists():
        return None
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return ForgeReflection.from_dict(payload)
    except (TypeError, ValueError):
        return None


def list_forge_reflections(root: Path) -> list[str]:
    """Return the workflow ids of every reflection on disk, sorted by
    file mtime (oldest first → newest last)."""
    base = reflection_dir(root)
    if not base.exists():
        return []
    json_files = sorted(base.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return [path.stem for path in json_files]


__all__ = [
    "REFLECTIONS_DIRNAME",
    "REFLECTION_SCHEMA_VERSION",
    "ForgeReflection",
    "ForgeStepReflection",
    "build_forge_reflection",
    "list_forge_reflections",
    "load_forge_reflection",
    "reflection_dir",
    "reflection_paths",
    "render_forge_reflection_markdown",
    "write_forge_reflection",
]
