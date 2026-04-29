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
import dataclasses
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Callable, Literal

from .ai.providers.base import ProviderResponse
from .ai.registry import ProviderRegistry
from .core.state import utc_now
from .errors import CliError, format_error
from .exit_codes import (
    OPERATIONAL_FAILURE,
    SUCCESS,
    UNSAFE_OPERATION_BLOCKED,
    USER_INPUT_ERROR,
)
from .forge_ledger import ForgeLedger, ForgeLedgerEntry
from .forge_reflection import (
    build_forge_reflection,
    list_forge_reflections,
    load_forge_reflection,
    render_forge_reflection_markdown,
    write_forge_reflection,
)
from .forge_verifier import DEFAULT_AUDITOR_GATES, GateRunner, run_auditor_gates
from .output import write_bullet, write_error, write_json, write_key_value, write_line
from .workflow_agents import (
    AGENT_CONTRACTS,
    AgentInput,
    AgentOutput,
    VerificationResult,
    contract_for,
    validate_input,
)
from .workflow_engine import (
    DEFAULT_ROLE_SEQUENCE,
    WorkflowEngine,
    WorkflowPlan,
    WorkflowStep,
)


# Provider duck-type — anything matching this Protocol works.
# Tests inject stubs; production uses ProviderRegistry().providers()[name].
class _SupportsRun:
    name: str

    def run(self, packet: object, *, dry_run: bool = False) -> ProviderResponse:  # pragma: no cover
        ...


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


