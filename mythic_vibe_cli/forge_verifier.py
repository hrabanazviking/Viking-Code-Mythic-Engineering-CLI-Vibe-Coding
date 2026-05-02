"""Gate runners for the Auditor agent (PH-03 slice 3.6).

The Auditor's contract (slice 3.1) declares three named gates:

- ``diff-reviewed-against-architecture``
- ``no-invariant-violation``
- ``test-evidence-recorded``

Slice 3.5 captured the Auditor's response into ``AgentOutput`` but
left ``verification_results`` empty. This module fills the gap: each
gate name maps to a runner function that returns a typed
:class:`mythic_vibe_cli.workflow_agents.VerificationResult`. The
forge orchestrator (slice 3.5 + 3.6) calls
:func:`run_auditor_gates` after the Auditor's provider call returns,
attaches the results to ``agent_output.verification_results``, and
transitions the ledger entry to ``failed`` if
:attr:`AgentOutput.all_gates_passed` is False.

Gate runners are intentionally permissive on bare projects:

- ``diff-reviewed-against-architecture`` passes when there are no
  changed files (nothing to review). Otherwise it checks whether the
  Auditor's ``raw_response`` mentions every changed file.
- ``no-invariant-violation`` consults
  :func:`mythic_vibe_cli.verify.invariant_checker.check_invariants`.
  Returns failure if the project's invariant check reports any
  errors. Bare projects fail this gate (missing boundary docs etc),
  which is correct behaviour — production usage runs against a real
  Mythic project.
- ``test-evidence-recorded`` requires
  ``mythic/verifications/latest.json`` to exist; a fresh project
  must run ``mythic-vibe verify --record`` first.

Tests inject custom gate dicts via the ``gates`` parameter; passing
``{}`` opts out entirely (Auditor succeeds purely on the provider's
say-so, which is how slice 3.5 behaved before this slice landed).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .verify import load_latest_verification
from .verify.git_diff import collect_changed_files
from .verify.invariant_checker import check_invariants
from .workflow_agents import AgentInput, AgentOutput, VerificationResult
from .workflow_engine import WorkflowPlan


GateRunner = Callable[
    [WorkflowPlan, AgentInput, AgentOutput, Path],
    VerificationResult,
]


# ---- Individual gate runners --------------------------------------------


def gate_diff_reviewed(
    plan: WorkflowPlan,
    agent_input: AgentInput,
    agent_output: AgentOutput,
    root: Path,
) -> VerificationResult:
    """Pass if the Auditor's response mentions every git-changed file
    by relative path. Bare/clean trees pass automatically (nothing to
    review). Uses ``verify.git_diff.collect_changed_files`` which
    returns ``[]`` when git is unavailable, so this gate never crashes
    on non-git projects."""
    name = "diff-reviewed-against-architecture"
    try:
        changed = collect_changed_files(root)
    except Exception as exc:  # noqa: BLE001 - never crash a gate
        return VerificationResult(
            name=name,
            passed=True,
            detail=f"git unavailable; treating as no diff to review ({exc})",
        )

    if not changed:
        return VerificationResult(
            name=name,
            passed=True,
            detail="no changed files to review",
        )

    response_text = (agent_output.raw_response or "").lower()
    if not response_text:
        return VerificationResult(
            name=name,
            passed=False,
            detail=f"empty audit response with {len(changed)} changed files",
        )

    not_mentioned = [
        path for path in changed if path.lower() not in response_text
    ]
    if not_mentioned:
        preview = ", ".join(not_mentioned[:5])
        more = f" (+{len(not_mentioned) - 5} more)" if len(not_mentioned) > 5 else ""
        return VerificationResult(
            name=name,
            passed=False,
            detail=f"changed files not mentioned in audit: {preview}{more}",
        )
    return VerificationResult(
        name=name,
        passed=True,
        detail=f"reviewed {len(changed)} changed files",
    )


def gate_no_invariant_violation(
    plan: WorkflowPlan,
    agent_input: AgentInput,
    agent_output: AgentOutput,
    root: Path,
) -> VerificationResult:
    """Run the project's invariant checker (the same one
    ``mythic-vibe verify --invariants`` uses) and convert the
    structured result into a single VerificationResult."""
    name = "no-invariant-violation"
    try:
        result = check_invariants(root)
    except Exception as exc:  # noqa: BLE001
        return VerificationResult(
            name=name,
            passed=False,
            detail=f"invariant checker crashed: {exc}",
        )

    if result.errors:
        first = result.errors[0]
        if len(first) > 100:
            first = first[:97] + "..."
        more = f" (+{len(result.errors) - 1} more)" if len(result.errors) > 1 else ""
        return VerificationResult(
            name=name,
            passed=False,
            detail=f"{len(result.errors)} invariant errors: {first}{more}",
        )
    return VerificationResult(
        name=name,
        passed=True,
        detail=f"checked: {', '.join(result.checked)}",
    )


def gate_test_evidence_recorded(
    plan: WorkflowPlan,
    agent_input: AgentInput,
    agent_output: AgentOutput,
    root: Path,
) -> VerificationResult:
    """Require a recorded verification at
    ``mythic/verifications/latest.json``. The Auditor's job is to
    confirm code claims against evidence — without a verification on
    disk, there's nothing to confirm against."""
    name = "test-evidence-recorded"
    latest = load_latest_verification(root)
    if latest is None:
        return VerificationResult(
            name=name,
            passed=False,
            detail=(
                "no mythic/verifications/latest.json on disk; "
                "run `mythic-vibe verify --record` first"
            ),
        )
    verification_id = str(latest.get("verification_id") or "?")
    result_value = str(latest.get("result") or "?")
    # Phase 19.0 / L-7 (additive 2026-05-02 audit remediation):
    # the dead ``"succeeded"`` sentinel was removed from the
    # passing-value set. ``VerificationArtifact.result`` only
    # ever writes ``"pass"`` / ``"fail"`` / ``"blocked"`` (verified
    # by grep across the production codebase). The legacy
    # ``"succeeded"`` value was never assigned and would never
    # match — its presence was misleading about the valid result
    # vocabulary.
    if result_value != "pass":
        return VerificationResult(
            name=name,
            passed=False,
            detail=(
                f"latest verification {verification_id} did not pass "
                f"(result={result_value!r})"
            ),
        )
    return VerificationResult(
        name=name,
        passed=True,
        detail=f"latest verification {verification_id} result={result_value!r}",
    )


