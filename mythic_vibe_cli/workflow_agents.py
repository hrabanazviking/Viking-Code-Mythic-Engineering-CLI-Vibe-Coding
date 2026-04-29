"""Mythic agent contract spec — typed input/output for each role.

PH-03 slice 3.1. Pure declarative layer: no provider calls, no
side-effects, no command wiring. Defines the typed contract that
the future ``mythic-vibe forge`` orchestrator will enforce when
running a Skald → Architect → Cartographer → Forge Worker → Auditor
→ Scribe cycle.

Three shaping ideas drove the design:

1. **Provider-agnostic.** ``AgentInput`` and ``AgentOutput`` describe
   what flows between roles regardless of whether the agent itself
   is a local LLM, a cloud provider, a copy-paste handoff, or a
   human. Today only the copy-paste path runs end-to-end (PH-03
   slice 3.5 introduces the provider-backed forge).
2. **Machine-checkable verification.** Each role declares a tuple
   of named gates in its contract. The runner is responsible for
   evaluating those gates and producing :class:`VerificationResult`
   instances on the output. ``AgentOutput.all_gates_passed`` is the
   canonical pass/fail signal the orchestrator consults.
3. **Round-trip serializable.** Every dataclass has ``to_dict`` /
   ``from_dict`` so the orchestrator can persist intermediate
   handoffs to ``mythic/forge/`` (slice 3.2 adds the ledger;
   3.3 wires the dry-run forge command).

This module imports :data:`mythic_vibe_cli.ai.prompts.roles.ROLE_PROMPTS`
for prose content (identity / focus / system_prompt) but does not
modify it. The two layers are intentionally separate: ``roles.py``
owns the prose; ``workflow_agents.py`` owns the typed contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .ai.prompts.roles import ROLE_PROMPTS


# ---- Canonical role sequence ---------------------------------------------

DEFAULT_AGENT_SEQUENCE: tuple[str, ...] = (
    "Skald",
    "Architect",
    "Cartographer",
    "Forge Worker",
    "Auditor",
    "Scribe",
)


# ---- Verification result -------------------------------------------------


@dataclass(frozen=True)
class VerificationResult:
    """One named gate's outcome on an agent invocation."""

    name: str
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VerificationResult":
        return cls(
            name=str(payload.get("name") or ""),
            passed=bool(payload.get("passed", False)),
            detail=str(payload.get("detail") or ""),
        )


# ---- Agent input ---------------------------------------------------------


@dataclass(frozen=True)
class AgentInput:
    """Typed input passed to an agent invocation.

    Tuples (not lists) so the dataclass can stay frozen and hashable.
    Construction from dicts (e.g. JSON ledgers) goes through
    :meth:`from_dict`.
    """

    role: str
    task: str
    phase: str
    workflow_id: str | None = None
    workflow_step_id: str | None = None
    prior_outputs: tuple[str, ...] = ()
    context_files: tuple[str, ...] = ()
    forbidden_files: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "task": self.task,
            "phase": self.phase,
            "workflow_id": self.workflow_id,
            "workflow_step_id": self.workflow_step_id,
            "prior_outputs": list(self.prior_outputs),
            "context_files": list(self.context_files),
            "forbidden_files": list(self.forbidden_files),
            "invariants": list(self.invariants),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentInput":
        return cls(
            role=str(payload.get("role") or ""),
            task=str(payload.get("task") or ""),
            phase=str(payload.get("phase") or ""),
            workflow_id=str(payload["workflow_id"]) if payload.get("workflow_id") else None,
            workflow_step_id=(
                str(payload["workflow_step_id"]) if payload.get("workflow_step_id") else None
            ),
            prior_outputs=tuple(str(x) for x in payload.get("prior_outputs", []) if isinstance(x, str)),
            context_files=tuple(str(x) for x in payload.get("context_files", []) if isinstance(x, str)),
            forbidden_files=tuple(str(x) for x in payload.get("forbidden_files", []) if isinstance(x, str)),
            invariants=tuple(str(x) for x in payload.get("invariants", []) if isinstance(x, str)),
            notes=tuple(str(x) for x in payload.get("notes", []) if isinstance(x, str)),
        )


# ---- Agent output --------------------------------------------------------