def materialize_agent_input(
    plan: WorkflowPlan,
    step: WorkflowStep,
    *,
    prior_outputs: tuple[str, ...] = (),
) -> AgentInput:
    """Build the typed :class:`AgentInput` for one step in ``plan``.

    Slice 3.3 dry-run callers leave ``prior_outputs`` empty, which
    causes contract validation to fail for every role except Skald
    (whose contract requires only ``task`` + ``phase``). Slice 3.5
    callers populate ``prior_outputs`` with serialised ``AgentOutput``
    JSON of every prior step that has completed, unblocking the
    downstream contract gates.
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
        prior_outputs=prior_outputs,
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


# ---- forge run (PH-03 slice 3.5) ----------------------------------------


# Type alias for the provider factory test injection point.
ProviderFactory = Callable[[str, Path], Any]


def prior_outputs_for_step(
    plan: WorkflowPlan,
    step: WorkflowStep,
    ledger: ForgeLedger,
) -> tuple[str, ...]:
    """Walk the plan up to ``step`` and collect the JSON-serialised
    ``AgentOutput`` of every prior step that has a recorded output in
    the ledger.

    Skipped / blocked / failed prior steps contribute nothing — only
    entries with a populated ``agent_output`` are included. The
    surviving outputs unblock contract validation for downstream
    roles whose contracts require ``prior_outputs`` (Architect /
    Cartographer / Forge Worker / Auditor / Scribe).
    """
    workflow_id = plan.workflow_id or ""
    prior_step_ids: list[str] = []
    for candidate in plan.steps:
        if candidate.step_id == step.step_id:
            break
        prior_step_ids.append(candidate.step_id)

    out: list[str] = []
    for prior_id in prior_step_ids:
        entry = ledger.find_step(workflow_id, prior_id)
        if entry is None or entry.agent_output is None:
            continue
        out.append(json.dumps(entry.agent_output.to_dict()))
    return tuple(out)


def build_agent_output_from_response(
    response: ProviderResponse,
    agent_input: AgentInput,
) -> AgentOutput:
    """Minimal text → :class:`AgentOutput` translation.

    Slice 3.5 captures the provider's full response as
    ``raw_response`` and uses the first non-empty line as the
    summary. Structured fields (artefacts / decisions / risks /
    handoff_notes / verification_results) stay empty until a
    structured-extraction pass lands in a later slice — operators
    can fill them in by re-ingesting via ``packet ingest`` if they
    need provenance richer than the raw text.
    """
    text = (response.content or "").strip()
    summary = ""
    for line in text.splitlines():
        clean = line.strip()
        if clean:
            summary = clean[:200]
            break
    return AgentOutput(
        role=agent_input.role,
        timestamp=utc_now(),
        workflow_id=agent_input.workflow_id,
        workflow_step_id=agent_input.workflow_step_id,
        summary=summary,
        artefacts=(),
        decisions=(),
        risks=(),
        handoff_notes=(),
        verification_results=(),
        raw_response=response.content,
    )


def _resolve_provider(
    name: str,
    root: Path,
    *,
    provider_factory: ProviderFactory | None,
) -> tuple[Any | None, str | None]:
    """Resolve a provider by name. Returns ``(provider, error_message)``.

    Tests pass ``provider_factory`` to inject stubs without going
    through ``ProviderRegistry``. Real CLI invocations use the
    registry.
    """
    if provider_factory is not None:
        try:
            return provider_factory(name, root), None
        except Exception as exc:  # noqa: BLE001 - factory is test-controlled
            return None, f"Provider factory rejected {name!r}: {exc}"

    providers = ProviderRegistry(root=root).providers()
    provider = providers.get(name)
    if provider is None:
        valid = ", ".join(sorted(providers))
        return None, f"Unknown provider {name!r}. Available: {valid}"
    status = provider.validate_config()
    if not status.configured:
        joined = "; ".join(status.details) or "provider not configured"
        return None, f"Provider {name!r} is not configured: {joined}"
    return provider, None


def cmd_forge_run(
    args: argparse.Namespace,
    *,
    gate_handler: GateHandler | None = None,
    provider_factory: ProviderFactory | None = None,
    auditor_gates: dict[str, GateRunner] | None = None,
) -> int:
    """``mythic-vibe forge run`` — provider-backed forge execution.

    Walks the workflow plan, populates ``prior_outputs`` per step
    from the ledger, calls the configured provider for each role,
    captures responses into ``AgentOutput`` records, and persists
    each transition through ``ForgeLedger``.

    For the Auditor step (slice 3.6), the captured ``AgentOutput`` is
    additionally run through :func:`run_auditor_gates` so the role
    contract's named gates become real machine-checks. A failing gate
    transitions the step from ``succeeded`` to ``failed`` even if the
    provider call itself returned cleanly. Pass
    ``auditor_gates={}`` to opt out; pass a custom dict to inject
    stubs.

    With ``--strict``, any failed gate aborts the run: every
    remaining step is recorded as ``blocked`` with note
    ``"verifier strict-mode abort"``.

    Status transitions per step:

    - contract validation fails → ``blocked`` (no provider call)
    - provider call begins → ``running``
    - provider call returns → ``succeeded``
    - provider call raises → ``failed``
    - Auditor verifier gates fail → ``failed``
    - operator aborts at gate → all remaining steps ``blocked``
    - operator skips at gate → next step ``blocked``
    - --strict + Auditor gate failure → all remaining ``blocked``

    Returns ``SUCCESS`` if every executed step succeeded;
    ``OPERATIONAL_FAILURE`` if at least one step failed;
    ``UNSAFE_OPERATION_BLOCKED`` if the operator aborted via gate or
    --strict triggered;
    ``USER_INPUT_ERROR`` for missing task / unknown provider.
    """
    root = Path(getattr(args, "path", ".")).resolve()
    task = (getattr(args, "task", "") or "").strip()
    if not task:
        write_error("forge run requires --task <text>.")
        return USER_INPUT_ERROR

    provider_name = (getattr(args, "provider", "") or "").strip()
    if not provider_name:
        write_error("forge run requires --provider <name>.")
        return USER_INPUT_ERROR

    provider, provider_err = _resolve_provider(
        provider_name, root, provider_factory=provider_factory
    )
    if provider is None:
        write_error(provider_err or f"Could not resolve provider {provider_name!r}.")
        return USER_INPUT_ERROR

    engine = WorkflowEngine(root)
    try:
        plan = engine.build_plan(task, role_sequence=DEFAULT_ROLE_SEQUENCE)
    except ValueError as exc:
        write_error(format_error(CliError(f"Workflow plan build failed: {exc}")))
        return USER_INPUT_ERROR

    skip_ledger = _flag(args, "skip_ledger")
    interactive = _flag(args, "interactive")
    strict = _flag(args, "strict")
    handler: GateHandler = gate_handler or default_gate_handler
    auditor_gates_map = (
        DEFAULT_AUDITOR_GATES if auditor_gates is None else auditor_gates
    )
    ledger = ForgeLedger(root=root)

    step_payloads: list[dict[str, Any]] = []
    started_at = utc_now()
    aborted = False
    skip_next_step = False
    failure_count = 0
    success_count = 0

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

        prior_outputs = prior_outputs_for_step(plan, step, ledger)
        agent_input = materialize_agent_input(plan, step, prior_outputs=prior_outputs)
        contract = contract_for(step.role)
        validation_errors = validate_input(agent_input, contract)

        if validation_errors:
            # Contract failure — record blocked and continue (operator
            # decides whether to abort at the next gate).
            if not skip_ledger:
                entry = ForgeLedgerEntry(
                    workflow_id=plan.workflow_id or "",
                    step_id=step.step_id,
                    role=step.role,
                    status="blocked",
                    started_at=started_at,
                    agent_input=agent_input,
                    notes=tuple(validation_errors),
                )
                ledger.append(entry)
            step_payloads.append(
                {
                    "step_id": step.step_id,
                    "role": step.role,
                    "phase": step.phase,
                    "objective": step.objective,
                    "handoff_to": step.handoff_to,
                    "agent_input": agent_input.to_dict(),
                    "validation_errors": list(validation_errors),
                    "status": "blocked",
                    "agent_output": None,
                }
            )
        else:
            # Append running entry, call provider, transition to
            # succeeded or failed.
            running_entry = ForgeLedgerEntry(
                workflow_id=plan.workflow_id or "",
                step_id=step.step_id,
                role=step.role,
                status="running",
                started_at=utc_now(),
                agent_input=agent_input,
            )
            if not skip_ledger:
                ledger.append(running_entry)

            packet_text = render_forge_packet(plan, step, agent_input)
            packet_view = {
                "text": packet_text,
                "packet_id": f"{plan.workflow_id or 'WF'}:{step.step_id}",
                "source": "forge",
            }

            try:
                response = provider.run(packet_view)
            except Exception as exc:  # noqa: BLE001 - provider failure is recoverable
                failure_count += 1
                failed_at = utc_now()
                if not skip_ledger:
                    duration = _duration_ms(running_entry.started_at, failed_at)
                    ledger.update_step(
                        running_entry.workflow_id,
                        running_entry.step_id,
                        status="failed",
                        completed_at=failed_at,
                        duration_ms=duration,
                        notes=(f"provider raised: {exc}",),
                    )
                step_payloads.append(
                    {
                        "step_id": step.step_id,
                        "role": step.role,
                        "phase": step.phase,
                        "objective": step.objective,
                        "handoff_to": step.handoff_to,
                        "agent_input": agent_input.to_dict(),
                        "validation_errors": [],
                        "status": "failed",
                        "agent_output": None,
                        "error": str(exc),
                    }
                )
            else:
                agent_output = build_agent_output_from_response(response, agent_input)

                # Slice 3.6: if this is the Auditor, run the contract's
                # verification gates against the project state. The
                # gates either confirm the audit (verification_results
                # all pass → step still succeeds) or reveal that the
                # audit missed something (any fail → step transitions
                # to failed regardless of the provider's response).
                #
                # An empty ``auditor_gates_map`` means "opt out" — used
                # by tests that focus on the orchestration loop rather
                # than the gate runners. Production callers leave
                # ``auditor_gates`` as None so DEFAULT_AUDITOR_GATES
                # is used.
                gate_results: tuple[VerificationResult, ...] = ()
                contract_for_step = AGENT_CONTRACTS.get(step.role)
                if (
                    step.role == "Auditor"
                    and contract_for_step is not None
                    and auditor_gates_map
                ):
                    gate_results = run_auditor_gates(
                        plan,
                        agent_input,
                        agent_output,
                        root,
                        gate_names=contract_for_step.verification_gate,
                        gates=auditor_gates_map,
                    )
                    if gate_results:
                        agent_output = dataclasses.replace(
                            agent_output, verification_results=gate_results
                        )

                completed_at = agent_output.timestamp
                gates_ok = agent_output.all_gates_passed
                if gates_ok:
                    final_status = "succeeded"
                    success_count += 1
                    failed_gate_names: list[str] = []
                    notes: tuple[str, ...] = ()
                else:
                    final_status = "failed"
                    failure_count += 1
                    failed_gate_names = [
                        r.name for r in gate_results if not r.passed
                    ]
                    notes = (
                        "verification gates failed: "
                        + ", ".join(failed_gate_names),
                    )

                if not skip_ledger:
                    duration = _duration_ms(running_entry.started_at, completed_at)
                    ledger.update_step(
                        running_entry.workflow_id,
                        running_entry.step_id,
                        status=final_status,
                        completed_at=completed_at,
                        duration_ms=duration,
                        agent_output=agent_output,
                        notes=notes if notes else None,
                    )
                step_payloads.append(
                    {
                        "step_id": step.step_id,
                        "role": step.role,
                        "phase": step.phase,
                        "objective": step.objective,
                        "handoff_to": step.handoff_to,
                        "agent_input": agent_input.to_dict(),
                        "validation_errors": [],
                        "status": final_status,
                        "agent_output": agent_output.to_dict(),
                        "failed_gates": failed_gate_names,
                    }
                )

                # --strict: any auditor gate failure aborts the rest.
                if not gates_ok and strict and step.role == "Auditor":
                    aborted = True
                    for remaining in plan.steps[index + 1 :]:
                        payload = _record_aborted_step(
                            plan=plan,
                            step=remaining,
                            started_at=started_at,
                            note="verifier strict-mode abort",
                            skip_ledger=skip_ledger,
                            ledger=ledger,
                        )
                        step_payloads.append(payload)
                    break

        # Gate after this step before advancing — but never after the
        # final step.
        if interactive and index + 1 < total:
            next_step = plan.steps[index + 1]
            context = ForgeGateContext(
                workflow_id=plan.workflow_id or "",
                completed_step_index=index,
                completed_step_id=step.step_id,
                completed_role=step.role,
                completed_status=step_payloads[-1]["status"],
                completed_validation_errors=tuple(step_payloads[-1]["validation_errors"]),
                next_step_id=next_step.step_id,
                next_role=next_step.role,
                total_steps=total,
            )
            decision = handler(context)
            if decision == "abort":
                aborted = True
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

    # Determine final exit code.
    if aborted:
        final_code: int = UNSAFE_OPERATION_BLOCKED
    elif failure_count > 0:
        final_code = OPERATIONAL_FAILURE
    else:
        final_code = SUCCESS

    # Slice 3.7: build + persist a reflection unless skipped.
    # Skip when the ledger is suppressed (no entries to read from)
    # or when --skip-reflection was set explicitly.
    reflection_paths_written: tuple[Path, Path] | None = None
    if not skip_ledger and not _flag(args, "skip_reflection"):
        reflection = build_forge_reflection(plan, ledger, aborted=aborted)
        reflection_paths_written = write_forge_reflection(root, reflection)

    if _flag(args, "json"):
        write_json(
            {
                "command": "forge run",
                "provider": provider_name,
                "skip_ledger": skip_ledger,
                "interactive": interactive,
                "aborted": aborted,
                "workflow_id": plan.workflow_id,
                "task": plan.task,
                "created_at": plan.created_at,
                "ledger_path": str(ledger.path) if not skip_ledger else None,
                "reflection_json_path": (
                    str(reflection_paths_written[0]) if reflection_paths_written else None
                ),
                "reflection_markdown_path": (
                    str(reflection_paths_written[1]) if reflection_paths_written else None
                ),
                "role_sequence": list(DEFAULT_ROLE_SEQUENCE),
                "success_count": success_count,
                "failure_count": failure_count,
                "steps": step_payloads,
            }
        )
        return final_code

    write_line("Mythic forge run")
    write_key_value("Workflow", plan.workflow_id or "(no id)")
    write_key_value("Task", plan.task)
    write_key_value("Provider", provider_name)
    write_key_value("Steps", total)
    write_key_value("Succeeded", success_count)
    write_key_value("Failed", failure_count)
    if interactive:
        write_key_value("Interactive", "yes")
    if aborted:
        write_key_value("Aborted", "yes (operator declined a gate)")
    if not skip_ledger:
        write_key_value("Ledger", ledger.path)
    if reflection_paths_written is not None:
        write_key_value("Reflection (md)", reflection_paths_written[1])
        write_key_value("Reflection (json)", reflection_paths_written[0])
    write_line("")

    for payload in step_payloads:
        write_line(
            f"- {payload['step_id']} :: {payload['role']} ({payload['phase']}) -> {payload['handoff_to'] or 'end'}"
        )
        write_bullet(f"status: {payload['status']}", indent=2)
        if payload.get("validation_errors"):
            write_bullet("validation errors:", indent=2)
            for err in payload["validation_errors"]:
                write_bullet(err, indent=4)
        if payload.get("error"):
            write_bullet(f"error: {payload['error']}", indent=2)
        if payload.get("blocked_reason"):
            write_bullet(f"blocked: {payload['blocked_reason']}", indent=2)
        if payload.get("agent_output") and payload["agent_output"].get("summary"):
            write_bullet(f"summary: {payload['agent_output']['summary']}", indent=2)

    return final_code


def _duration_ms(started_at: str, ended_at: str) -> int | None:
    """Best-effort millisecond delta between two ISO-8601 timestamps.

    Returns ``None`` if either string fails to parse — duration is
    decorative metadata, not load-bearing.
    """
    from datetime import datetime as _dt

    try:
        start = _dt.fromisoformat(started_at.replace("Z", "+00:00"))
        end = _dt.fromisoformat(ended_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    delta = end - start
    return int(delta.total_seconds() * 1000)


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


def cmd_forge_reflection_list(args: argparse.Namespace) -> int:
    """``mythic-vibe forge reflection list`` — every reflection on disk."""
    root = Path(getattr(args, "path", ".")).resolve()
    workflow_ids = list_forge_reflections(root)

    if _flag(args, "json"):
        write_json(
            {
                "command": "forge reflection list",
                "reflections_dir": str((root / "mythic" / "reflections").resolve()),
                "count": len(workflow_ids),
                "workflow_ids": workflow_ids,
            }
        )
        return SUCCESS

    if not workflow_ids:
        write_line("No forge reflections recorded.")
        write_key_value("Path", root / "mythic" / "reflections")
        return SUCCESS

    write_line(f"Forge reflections ({len(workflow_ids)} on disk)")
    for workflow_id in workflow_ids:
        write_bullet(workflow_id, indent=2)
    return SUCCESS


def cmd_forge_reflection_show(args: argparse.Namespace) -> int:
    """``mythic-vibe forge reflection show --workflow <id>`` — read one
    reflection's JSON sidecar and render it (defaults to markdown)."""
    root = Path(getattr(args, "path", ".")).resolve()
    workflow_id = (getattr(args, "workflow", "") or "").strip()
    if not workflow_id:
        write_error("forge reflection show requires --workflow <id>.")
        return USER_INPUT_ERROR

    reflection = load_forge_reflection(root, workflow_id)
    if reflection is None:
        message = f"No reflection found for workflow_id={workflow_id!r}."
        if _flag(args, "json"):
            write_json(
                {
                    "command": "forge reflection show",
                    "workflow_id": workflow_id,
                    "ok": False,
                    "errors": [message],
                }
            )
        else:
            write_error(message)
        return USER_INPUT_ERROR

    if _flag(args, "json"):
        write_json(
            {
                "command": "forge reflection show",
                "workflow_id": workflow_id,
                "ok": True,
                "reflection": reflection.to_dict(),
            }
        )
        return SUCCESS

    write_line(render_forge_reflection_markdown(reflection), force=True)
    return SUCCESS


