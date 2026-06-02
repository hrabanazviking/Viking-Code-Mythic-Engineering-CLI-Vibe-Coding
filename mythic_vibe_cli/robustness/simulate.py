"""Failure simulation (PH-18 Slice 18.4 — Round 4).

Injects synthetic failures across canonical CLI scenarios and
confirms graceful degradation. Each scenario runs in a fresh
temp project so the host filesystem stays untouched.

The four canonical scenarios:

- **malformed-status** — write garbage into ``mythic/status.json``
  and confirm ``cmd_status`` exits cleanly with a useful error
  rather than crashing.
- **missing-artefact** — invoke ``cmd_handoff_show`` on a
  project that has no handoff record; confirm the
  USER_INPUT_ERROR path fires with a clean message.
- **provider-unconfigured** — invoke ``cmd_ai_run`` with
  ``--no-fallback`` and an unconfigured provider; confirm
  USER_INPUT_ERROR rather than a stack trace.
- **constraint-blocking-no-override** — write a blocking
  ``mythic/constraints.md`` and run ``cmd_oath`` without
  ``--override``; confirm the policy gate returns
  UNSAFE_OPERATION_BLOCKED.

Each scenario records a typed :class:`SimulationOutcome`
(``passed``, ``exit_code``, ``stdout``, ``stderr``, ``detail``).

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import argparse
import io
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..runtime.output_guard import suspend_stdout_guard


@dataclass(frozen=True)
class SimulationOutcome:
    """Result of one synthetic failure scenario."""

    name: str
    passed: bool
    expected_exit_code: int
    actual_exit_code: int
    stdout: str
    stderr: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "expected_exit_code": self.expected_exit_code,
            "actual_exit_code": self.actual_exit_code,
            # stdout / stderr can be huge; truncate for the
            # summary payload.
            "stdout_chars": len(self.stdout),
            "stderr_chars": len(self.stderr),
            "stderr_preview": self.stderr[:200],
            "detail": self.detail,
        }


@dataclass
class SimulationReport:
    """Aggregated outcome of a full simulation run."""

    outcomes: list[SimulationOutcome] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for o in self.outcomes if o.passed)

    @property
    def failed(self) -> int:
        return sum(1 for o in self.outcomes if not o.passed)

    @property
    def ok(self) -> bool:
        return all(o.passed for o in self.outcomes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcomes": [o.to_dict() for o in self.outcomes],
            "passed": self.passed,
            "failed": self.failed,
            "total": len(self.outcomes),
            "ok": self.ok,
            "notes": list(self.notes),
        }


def _run_handler(
    handler: Callable[[argparse.Namespace], int],
    namespace: argparse.Namespace,
) -> tuple[int, str, str]:
    """Invoke a CLI handler with stdout/stderr captured."""
    out = io.StringIO()
    err = io.StringIO()
    with suspend_stdout_guard(), redirect_stdout(out), redirect_stderr(err):
        exit_code = handler(namespace)
    return exit_code, out.getvalue(), err.getvalue()


# ---- canonical scenarios ---------------------------------------------


def _scenario_malformed_status(root: Path) -> SimulationOutcome:
    from ..commands import cmd_status
    from ..exit_codes import OPERATIONAL_FAILURE, SUCCESS

    name = "malformed-status"
    project = root / "malformed-status"
    project.mkdir()
    (project / "mythic").mkdir()
    (project / "mythic" / "status.json").write_text(
        "this is not json", encoding="utf-8"
    )
    namespace = argparse.Namespace(path=str(project), json=True, quiet=False)
    exit_code, stdout, stderr = _run_handler(cmd_status, namespace)
    # Two acceptable outcomes: SUCCESS with a "valid:false" payload,
    # OR OPERATIONAL_FAILURE with a clean error. Anything else
    # (crash, raise) is a sim failure.
    passed = exit_code in {SUCCESS, OPERATIONAL_FAILURE}
    return SimulationOutcome(
        name=name,
        passed=passed,
        expected_exit_code=SUCCESS,
        actual_exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        detail=(
            "malformed status.json should not crash the CLI"
            if passed
            else "cmd_status leaked an unexpected exit code"
        ),
    )


def _scenario_missing_artefact(root: Path) -> SimulationOutcome:
    from ..commands import cmd_handoff_latest
    from ..exit_codes import USER_INPUT_ERROR

    name = "missing-artefact"
    project = root / "missing-artefact"
    project.mkdir()
    (project / "mythic").mkdir()
    namespace = argparse.Namespace(path=str(project), json=True)
    exit_code, stdout, stderr = _run_handler(cmd_handoff_latest, namespace)
    passed = exit_code == USER_INPUT_ERROR
    return SimulationOutcome(
        name=name,
        passed=passed,
        expected_exit_code=USER_INPUT_ERROR,
        actual_exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        detail=(
            "missing handoff record returns USER_INPUT_ERROR cleanly"
            if passed
            else "handoff latest leaked an unexpected exit code"
        ),
    )


def _scenario_provider_unconfigured(root: Path) -> SimulationOutcome:
    from ..commands import cmd_ai_run
    from ..exit_codes import USER_INPUT_ERROR

    name = "provider-unconfigured"
    project = root / "provider-unconfigured"
    project.mkdir()
    namespace = argparse.Namespace(
        path=str(project),
        provider="openai",
        packet="hello",
        json=True,
        dry_run=False,
        no_record=True,
        no_fallback=True,
        conversation_id="",
    )
    exit_code, stdout, stderr = _run_handler(cmd_ai_run, namespace)
    passed = exit_code == USER_INPUT_ERROR
    return SimulationOutcome(
        name=name,
        passed=passed,
        expected_exit_code=USER_INPUT_ERROR,
        actual_exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        detail=(
            "unconfigured provider with --no-fallback returns "
            "USER_INPUT_ERROR cleanly"
            if passed
            else "cmd_ai_run leaked an unexpected exit code"
        ),
    )


def _scenario_constraint_blocking(root: Path) -> SimulationOutcome:
    from ..commands import cmd_oath
    from ..exit_codes import UNSAFE_OPERATION_BLOCKED

    name = "constraint-blocking-no-override"
    project = root / "constraint-blocking"
    project.mkdir()
    (project / "mythic").mkdir()
    (project / "mythic" / "constraints.md").write_text(
        "- never break the law [blocking]\n", encoding="utf-8"
    )
    namespace = argparse.Namespace(
        path=str(project), yes=False, override=""
    )
    exit_code, stdout, stderr = _run_handler(cmd_oath, namespace)
    passed = exit_code == UNSAFE_OPERATION_BLOCKED
    return SimulationOutcome(
        name=name,
        passed=passed,
        expected_exit_code=UNSAFE_OPERATION_BLOCKED,
        actual_exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        detail=(
            "blocking constraint without --override returns "
            "UNSAFE_OPERATION_BLOCKED"
            if passed
            else "cmd_oath leaked an unexpected exit code"
        ),
    )


CANONICAL_SCENARIOS: tuple[Callable[[Path], SimulationOutcome], ...] = (
    _scenario_malformed_status,
    _scenario_missing_artefact,
    _scenario_provider_unconfigured,
    _scenario_constraint_blocking,
)


def run_simulation(*, scenarios: tuple[Callable[[Path], SimulationOutcome], ...] | None = None) -> SimulationReport:
    """Run the canonical (or supplied) scenarios. Each scenario
    runs in a fresh subdirectory of a single temp project so
    nothing leaks across scenarios."""
    chosen = scenarios if scenarios is not None else CANONICAL_SCENARIOS
    report = SimulationReport()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for scenario in chosen:
            try:
                outcome = scenario(root)
            except Exception as exc:  # noqa: BLE001 — sim failures shouldn't crash the runner
                outcome = SimulationOutcome(
                    name=getattr(scenario, "__name__", "<unknown>"),
                    passed=False,
                    expected_exit_code=0,
                    actual_exit_code=-1,
                    stdout="",
                    stderr=str(exc),
                    detail=f"scenario raised: {type(exc).__name__}: {exc}",
                )
            report.outcomes.append(outcome)
    return report


__all__ = [
    "CANONICAL_SCENARIOS",
    "SimulationOutcome",
    "SimulationReport",
    "run_simulation",
]