@dataclass(frozen=True)
class AgentOutput:
    """Typed output every agent must produce.

    ``raw_response`` is provider-specific text (only populated when a
    real provider runs). The structured fields above it are what the
    orchestrator and downstream agents actually consume.
    """

    role: str
    timestamp: str
    workflow_id: str | None = None
    workflow_step_id: str | None = None
    summary: str = ""
    artefacts: tuple[str, ...] = ()
    decisions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    handoff_notes: tuple[str, ...] = ()
    verification_results: tuple[VerificationResult, ...] = ()
    raw_response: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "timestamp": self.timestamp,
            "workflow_id": self.workflow_id,
            "workflow_step_id": self.workflow_step_id,
            "summary": self.summary,
            "artefacts": list(self.artefacts),
            "decisions": list(self.decisions),
            "risks": list(self.risks),
            "handoff_notes": list(self.handoff_notes),
            "verification_results": [v.to_dict() for v in self.verification_results],
            "raw_response": self.raw_response,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentOutput":
        results = tuple(
            VerificationResult.from_dict(v)
            for v in payload.get("verification_results", [])
            if isinstance(v, dict)
        )
        raw = payload.get("raw_response")
        return cls(
            role=str(payload.get("role") or ""),
            timestamp=str(payload.get("timestamp") or ""),
            workflow_id=str(payload["workflow_id"]) if payload.get("workflow_id") else None,
            workflow_step_id=(
                str(payload["workflow_step_id"]) if payload.get("workflow_step_id") else None
            ),
            summary=str(payload.get("summary") or ""),
            artefacts=tuple(str(x) for x in payload.get("artefacts", []) if isinstance(x, str)),
            decisions=tuple(str(x) for x in payload.get("decisions", []) if isinstance(x, str)),
            risks=tuple(str(x) for x in payload.get("risks", []) if isinstance(x, str)),
            handoff_notes=tuple(str(x) for x in payload.get("handoff_notes", []) if isinstance(x, str)),
            verification_results=results,
            raw_response=str(raw) if raw is not None else None,
        )

    @property
    def all_gates_passed(self) -> bool:
        """True iff every recorded verification gate passed.

        An output with no recorded gates is treated as passing — the
        orchestrator is responsible for ensuring required gates are
        run, not this property.
        """
        return all(v.passed for v in self.verification_results)


# ---- Agent contract ------------------------------------------------------


@dataclass(frozen=True)
class AgentContract:
    """Static declaration of a Mythic agent role's input/output contract.

    A contract is descriptive: it tells the orchestrator what the
    agent expects, what it must produce, what artefact kinds carry
    its output, and which named gates determine pass/fail. The
    orchestrator does the work; the contract states the rules.
    """

    role: str
    input_required_fields: tuple[str, ...]
    output_required_fields: tuple[str, ...]
    output_artefact_kinds: tuple[str, ...]
    verification_gate: tuple[str, ...]
    handoff_to_role: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "input_required_fields": list(self.input_required_fields),
            "output_required_fields": list(self.output_required_fields),
            "output_artefact_kinds": list(self.output_artefact_kinds),
            "verification_gate": list(self.verification_gate),
            "handoff_to_role": self.handoff_to_role,
        }


# ---- Canonical contract registry ----------------------------------------

# Sequence handoffs are derived from DEFAULT_AGENT_SEQUENCE so the two
# tables can never drift apart. Each contract names:
#
# - input_required_fields   AgentInput fields that must be non-empty
# - output_required_fields  AgentOutput fields that must be non-empty
# - output_artefact_kinds   filename / artefact-shape labels the role
#                           is expected to produce or update
# - verification_gate       named checks the orchestrator runs against
#                           AgentOutput before allowing handoff

_HANDOFFS = {
    role: (DEFAULT_AGENT_SEQUENCE[i + 1] if i + 1 < len(DEFAULT_AGENT_SEQUENCE) else None)
    for i, role in enumerate(DEFAULT_AGENT_SEQUENCE)
}


AGENT_CONTRACTS: dict[str, AgentContract] = {
    "Skald": AgentContract(
        role="Skald",
        input_required_fields=("task", "phase"),
        output_required_fields=("summary", "decisions"),
        output_artefact_kinds=(
            "SYSTEM_VISION.md",
            "naming-notes.md",
        ),
        verification_gate=(
            "names-map-to-identifiable-concepts",
            "vision-stays-implementation-aligned",
        ),
        handoff_to_role=_HANDOFFS["Skald"],
    ),
    "Architect": AgentContract(
        role="Architect",
        input_required_fields=("task", "phase", "prior_outputs"),
        output_required_fields=("summary", "decisions", "artefacts"),
        output_artefact_kinds=(
            "ARCHITECTURE.md",
            "DOMAIN_MAP.md",
            "docs/ADRS/ADR-NNNN-*.md",
        ),
        verification_gate=(
            "boundaries-declared",
            "dependency-direction-consistent",
            "every-new-component-has-an-owner",
        ),
        handoff_to_role=_HANDOFFS["Architect"],
    ),
    "Cartographer": AgentContract(
        role="Cartographer",
        input_required_fields=("task", "phase", "prior_outputs"),
        output_required_fields=("summary", "artefacts", "handoff_notes"),
        output_artefact_kinds=(
            "DATA_FLOW.md",
            "docs/INDEX.md",
            "context-map.json",
        ),
        verification_gate=(
            "every-affected-path-mapped",
            "blast-radius-explicit",
        ),
        handoff_to_role=_HANDOFFS["Cartographer"],
    ),
    "Forge Worker": AgentContract(
        role="Forge Worker",
        input_required_fields=("task", "phase", "prior_outputs"),
        output_required_fields=("summary", "artefacts"),
        output_artefact_kinds=(
            "code-diffs",
            "new-or-modified-source-files",
        ),
        verification_gate=(
            "tests-pass",
            "lint-clean",
            "edit-surface-bounded",
        ),
        handoff_to_role=_HANDOFFS["Forge Worker"],
    ),
    "Auditor": AgentContract(
        role="Auditor",
        input_required_fields=("task", "phase", "prior_outputs"),
        output_required_fields=("summary", "verification_results"),
        output_artefact_kinds=(
            "mythic/verifications/<id>.json",
            "audit-report.md",
        ),
        verification_gate=(
            "diff-reviewed-against-architecture",
            "no-invariant-violation",
            "test-evidence-recorded",
        ),
        handoff_to_role=_HANDOFFS["Auditor"],
    ),
    "Scribe": AgentContract(
        role="Scribe",
        input_required_fields=("task", "phase", "prior_outputs"),
        output_required_fields=("summary", "artefacts", "handoff_notes"),
        output_artefact_kinds=(
            "DEVLOG.md",
            "CHANGELOG.md",
            "docs/SESSION_HANDOFF.md",
        ),
        verification_gate=(
            "docs-match-implementation",
            "handoff-recorded",
        ),
        handoff_to_role=_HANDOFFS["Scribe"],
    ),
}


