"""Approval modes (PH-11 Slice 11.1).

Three operator-approval modes for sensitive actions:

- ``"suggest"``  — prompt the operator before every action.
- ``"auto"``     — run without prompting (CI / scripted flows).
- ``"partial"``  — allow read actions, prompt for write actions.

Configured per-project via ``mythic/security.toml``:

.. code-block:: toml

    [approval]
    mode = "suggest"

CLI invocations override per-call via ``--approval suggest|auto|partial``.

A sensible default is auto-resolved when no config or CLI flag
is set:

- Interactive TTY → ``"suggest"`` (operator gets prompts).
- Non-TTY (CI, redirected stdin/stdout) → ``"auto"``.

This keeps scripted flows from blocking on stdin while still
prompting when a human is at the keyboard. The conservative
``"suggest"`` default for TTYs maps to "ask first" — operators
explicitly opt into ``"auto"`` when they want unattended runs.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal


ApprovalMode = Literal["suggest", "auto", "partial"]
ApprovalAction = Literal["read", "write", "exec"]
APPROVAL_MODES: tuple[ApprovalMode, ...] = ("suggest", "auto", "partial")
APPROVAL_ACTIONS: tuple[ApprovalAction, ...] = ("read", "write", "exec")


@dataclass(frozen=True)
class ApprovalDecision:
    """Result of :func:`resolve_approval`. ``approved`` is the
    final yes/no; ``mode`` and ``action`` echo the inputs;
    ``prompted`` flags whether stdin was consulted."""

    approved: bool
    mode: ApprovalMode
    action: ApprovalAction
    prompted: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "mode": self.mode,
            "action": self.action,
            "prompted": self.prompted,
            "reason": self.reason,
        }


# Type alias for the prompt callable. Tests inject a fake
# responder; production uses :func:`_default_responder`.
PromptResponder = Callable[[str], str]


def is_interactive_tty(*, stream: Any = None) -> bool:
    """Best-effort TTY detection. Used by :func:`resolve_default_mode`
    to pick a sensible default when no config is present.

    Tests can pass a stream object with a ``.isatty()`` method.
    Production checks ``sys.stdin.isatty()``.
    """
    target = stream if stream is not None else sys.stdin
    isatty = getattr(target, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except Exception:  # noqa: BLE001 — never raise from a TTY probe
        return False


def resolve_default_mode(*, stream: Any = None) -> ApprovalMode:
    """Pick a default approval mode when no config / flag is set."""
    return "suggest" if is_interactive_tty(stream=stream) else "auto"


def normalise_mode(raw: str | None) -> ApprovalMode:
    """Coerce an arbitrary string into an ``ApprovalMode``. Unknown
    values fall back to ``"suggest"`` (the safest behaviour)."""
    cleaned = (raw or "").strip().lower()
    if cleaned in APPROVAL_MODES:
        return cleaned  # type: ignore[return-value]
    return "suggest"


def load_security_config(root: Path) -> dict[str, Any]:
    """Read ``<root>/mythic/security.toml`` if present. Returns the
    parsed dict on success; an empty dict on missing-file or any
    parse error (security config is best-effort, not load-bearing).
    """
    path = Path(root) / "mythic" / "security.toml"
    if not path.is_file():
        return {}
    try:
        try:
            import tomllib  # Python 3.11+
        except ImportError:  # pragma: no cover — 3.10 path
            import tomli as tomllib  # type: ignore[no-redef, import-not-found]
        with path.open("rb") as fh:
            payload = tomllib.load(fh)
    except Exception:  # noqa: BLE001 — never crash on bad config
        return {}
    return payload if isinstance(payload, dict) else {}


def resolve_mode(
    root: Path,
    *,
    cli_override: str | None = None,
    stream: Any = None,
) -> ApprovalMode:
    """Pick the active mode for a CLI invocation.

    Resolution order (first wins):
    1. CLI override (``--approval suggest|auto|partial``).
    2. ``mythic/security.toml [approval] mode = "..."``.
    3. Default heuristic (TTY → ``"suggest"``, else ``"auto"``).
    """
    if cli_override:
        return normalise_mode(cli_override)
    config = load_security_config(root)
    approval = config.get("approval") if isinstance(config, dict) else None
    if isinstance(approval, dict):
        mode = approval.get("mode")
        if isinstance(mode, str) and mode.strip():
            return normalise_mode(mode)
    return resolve_default_mode(stream=stream)


def _default_responder(prompt: str) -> str:
    """Default stdin responder. Reads a line from stdin and returns
    it stripped. Empty input is treated as "no" (the conservative
    default — operators must explicitly approve)."""
    try:
        return input(prompt).strip().lower()
    except EOFError:
        return ""
    except Exception:  # noqa: BLE001 — never crash on weird stdin states
        return ""


def resolve_approval(
    *,
    mode: ApprovalMode,
    action: ApprovalAction,
    description: str,
    responder: PromptResponder | None = None,
) -> ApprovalDecision:
    """Resolve approval for a single action under the given mode.

    Decision matrix:

    +---------+---------+---------+---------+
    | mode    | read    | write   | exec    |
    +=========+=========+=========+=========+
    | auto    | ✓ auto  | ✓ auto  | ✓ auto  |
    +---------+---------+---------+---------+
    | suggest | prompt  | prompt  | prompt  |
    +---------+---------+---------+---------+
    | partial | ✓ auto  | prompt  | prompt  |
    +---------+---------+---------+---------+

    The ``description`` is shown to the operator alongside the
    prompt so they can identify what's about to happen.
    """
    if mode == "auto":
        return ApprovalDecision(
            approved=True,
            mode=mode,
            action=action,
            prompted=False,
            reason="auto-approve mode",
        )
    if mode == "partial" and action == "read":
        return ApprovalDecision(
            approved=True,
            mode=mode,
            action=action,
            prompted=False,
            reason="partial mode allows read actions",
        )

    # suggest mode (or partial + non-read action) → prompt operator.
    actual_responder = responder if responder is not None else _default_responder
    prompt = (
        f"[approval] {action} action: {description}\n"
        f"  → approve? [y/N] "
    )
    answer = actual_responder(prompt)
    approved = answer in {"y", "yes"}
    return ApprovalDecision(
        approved=approved,
        mode=mode,
        action=action,
        prompted=True,
        reason=f"operator answered {answer!r}",
    )


__all__ = [
    "APPROVAL_ACTIONS",
    "APPROVAL_MODES",
    "ApprovalAction",
    "ApprovalDecision",
    "ApprovalMode",
    "PromptResponder",
    "is_interactive_tty",
    "load_security_config",
    "normalise_mode",
    "resolve_approval",
    "resolve_default_mode",
    "resolve_mode",
]
