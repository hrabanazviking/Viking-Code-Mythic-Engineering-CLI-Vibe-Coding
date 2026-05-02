"""Policy gate (PH-14 Slice 14.2).

Sits in front of write commands. Given a loaded
:class:`ConstraintLoadResult` and a proposed action +
command, returns a typed :class:`PolicyDecision` with the
violations and a flag for whether an explicit override is
required.

The gate is **opt-in by command**. Wholesale interception of
every write command would silently change behaviour project-
wide. Slice 14.2 wires one demonstration command (cmd_oath);
follow-ups roll out gradually as each command opts in via
:func:`enforce_policy`.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .constraint_store import (
    Constraint,
    SEVERITY_BLOCKING,
    load_constraints,
)


PolicyAction = str  # "read" | "write" | "exec" — narrow vocabulary


@dataclass(frozen=True)
class PolicyDecision:
    """Result of :func:`evaluate`. ``allowed`` is the final
    permit/deny verdict; ``violations`` is the list of
    constraints the proposed command runs into; ``requires_override``
    flags blocking violations that need an explicit
    ``--override "<reason>"``."""

    allowed: bool
    violations: list[Constraint] = field(default_factory=list)
    requires_override: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "violations": [c.to_dict() for c in self.violations],
            "requires_override": self.requires_override,
            "notes": list(self.notes),
            "violation_count": len(self.violations),
        }


def _matches_command(constraint: Constraint, command: str) -> bool:
    """Heuristic match: a constraint applies to a command when
    the command name appears in the constraint text (case-
    insensitive). The default policy gate is intentionally
    conservative — it surfaces *all* constraints as violations
    if no specific command is mentioned in the text, so operators
    can't miss them.

    Tag a constraint with ``[command:<name>]`` to scope it to a
    specific command (future enhancement; ignored today)."""
    return command.lower() in constraint.text.lower()


def evaluate(
    constraints: Iterable[Constraint],
    *,
    action: PolicyAction,
    command: str,
    root: Path | None = None,
) -> PolicyDecision:
    """Walk the constraints and return a typed decision.

    Today's matching rule is broad: every blocking constraint
    surfaces as a violation regardless of command name. Operators
    write narrowly-scoped constraints to keep the surface
    actionable. (Future enhancement: per-command scoping via
    ``[command:<name>]`` tags.)
    """
    # Additive 2026-05-02 (Phase A.2 of audit remediation): materialise
    # the iterable once, up-front, so both the list-comprehension below
    # and the `any(constraints)` check that follows it see the same
    # constraint set. Pseudo-code audit finding #3 caught this:
    # generator inputs were exhausted by the comp at line 85, leaving
    # `any()` to operate on an empty iterator and silently suppress the
    # advisory note. List inputs were unaffected (lists support multiple
    # iteration); the bug only fired for generator-style callers.
    constraints = list(constraints)
    violations = [
        c for c in constraints if c.severity == SEVERITY_BLOCKING
    ]
    requires_override = bool(violations)
    notes: list[str] = []
    if not violations and any(constraints):
        notes.append(
            f"action={action!r} command={command!r}: "
            "no blocking violations (warn/advisory constraints not gating)"
        )
    if root is not None:
        notes.append(f"project_root={root.resolve()}")
    return PolicyDecision(
        allowed=not requires_override,
        violations=violations,
        requires_override=requires_override,
        notes=notes,
    )


def evaluate_for_root(
    root: Path,
    *,
    action: PolicyAction,
    command: str,
) -> PolicyDecision:
    """Convenience: load constraints from ``root`` and evaluate."""
    result = load_constraints(root)
    return evaluate(
        result.constraints, action=action, command=command, root=root
    )


def enforce_policy(
    root: Path,
    *,
    action: PolicyAction,
    command: str,
    override_reason: str | None = None,
) -> tuple[bool, PolicyDecision]:
    """Top-level enforcement helper called by writing commands.

    Returns ``(proceed, decision)``:
    - ``proceed=True`` when the command should run normally
      (no blocking constraints OR override supplied).
    - ``proceed=False`` when blocking constraints exist and no
      override was supplied — the caller should refuse.

    When an override is supplied, the gate logs the override via
    :mod:`override_log` (slice 14.3) but still returns proceed=True.
    """
    decision = evaluate_for_root(root, action=action, command=command)

    if not decision.requires_override:
        return True, decision

    if override_reason and override_reason.strip():
        # Log + continue.
        from .override_log import append_override

        try:
            append_override(
                root,
                action=action,
                command=command,
                reason=override_reason.strip(),
                violation_ids=[c.id for c in decision.violations],
            )
        except Exception:  # noqa: BLE001 — never crash the parent command
            pass
        return True, decision

    return False, decision


__all__ = [
    "PolicyAction",
    "PolicyDecision",
    "enforce_policy",
    "evaluate",
    "evaluate_for_root",
]