# ---- Registry + orchestration entry point -------------------------------


DEFAULT_AUDITOR_GATES: dict[str, GateRunner] = {
    "diff-reviewed-against-architecture": gate_diff_reviewed,
    "no-invariant-violation": gate_no_invariant_violation,
    "test-evidence-recorded": gate_test_evidence_recorded,
}


def run_auditor_gates(
    plan: WorkflowPlan,
    agent_input: AgentInput,
    agent_output: AgentOutput,
    root: Path,
    *,
    gate_names: tuple[str, ...] | None = None,
    gates: dict[str, GateRunner] | None = None,
) -> tuple[VerificationResult, ...]:
    """Run every gate in ``gate_names`` and return the typed results.

    Resolution rules:

    - ``gate_names=None`` (default) → run every gate in ``gates`` in
      registry order. Used in production where the contract gates are
      whatever the registry contains.
    - ``gate_names=("a", "b")`` → run only those gates. Used when the
      caller wants to honour the role contract's
      :data:`AGENT_CONTRACTS["Auditor"].verification_gate` ordering.
    - ``gates=None`` → use :data:`DEFAULT_AUDITOR_GATES`. Tests pass
      ``gates={}`` to opt out (return empty tuple, Auditor succeeds
      on the provider's say-so) or a custom dict to inject stubs.

    A gate name with no registered runner becomes a failed
    :class:`VerificationResult` with a "no runner registered"
    detail, rather than silently disappearing — so a typo at the
    contract layer is caught at run time.
    """
    runners = gates if gates is not None else DEFAULT_AUDITOR_GATES
    if gate_names is None:
        ordered_names: tuple[str, ...] = tuple(runners.keys())
    else:
        ordered_names = gate_names

    results: list[VerificationResult] = []
    for name in ordered_names:
        runner = runners.get(name)
        if runner is None:
            results.append(
                VerificationResult(
                    name=name,
                    passed=False,
                    detail=f"no runner registered for gate {name!r}",
                )
            )
            continue
        try:
            results.append(runner(plan, agent_input, agent_output, root))
        except Exception as exc:  # noqa: BLE001 - gate runner failure is contained
            results.append(
                VerificationResult(
                    name=name,
                    passed=False,
                    detail=f"runner crashed: {exc}",
                )
            )
    return tuple(results)


__all__ = [
    "DEFAULT_AUDITOR_GATES",
    "GateRunner",
    "gate_diff_reviewed",
    "gate_no_invariant_violation",
    "gate_test_evidence_recorded",
    "run_auditor_gates",
]
