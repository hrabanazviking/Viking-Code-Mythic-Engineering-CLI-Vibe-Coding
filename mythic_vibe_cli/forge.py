"""Forge command — multi-agent workflow orchestrator (PH-03 slice 3.3).

This slice ships the **dry-run** half of the forge command. No
provider is invoked, no agent actually runs. The command:

1. Builds a :class:`mythic_vibe_cli.workflow_engine.WorkflowPlan` via
   the existing engine.
2. Materialises one :class:`mythic_vibe_cli.workflow_agents.AgentInput`
   per step from the slice-3.1 contracts.
3. Validates each input against its contract; failures are recorded
   (status=``blocked``) but do not crash the run.
4. Writes one ``pending`` :class:`mythic_vibe_cli.forge_ledger.ForgeLedgerEntry`
   per step (skippable with ``--skip-ledger``).
5. Renders a per-agent packet for each step — markdown that an
   operator can paste into ChatGPT / Claude / Gemini, or that a
   future provider-backed slice (3.5) will route directly.

The ``ledger`` subcommand is the inspection counterpart for the
new ``mythic/forge_ledger.json``, mirroring the existing
``mythic-vibe workflow history`` reader for the per-plan ledger.

Slice 3.4 adds approval gates between steps; slice 3.5 makes
``forge run`` actually execute via providers; slice 3.8 adds
``forge resume`` to pick up a partially completed cycle.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Callable, Literal

from .core.state import utc_now
from .errors import CliError, format_error
from .exit_codes import SUCCESS, UNSAFE_OPERATION_BLOCKED, USER_INPUT_ERROR
from .forge_ledger import ForgeLedger, ForgeLedgerEntry
from .output import write_bullet, write_error, write_json, write_key_value, write_line
from .workflow_agents import (
    AGENT_CONTRACTS,
    AgentInput,
    contract_for,
    validate_input,
)
from .workflow_engine import (
    DEFAULT_ROLE_SEQUENCE,
    WorkflowEngine,
    WorkflowPlan,
    WorkflowStep,
)


# ---- Gate machinery (PH-03 slice 3.4) -----------------------------------

GateDecision = Literal["advance", "abort", "skip"]


@dataclass(frozen=True)
class ForgeGateContext:
    """Snapshot passed to a gate handler after each forge step.

    The handler decides whether the orchestrator advances to the
    next step, aborts the run, or skips the next step. Frozen so a
    handler cannot mutate it; round-trippable to dict for tests
    that record gate calls.
    """

    workflow_id: str
    completed_step_index: int
    completed_step_id: str
    completed_role: str
    completed_status: str
    completed_validation_errors: tuple[str, ...]
    next_step_id: str | None
    next_role: str | None
    total_steps: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "completed_step_index": self.completed_step_index,
            "completed_step_id": self.completed_step_id,
            "completed_role": self.completed_role,
            "completed_status": self.completed_status,
            "completed_validation_errors": list(self.completed_validation_errors),
            "next_step_id": self.next_step_id,
            "next_role": self.next_role,
            "total_steps": self.total_steps,
        }


GateHandler = Callable[[ForgeGateContext], GateDecision]


def _describe_gate_context(context: ForgeGateContext) -> str:
    """Detail string shown when the operator types ``?`` at a gate."""
    lines = [
        "",
        "  --- Gate detail ---",
        f"  Workflow:        {context.workflow_id}",
        f"  Completed step:  {context.completed_step_id} ({context.completed_role})",
        f"  Status:          {context.completed_status}",
    ]
    if context.completed_validation_errors:
        lines.append("  Validation:")
        for err in context.completed_validation_errors:
            lines.append(f"    - {err}")
    if context.next_step_id:
        lines.append(f"  Next step:       {context.next_step_id} ({context.next_role})")
    else:
        lines.append("  Next step:       (end of cycle)")
    lines.append(f"  Position:        {context.completed_step_index + 1} / {context.total_steps}")
    lines.append("")
    return "\n".join(lines)


def default_gate_handler(context: ForgeGateContext) -> GateDecision:
    """Stdin-driven gate handler.

    Prompts ``[y/n/?/s]`` after each step; returns one of
    :data:`GateDecision`. ``?`` prints detail and re-prompts; empty
    input defaults to ``y`` (advance) so a Ctrl+D-driven approval
    flow works without typing.

    Tests inject their own handler via ``cmd_forge_plan(args,
    gate_handler=...)`` and never go through this path.
    """
    while True:
        next_label = (
            f"step {context.completed_step_index + 2}/{context.total_steps} "
            f"({context.next_role})"
            if context.next_step_id
            else "(end of cycle)"
        )
        prompt = (
            f"\n[gate] step {context.completed_step_index + 1}/{context.total_steps} "
            f"{context.completed_role} -> {next_label}\n"
            f"  status: {context.completed_status}\n"
            "  Advance? [y/n/?/s] "
        )
        try:
            response = input(prompt)
        except EOFError:
            # No more input — treat EOF as advance (the safe default
            # for piped/non-interactive runs).
            return "advance"
        normalised = response.strip().lower()
        if normalised in {"y", "yes", ""}:
            return "advance"
        if normalised in {"n", "no", "abort"}:
            return "abort"
        if normalised in {"s", "skip"}:
            return "skip"
        if normalised == "?":
            sys.stdout.write(_describe_gate_context(context))
            sys.stdout.flush()
            continue
        sys.stdout.write(f"Unknown response {response.rstrip()!r}. Try y/n/?/s.\n")
        sys.stdout.flush()


# ---- Helpers -------------------------------------------------------------


def _flag(args: argparse.Namespace, name: str) -> bool:
    return bool(getattr(args, name, False))


def materialize_agent_input(plan: WorkflowPlan, step: WorkflowStep) -> AgentInput:
    """Build the typed :class:`AgentInput` for one step in ``plan``.

    Slice 3.3 dry-run builds a minimum-viable input: role / task /
    phase plus the workflow identity. ``prior_outputs`` is left
    empty in dry-run; slice 3.5 will populate it from the ledger
    when a previous agent has actually completed.
    """
    contract = AGENT_CONTRACTS.get(step.role)
    invariants: tuple[str, ...] = step.invariants
    if contract is not None:
        # Surface contract-required gate names alongside the prose
        # invariants so the rendered packet shows operators what will
        # be checked.
        invariants = invariants + tuple(
            f"GATE: {gate}" for gate in contract.verification_gate
        )
    return AgentInput(
        role=step.role,
        task=plan.task,
        phase=step.phase,
        workflow_id=plan.workflow_id,
        workflow_step_id=step.step_id or None,
        prior_outputs=(),
        context_files=(),
        forbidden_files=(),
        invariants=invariants,
        notes=(step.objective,) if step.objective else (),
    )


def render_forge_packet(
    plan: WorkflowPlan,
    step: WorkflowStep,
    agent_input: AgentInput,
) -> str:
    """Render one step's packet as Mythic-style Markdown.

    The shape mirrors :data:`mythic_vibe_cli.codex_bridge.PACKET_OUTPUT_FORMATS`'
    canonical structure (Role / Intent / Context / Files / Verification)
    so a future provider-backed run can reuse the same renderer.
    """
    contract = AGENT_CONTRACTS.get(step.role)
    next_role = step.handoff_to or "(end of cycle)"

    lines: list[str] = [
        "# Mythic Forge Packet",
        "",
        f"- Workflow: {plan.workflow_id or '(no id)'}",
        f"- Step: {step.step_id} ({step.role} — {step.phase})",
        f"- Task: {plan.task}",
        f"- Hand off to: {next_role}",
        "",
        "## 1. Role",
        "",
        f"- Identity: {step.identity}",
        f"- Focus: {step.focus}",
        "",
        "## 2. System prompt",
        "",
        step.system_prompt,
        "",
        "## 3. Step objective",
        "",
        step.objective,
        "",
        "## 4. Invariants",
        "",
    ]

    if agent_input.invariants:
        for invariant in agent_input.invariants:
            lines.append(f"- {invariant}")
    else:
        lines.append("(none recorded)")
    lines.append("")

    lines.append("## 5. Verification (gates that must pass to advance)")
    lines.append("")
    if step.verification:
        for check in step.verification:
            lines.append(f"- {check}")
    if contract is not None:
        for gate in contract.verification_gate:
            lines.append(f"- GATE: {gate}")
    if not step.verification and (contract is None or not contract.verification_gate):
        lines.append("(none recorded)")
    lines.append("")

    lines.append("## 6. Expected output artefacts")
    lines.append("")
    if contract is not None and contract.output_artefact_kinds:
        for kind in contract.output_artefact_kinds:
            lines.append(f"- {kind}")
    else:
        lines.append("(no contract — see role notes)")
    lines.append("")

    lines.append("## 7. AgentInput payload")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(agent_input.to_dict(), indent=2))
    lines.append("```")

    return "\n".join(lines).rstrip() + "\n"


# ---- forge plan ----------------------------------------------------------


def _record_aborted_step(
    *,
    plan: WorkflowPlan,
    step: WorkflowStep,
    started_at: str,
    note: str,
    skip_ledger: bool,
    ledger: ForgeLedger,
) -> dict[str, Any]:
    """Materialise + write a ``blocked`` entry for an unprocessed step
    when the operator aborts at a gate or skips the next step.

    Returns the step payload dict so the caller's report can include
    the aborted/skipped step alongside the processed ones.
    """
    agent_input = materialize_agent_input(plan, step)
    if not skip_ledger:
        entry = ForgeLedgerEntry(
            workflow_id=plan.workflow_id or "",
            step_id=step.step_id,
            role=step.role,
            status="blocked",
            started_at=started_at,
            agent_input=agent_input,
            notes=(note,),
        )
        ledger.append(entry)
    return {
        "step_id": step.step_id,
        "role": step.role,
        "phase": step.phase,
        "objective": step.objective,
        "handoff_to": step.handoff_to,
        "agent_input": agent_input.to_dict(),
        "validation_errors": [],
        "status": "blocked",
        "blocked_reason": note,
    }


def cmd_forge_plan(
    args: argparse.Namespace,
    *,
    gate_handler: GateHandler | None = None,
) -> int:
    """``mythic-vibe forge plan`` — dry-run forge orchestration.

    Builds the plan, materialises every per-agent input, writes one
    pending ledger entry per step (unless ``--skip-ledger``), renders
    every per-agent packet, and prints the result. No provider runs.

    With ``--interactive``, calls ``gate_handler`` (default:
    :func:`default_gate_handler`) between each pair of steps. The
    handler returns a :data:`GateDecision`:

    - ``advance`` — proceed to the next step
    - ``abort`` — stop the run; remaining steps are written as
      ``blocked`` ledger entries with note ``"operator aborted at gate"``
    - ``skip`` — write the next step as ``blocked`` with note
      ``"operator skipped"`` then continue to the step after that

    Returns ``USER_INPUT_ERROR`` if ``--task`` is missing or blank,
    ``UNSAFE_OPERATION_BLOCKED`` if non-dry-run mode is requested
    (slice 3.5 lifts that gate), or ``SUCCESS``.
    """
    root = Path(getattr(args, "path", ".")).resolve()
    task = (getattr(args, "task", "") or "").strip()
    if not task:
        write_error("forge plan requires --task <text>.")
        return USER_INPUT_ERROR

    if not _flag(args, "dry_run"):
        write_error(
            "Provider-backed forge is not enabled yet. "
            "Re-run with `--dry-run` to preview the role sequence and packets."
        )
        return UNSAFE_OPERATION_BLOCKED

    engine = WorkflowEngine(root)
    try:
        plan = engine.build_plan(task, role_sequence=DEFAULT_ROLE_SEQUENCE)
    except ValueError as exc:
        write_error(format_error(CliError(f"Workflow plan build failed: {exc}")))
        return USER_INPUT_ERROR

    skip_ledger = _flag(args, "skip_ledger")
    interactive = _flag(args, "interactive")
    handler: GateHandler = gate_handler or default_gate_handler
    ledger = ForgeLedger(root=root)

    step_payloads: list[dict[str, Any]] = []
    started_at = utc_now()
    aborted = False
    skip_next_step = False

    total = len(plan.steps)
    for index, step in enumerate(plan.steps):
        if skip_next_step:
            skip_next_step = False
            payload = _record_aborted_step(
                plan=plan,
                step=step,
                started_at=started_at,
                note="operator skipped at preceding gate",
                skip_ledger=skip_ledger,
                ledger=ledger,
            )
            step_payloads.append(payload)
            continue

        agent_input = materialize_agent_input(plan, step)
        contract = contract_for(step.role)
        validation_errors = validate_input(agent_input, contract)
        status = "blocked" if validation_errors else "pending"

        if not skip_ledger:
            entry = ForgeLedgerEntry(
                workflow_id=plan.workflow_id or "",
                step_id=step.step_id,
                role=step.role,
                status=status,
                started_at=started_at,
                agent_input=agent_input,
                notes=tuple(validation_errors),
            )
            ledger.append(entry)

        packet_text = render_forge_packet(plan, step, agent_input)

        step_payloads.append(
            {
                "step_id": step.step_id,
                "role": step.role,
                "phase": step.phase,
                "objective": step.objective,
                "handoff_to": step.handoff_to,
                "agent_input": agent_input.to_dict(),
                "validation_errors": list(validation_errors),
                "status": status,
                "packet": packet_text,
            }
        )

        # Gate after this step before advancing — but never after the
        # final step (no next step to gate).
        if interactive and index + 1 < total:
            next_step = plan.steps[index + 1]
            context = ForgeGateContext(
                workflow_id=plan.workflow_id or "",
                completed_step_index=index,
                completed_step_id=step.step_id,
                completed_role=step.role,
                completed_status=status,
                completed_validation_errors=tuple(validation_errors),
                next_step_id=next_step.step_id,
                next_role=next_step.role,
                total_steps=total,
            )
            decision = handler(context)
            if decision == "abort":
                aborted = True
                # Mark every remaining step as blocked.
                for remaining in plan.steps[index + 1 :]:
                    payload = _record_aborted_step(
                        plan=plan,
                        step=remaining,
                        started_at=started_at,
                        note="operator aborted at gate",
                        skip_ledger=skip_ledger,
                        ledger=ledger,
                    )
                    step_payloads.append(payload)
                break
            if decision == "skip":
                skip_next_step = True
            # decision == "advance" → fall through

    if _flag(args, "json"):
        write_json(
            {
                "command": "forge plan",
                "dry_run": True,
                "skip_ledger": skip_ledger,
                "interactive": interactive,
                "aborted": aborted,
                "workflow_id": plan.workflow_id,
                "task": plan.task,
                "created_at": plan.created_at,
                "ledger_path": str(ledger.path) if not skip_ledger else None,
                "role_sequence": list(DEFAULT_ROLE_SEQUENCE),
                "steps": step_payloads,
            }
        )
        return SUCCESS

    write_line("Mythic forge plan (dry-run)")
    write_key_value("Workflow", plan.workflow_id or "(no id)")
    write_key_value("Task", plan.task)
    write_key_value("Created at", plan.created_at)
    write_key_value("Steps", len(plan.steps))
    if interactive:
        write_key_value("Interactive", "yes")
    if aborted:
        write_key_value("Aborted", "yes (operator declined a gate)")
    if not skip_ledger:
        write_key_value("Ledger", ledger.path)
    write_line("")

    for payload in step_payloads:
        write_line(f"- {payload['step_id']} :: {payload['role']} ({payload['phase']}) -> {payload['handoff_to'] or 'end'}")
        write_bullet(f"objective: {payload['objective']}", indent=2)
        write_bullet(f"status: {payload['status']}", indent=2)
        if payload["validation_errors"]:
            write_bullet("validation errors:", indent=2)
            for err in payload["validation_errors"]:
                write_bullet(err, indent=4)
        if payload.get("blocked_reason"):
            write_bullet(f"blocked: {payload['blocked_reason']}", indent=2)
    write_line("")

    rendered = [p for p in step_payloads if "packet" in p]
    if rendered:
        write_line("--- Per-agent packets ---")
        write_line("")
        for payload in rendered:
            write_line(f"### {payload['step_id']} :: {payload['role']}")
            write_line("")
            write_line(payload["packet"], force=True)

    return SUCCESS


# ---- forge ledger --------------------------------------------------------


def _entry_summary(entry: ForgeLedgerEntry) -> dict[str, Any]:
    return {
        "workflow_id": entry.workflow_id,
        "step_id": entry.step_id,
        "role": entry.role,
        "status": entry.status,
        "started_at": entry.started_at,
        "completed_at": entry.completed_at,
        "duration_ms": entry.duration_ms,
        "notes": list(entry.notes),
    }


def cmd_forge_ledger_list(args: argparse.Namespace) -> int:
    """``mythic-vibe forge ledger list`` — every recorded entry, oldest first."""
    root = Path(getattr(args, "path", ".")).resolve()
    ledger = ForgeLedger(root=root)
    entries = ledger.load()

    if _flag(args, "json"):
        write_json(
            {
                "command": "forge ledger list",
                "ledger_path": str(ledger.path),
                "count": len(entries),
                "entries": [_entry_summary(e) for e in entries],
            }
        )
        return SUCCESS

    if not entries:
        write_line("Forge ledger is empty.")
        write_key_value("Path", ledger.path)
        return SUCCESS

    write_line(f"Forge ledger ({len(entries)} entries)")
    write_key_value("Path", ledger.path)
    write_line("")
    for entry in entries:
        write_bullet(
            f"{entry.workflow_id} :: {entry.step_id} :: {entry.role} :: {entry.status}",
            indent=2,
        )
    return SUCCESS


def cmd_forge_ledger_latest(args: argparse.Namespace) -> int:
    """``mythic-vibe forge ledger latest`` — most recent N entries."""
    root = Path(getattr(args, "path", ".")).resolve()
    ledger = ForgeLedger(root=root)
    limit = int(getattr(args, "limit", 5) or 5)
    entries = ledger.latest(limit=limit)

    if _flag(args, "json"):
        write_json(
            {
                "command": "forge ledger latest",
                "ledger_path": str(ledger.path),
                "limit": limit,
                "count": len(entries),
                "entries": [_entry_summary(e) for e in entries],
            }
        )
        return SUCCESS

    if not entries:
        write_line(f"No entries within the latest {limit} window.")
        return SUCCESS

    write_line(f"Forge ledger — latest {len(entries)} of {limit} requested")
    for entry in entries:
        write_bullet(
            f"{entry.workflow_id} :: {entry.step_id} :: {entry.role} :: {entry.status}",
            indent=2,
        )
    return SUCCESS


def cmd_forge_ledger_show(args: argparse.Namespace) -> int:
    """``mythic-vibe forge ledger show`` — entries for one workflow,
    optionally filtered to a single step."""
    root = Path(getattr(args, "path", ".")).resolve()
    workflow_id = (getattr(args, "workflow", "") or "").strip()
    step_id = (getattr(args, "step", "") or "").strip()

    if not workflow_id:
        write_error("forge ledger show requires --workflow <id>.")
        return USER_INPUT_ERROR

    ledger = ForgeLedger(root=root)
    matches = ledger.find_by_workflow(workflow_id)
    if step_id:
        matches = [e for e in matches if e.step_id == step_id]

    if not matches:
        message = f"No ledger entries match workflow={workflow_id!r}"
        if step_id:
            message += f" step={step_id!r}"
        if _flag(args, "json"):
            write_json(
                {
                    "command": "forge ledger show",
                    "ledger_path": str(ledger.path),
                    "workflow_id": workflow_id,
                    "step_id": step_id or None,
                    "count": 0,
                    "errors": [message],
                }
            )
        else:
            write_error(message)
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        write_json(
            {
                "command": "forge ledger show",
                "ledger_path": str(ledger.path),
                "workflow_id": workflow_id,
                "step_id": step_id or None,
                "count": len(matches),
                "entries": [entry.to_dict() for entry in matches],
            }
        )
        return SUCCESS

    write_line(f"Forge ledger — workflow {workflow_id}")
    if step_id:
        write_key_value("Step filter", step_id)
    write_line("")
    for entry in matches:
        write_line(f"## {entry.step_id} :: {entry.role}")
        write_bullet(f"status: {entry.status}", indent=2)
        write_bullet(f"started_at: {entry.started_at}", indent=2)
        if entry.completed_at:
            write_bullet(f"completed_at: {entry.completed_at}", indent=2)
        if entry.duration_ms is not None:
            write_bullet(f"duration_ms: {entry.duration_ms}", indent=2)
        if entry.notes:
            write_bullet("notes:", indent=2)
            for note in entry.notes:
                write_bullet(note, indent=4)
        write_line("")
    return SUCCESS


# ---- Dispatcher ---------------------------------------------------------


def cmd_forge_ledger_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "ledger_command", None)
    if sub == "list":
        return cmd_forge_ledger_list(args)
    if sub == "latest":
        return cmd_forge_ledger_latest(args)
    if sub == "show":
        return cmd_forge_ledger_show(args)
    write_error(
        f"Unknown forge ledger subcommand: {sub!r}. "
        "Try `mythic-vibe forge ledger list`, `latest`, or `show --workflow <id>`."
    )
    return USER_INPUT_ERROR


def cmd_forge_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "forge_command", None)
    if sub == "plan":
        return cmd_forge_plan(args)
    if sub == "ledger":
        return cmd_forge_ledger_dispatch(args)
    write_error(
        f"Unknown forge subcommand: {sub!r}. "
        "Try `mythic-vibe forge plan --dry-run --task <X>` or `mythic-vibe forge ledger list`."
    )
    return USER_INPUT_ERROR


__all__ = [
    "ForgeGateContext",
    "GateDecision",
    "GateHandler",
    "cmd_forge_dispatch",
    "cmd_forge_ledger_dispatch",
    "cmd_forge_ledger_latest",
    "cmd_forge_ledger_list",
    "cmd_forge_ledger_show",
    "cmd_forge_plan",
    "default_gate_handler",
    "materialize_agent_input",
    "render_forge_packet",
]
