"""SSH-readiness diagnostic (PH-17 Slice 17.3).

Runs a small set of checks that confirm the CLI is suitable for
SSH usage. Reporting only — never mutates config or state.

Checks:

- **TTY detection** — does the CLI think it has a TTY? If not,
  the slice 11.1 approval default flips to ``auto`` (correct
  for SSH non-interactive sessions).
- **Color stripping** — is ``NO_COLOR`` set OR is stdout not a
  TTY? If neither, ANSI codes will leak into log files /
  redirections.
- **TERM env var** — present and non-empty? Many SSH sessions
  inherit the local ``TERM``; bare ``TERM`` confuses the TUI.
- **Approval mode default** — what would slice 11.1 pick right
  now? In SSH automation we expect ``auto``.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SshCheck:
    """One readiness check outcome."""

    name: str
    passed: bool
    detail: str
    severity: str = "advisory"  # "advisory" | "warn"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "severity": self.severity,
        }


@dataclass
class SshDoctorReport:
    checks: list[SshCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if not c.passed and c.severity == "warn")

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [c.to_dict() for c in self.checks],
            "total": len(self.checks),
            "passed": sum(1 for c in self.checks if c.passed),
            "warnings": self.warnings,
            "ok": self.ok,
        }


def _check_tty() -> SshCheck:
    is_tty = bool(getattr(sys.stdout, "isatty", lambda: False)())
    if is_tty:
        detail = "stdout is a TTY (interactive); fine for terminal SSH"
    else:
        detail = (
            "stdout is NOT a TTY (script / piped) — slice 11.1 approval "
            "defaults to 'auto', no prompts will block"
        )
    return SshCheck(
        name="tty-detected",
        passed=True,  # always pass — the detail explains the implications
        detail=detail,
        severity="advisory",
    )


def _check_no_color() -> SshCheck:
    no_color_set = bool(os.environ.get("NO_COLOR", "").strip())
    is_tty = bool(getattr(sys.stdout, "isatty", lambda: False)())
    if is_tty or no_color_set:
        return SshCheck(
            name="color-output-safe",
            passed=True,
            detail=(
                "TTY detected — ANSI colors render correctly"
                if is_tty
                else "NO_COLOR set — ANSI codes suppressed"
            ),
        )
    return SshCheck(
        name="color-output-safe",
        passed=False,
        detail=(
            "non-TTY without NO_COLOR — ANSI codes may leak into log "
            "files / redirections. Set NO_COLOR=1 in scripted SSH flows."
        ),
        severity="warn",
    )


def _check_term_env() -> SshCheck:
    term = os.environ.get("TERM", "").strip()
    if not term:
        return SshCheck(
            name="term-env-set",
            passed=False,
            detail=(
                "TERM env var is empty — TUI rendering may use a "
                "fallback profile. Common fix: set TERM=xterm-256color."
            ),
            severity="warn",
        )
    return SshCheck(
        name="term-env-set",
        passed=True,
        detail=f"TERM={term!r}",
    )


def _check_approval_default() -> SshCheck:
    from ..security.approval import resolve_default_mode

    mode = resolve_default_mode()
    is_tty = bool(getattr(sys.stdin, "isatty", lambda: False)())
    if not is_tty and mode == "auto":
        return SshCheck(
            name="approval-default-sensible",
            passed=True,
            detail=(
                "non-TTY → approval default 'auto' (no stdin prompts will "
                "block). Override via --approval suggest|partial."
            ),
        )
    if is_tty and mode == "suggest":
        return SshCheck(
            name="approval-default-sensible",
            passed=True,
            detail=(
                "TTY → approval default 'suggest' (operator gets prompts)."
            ),
        )
    return SshCheck(
        name="approval-default-sensible",
        passed=False,
        detail=(
            f"unexpected combination: tty={is_tty} default={mode!r}. "
            "Slice 11.1's resolver picked an unusual mode for this shell."
        ),
        severity="warn",
    )


def run_ssh_doctor() -> SshDoctorReport:
    """Run all checks and return the aggregated report."""
    return SshDoctorReport(
        checks=[
            _check_tty(),
            _check_no_color(),
            _check_term_env(),
            _check_approval_default(),
        ]
    )


__all__ = [
    "SshCheck",
    "SshDoctorReport",
    "run_ssh_doctor",
]
