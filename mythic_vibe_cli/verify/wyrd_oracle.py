"""WYRD Protocol island binding (PH-09 Slice 9.3).

Optional Verifier-agent world-model check that try-imports the
``wyrd`` package — Volmarr's separate WYRD Protocol project (an
ECS-based AI world model that moves world-state out of the LLM
context into deterministic structured state).

This module exposes a gate runner compatible with the slice 3.6
:mod:`mythic_vibe_cli.forge_verifier` registry. Operators opt into
the WYRD gate explicitly — the default Auditor gate set is
unchanged from before PH-09 unless
``MYTHIC_ISLAND_WYRD_ENABLED=1`` AND the operator includes the
gate in their configuration.

Per ADR-0002 (no-direct-vendor-imports) and ADR-0007 (this
adapter's boundary), this module **never** imports from any
in-tree WYRD vendored snapshot. It only resolves whatever ``wyrd``
package the operator's ``sys.path`` / pip env makes available.

Cross-platform: stdlib only on the must-work path.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from ..workflow_agents import AgentInput, AgentOutput, VerificationResult
from ..workflow_engine import WorkflowPlan


ISLAND_ENABLED_ENV = "MYTHIC_ISLAND_WYRD_ENABLED"
GATE_NAME = "wyrd-oracle"
INSTALL_HINT = (
    "Install with `pip install wyrd-protocol` "
    "(or `pip install mythic-vibe[wyrd]` once the extra is published)."
)
_TRUTHY = {"1", "true", "yes", "on"}


def is_island_enabled() -> bool:
    raw = os.environ.get(ISLAND_ENABLED_ENV, "").strip().lower()
    return raw in _TRUTHY


def _try_import_wyrd() -> Any | None:
    try:
        import wyrd  # type: ignore[import-not-found]
    except ImportError:
        return None
    return wyrd


def gate_wyrd_oracle(
    plan: WorkflowPlan,
    agent_input: AgentInput,
    agent_output: AgentOutput,
    root: Path,
) -> VerificationResult:
    """Run the WYRD Protocol's passive_oracle against the Auditor's
    response. Passes when the oracle reports no world-model
    inconsistencies; fails otherwise. Always returns a typed
    :class:`VerificationResult`; never raises.

    Special cases:

    - Island flag off → passes with a "disabled" detail. This lets
      operators add the gate to their pipeline unconditionally and
      let the env flag control activation.
    - WYRD package missing → fails (gate was opted-in but can't
      run); the failure detail surfaces the install hint.
    - WYRD package present but no ``passive_oracle`` shape → fails
      with a contract-gap detail.
    - Auditor's ``raw_response`` is empty → passes (nothing to
      check; Auditor has independent gates for that case).
    """
    if not is_island_enabled():
        return VerificationResult(
            name=GATE_NAME,
            passed=True,
            detail=(
                f"WYRD island disabled "
                f"(set {ISLAND_ENABLED_ENV}=1 to activate)"
            ),
        )

    module = _try_import_wyrd()
    if module is None:
        return VerificationResult(
            name=GATE_NAME,
            passed=False,
            detail=f"wyrd package not importable. {INSTALL_HINT}",
        )

    response_text = agent_output.raw_response or ""
    if not response_text.strip():
        return VerificationResult(
            name=GATE_NAME,
            passed=True,
            detail="empty audit response — nothing for the oracle to check",
        )

    oracle: Callable[[str], Any] | None = None
    for attr_path in ("passive_oracle", "oracle.passive_oracle", "oracle.check"):
        target: Any = module
        for piece in attr_path.split("."):
            target = getattr(target, piece, None)
            if target is None:
                break
        if callable(target):
            oracle = target  # type: ignore[assignment]
            break

    if oracle is None:
        return VerificationResult(
            name=GATE_NAME,
            passed=False,
            detail=(
                "wyrd package is importable but does not expose a known "
                "oracle shape (tried: passive_oracle, oracle.passive_oracle, "
                "oracle.check)"
            ),
        )

    try:
        verdict = oracle(response_text)
    except Exception as exc:  # noqa: BLE001 — never crash a gate
        return VerificationResult(
            name=GATE_NAME,
            passed=False,
            detail=f"oracle raised: {exc}",
        )

    # WYRD's oracle shape is loosely-typed historically — accept
    # bool, dict (with "passed" / "ok" / "consistent" keys), or any
    # truthy value. Default to "pass on truthy" so operators can
    # write a minimal stub oracle for testing.
    passed, detail = _interpret_oracle_verdict(verdict)
    return VerificationResult(name=GATE_NAME, passed=passed, detail=detail)


def _interpret_oracle_verdict(verdict: Any) -> tuple[bool, str]:
    """Coerce a duck-typed oracle return value into a (passed,
    detail) pair. Accepts bool, dict, or any truthy value."""
    if isinstance(verdict, bool):
        return verdict, "passive_oracle returned bool"
    if isinstance(verdict, dict):
        for key in ("passed", "ok", "consistent"):
            if key in verdict:
                passed = bool(verdict[key])
                detail = str(verdict.get("detail", "") or verdict.get("reason", "") or "")
                return passed, detail or f"passive_oracle {key}={passed}"
        # No recognised verdict key — treat presence of dict as
        # truthy if non-empty, false if empty.
        return bool(verdict), f"passive_oracle returned dict {verdict!r}"
    return bool(verdict), f"passive_oracle returned {type(verdict).__name__} (truthy={bool(verdict)})"


def wyrd_gate_if_enabled() -> dict[str, Any]:
    """Convenience: return ``{"wyrd-oracle": gate_wyrd_oracle}``
    when the island flag is on, else an empty dict. Operators
    spread this into their gate registry to opt into the gate
    only when configured:

    .. code-block:: python

        from mythic_vibe_cli.forge_verifier import DEFAULT_AUDITOR_GATES
        from mythic_vibe_cli.verify.wyrd_oracle import wyrd_gate_if_enabled

        gates = {**DEFAULT_AUDITOR_GATES, **wyrd_gate_if_enabled()}
    """
    if is_island_enabled():
        return {GATE_NAME: gate_wyrd_oracle}
    return {}


__all__ = [
    "GATE_NAME",
    "INSTALL_HINT",
    "ISLAND_ENABLED_ENV",
    "gate_wyrd_oracle",
    "is_island_enabled",
    "wyrd_gate_if_enabled",
]