# ---- Helpers -------------------------------------------------------------


def contract_for(role: str) -> AgentContract:
    """Return the contract for ``role`` or raise ``ValueError``."""
    contract = AGENT_CONTRACTS.get(role)
    if contract is None:
        raise ValueError(f"No agent contract registered for role: {role}")
    return contract


def validate_input(agent_input: AgentInput, contract: AgentContract) -> list[str]:
    """Return the list of contract-violation messages for ``agent_input``.

    Empty list means the input satisfies the contract. Currently the
    rule is "every field named in ``contract.input_required_fields``
    must be non-empty" — strings are stripped first; tuples must
    have at least one entry.
    """
    if agent_input.role != contract.role:
        return [f"AgentInput.role={agent_input.role!r} does not match contract.role={contract.role!r}"]
    errors: list[str] = []
    for field_name in contract.input_required_fields:
        value = getattr(agent_input, field_name, None)
        if value is None:
            errors.append(f"AgentInput.{field_name} is required for role {contract.role}")
            continue
        if isinstance(value, str) and not value.strip():
            errors.append(f"AgentInput.{field_name} must be non-empty for role {contract.role}")
            continue
        if isinstance(value, (list, tuple)) and len(value) == 0:
            errors.append(f"AgentInput.{field_name} must have at least one entry for role {contract.role}")
    return errors


def validate_output(agent_output: AgentOutput, contract: AgentContract) -> list[str]:
    """Return the list of contract-violation messages for ``agent_output``.

    Same rule as :func:`validate_input`. ``verification_results`` is a
    structural requirement only — the values themselves are not graded
    here. The orchestrator separately checks
    :attr:`AgentOutput.all_gates_passed` to decide whether to advance.
    """
    if agent_output.role != contract.role:
        return [
            f"AgentOutput.role={agent_output.role!r} does not match contract.role={contract.role!r}"
        ]
    errors: list[str] = []
    for field_name in contract.output_required_fields:
        value = getattr(agent_output, field_name, None)
        if value is None:
            errors.append(f"AgentOutput.{field_name} is required for role {contract.role}")
            continue
        if isinstance(value, str) and not value.strip():
            errors.append(f"AgentOutput.{field_name} must be non-empty for role {contract.role}")
            continue
        if isinstance(value, (list, tuple)) and len(value) == 0:
            errors.append(
                f"AgentOutput.{field_name} must have at least one entry for role {contract.role}"
            )
    return errors


def expected_handoff_chain() -> tuple[tuple[str, str | None], ...]:
    """Return ``((role, next_role))`` pairs for the canonical sequence.

    Used by tests to confirm ``AGENT_CONTRACTS`` and
    ``DEFAULT_AGENT_SEQUENCE`` agree on handoff direction.
    """
    return tuple(
        (
            role,
            DEFAULT_AGENT_SEQUENCE[i + 1] if i + 1 < len(DEFAULT_AGENT_SEQUENCE) else None,
        )
        for i, role in enumerate(DEFAULT_AGENT_SEQUENCE)
    )


def role_prose(role: str) -> dict[str, Any]:
    """Return the prose half of a role (identity / focus / system_prompt /
    invariants / verification) by reaching into
    :data:`mythic_vibe_cli.ai.prompts.roles.ROLE_PROMPTS`.

    The contract layer defines structure; the prose layer defines
    voice. Keeping them separate means a future provider-backed forge
    can mix and match: ship structured contract validation while
    swapping prose for a different style or language.
    """
    prompt = ROLE_PROMPTS.get(role)
    if prompt is None:
        raise ValueError(f"No role prompt registered for role: {role}")
    return {
        "name": prompt.name,
        "identity": prompt.identity,
        "focus": prompt.focus,
        "system_prompt": prompt.system_prompt,
        "invariants": list(prompt.invariants),
        "verification": list(prompt.verification),
    }


__all__ = [
    "AGENT_CONTRACTS",
    "AgentContract",
    "AgentInput",
    "AgentOutput",
    "DEFAULT_AGENT_SEQUENCE",
    "VerificationResult",
    "contract_for",
    "expected_handoff_chain",
    "role_prose",
    "validate_input",
    "validate_output",
]