def cmd_forge_reflection_latest(args: argparse.Namespace) -> int:
    """``mythic-vibe forge reflection latest`` — show the most recently
    written reflection."""
    root = Path(getattr(args, "path", ".")).resolve()
    workflow_ids = list_forge_reflections(root)
    if not workflow_ids:
        message = "No forge reflections recorded."
        if _flag(args, "json"):
            write_json(
                {
                    "command": "forge reflection latest",
                    "ok": False,
                    "errors": [message],
                }
            )
        else:
            write_line(message)
        return SUCCESS if not _flag(args, "json") else USER_INPUT_ERROR

    latest_id = workflow_ids[-1]
    args.workflow = latest_id
    return cmd_forge_reflection_show(args)


def cmd_forge_reflection_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "reflection_command", None)
    if sub == "list":
        return cmd_forge_reflection_list(args)
    if sub == "show":
        return cmd_forge_reflection_show(args)
    if sub == "latest":
        return cmd_forge_reflection_latest(args)
    write_error(
        f"Unknown forge reflection subcommand: {sub!r}. "
        "Try `forge reflection list`, `latest`, or `show --workflow <id>`."
    )
    return USER_INPUT_ERROR


def cmd_forge_dispatch(args: argparse.Namespace) -> int:
    sub = getattr(args, "forge_command", None)
    if sub == "plan":
        return cmd_forge_plan(args)
    if sub == "run":
        return cmd_forge_run(args)
    if sub == "ledger":
        return cmd_forge_ledger_dispatch(args)
    if sub == "reflection":
        return cmd_forge_reflection_dispatch(args)
    write_error(
        f"Unknown forge subcommand: {sub!r}. "
        "Try `mythic-vibe forge plan --dry-run --task <X>`, "
        "`mythic-vibe forge run --provider <name> --task <X>`, "
        "`mythic-vibe forge ledger list`, "
        "or `mythic-vibe forge reflection list`."
    )
    return USER_INPUT_ERROR


__all__ = [
    "ForgeGateContext",
    "GateDecision",
    "GateHandler",
    "ProviderFactory",
    "build_agent_output_from_response",
    "cmd_forge_dispatch",
    "cmd_forge_ledger_dispatch",
    "cmd_forge_ledger_latest",
    "cmd_forge_ledger_list",
    "cmd_forge_ledger_show",
    "cmd_forge_plan",
    "cmd_forge_reflection_dispatch",
    "cmd_forge_reflection_latest",
    "cmd_forge_reflection_list",
    "cmd_forge_reflection_show",
    "cmd_forge_run",
    "default_gate_handler",
    "materialize_agent_input",
    "prior_outputs_for_step",
    "render_forge_packet",
]
