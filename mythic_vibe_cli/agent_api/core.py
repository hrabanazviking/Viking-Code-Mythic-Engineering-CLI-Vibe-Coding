"""Hermes Agent — central programmatic surface (v1.0 / PH-Hermes).

This module is the **single source of truth** for everything an
external agent can do with Mythic Vibe CLI. Both the in-process
TCL (Tool Calling Library) wrapper and the HTTP API delegate to
the registry + invoker defined here, so behaviour is identical
regardless of access mode.

Design intent:

- **Curated tool surface, not a full RPC mirror of argparse.**
  Each tool is a hand-validated, JSON-Schema-described callable
  that wraps a high-value operation. The schema is the contract
  agents see; the implementation can change without breaking
  callers.
- **Stateless invocation, stateful project root.** Each Hermes
  instance is bound to one project root. Tool calls return
  serialisable results; they don't carry hidden conversational
  state across invocations.
- **Defensive serialisation.** Every result goes through
  ``_safe_serialise`` so an exotic return value can't crash the
  HTTP layer.
- **Audit trail.** Every invocation appends one event-log line
  via the existing ``runtime/event_log`` primitive — operators
  see exactly what an agent did via ``mythic-vibe`` introspection.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal


ToolCallable = Callable[["HermesCore", dict[str, Any]], "InvocationResult"]


@dataclass(frozen=True)
class ToolSpec:
    """JSON-Schema-compatible description of one tool. Designed
    for direct use by Anthropic Tool Use, OpenAI function
    calling, and similar surfaces.

    ``input_schema`` follows JSON Schema draft 2020-12. Tools
    are introspectable via ``HermesCore.list_tools()``.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    capabilities: tuple[str, ...] = ()
    """Required runtime capabilities (read / network / subprocess /
    file-write). Maps to PH-20.3 plugin-capability vocabulary."""

    side_effects: tuple[str, ...] = ()
    """Human-readable side-effect tags (e.g. ``"writes mythic/status.json"``).
    Surfaced to operators for audit; not enforced."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": dict(self.input_schema),
            "capabilities": list(self.capabilities),
            "side_effects": list(self.side_effects),
        }


@dataclass(frozen=True)
class Invocation:
    """One tool-call request. Built by the HTTP layer or the TCL
    wrapper from operator/agent input."""

    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "args": dict(self.args),
            "request_id": self.request_id,
        }


InvocationStatus = Literal["ok", "error", "unknown_tool", "validation_error"]


@dataclass(frozen=True)
class InvocationResult:
    """One tool-call response. Defensive: ``value`` is always
    serialisable (the invoker passes it through ``_safe_serialise``)."""

    status: InvocationStatus
    value: Any = None
    error: str = ""
    elapsed_ms: float = 0.0
    tool: str = ""
    request_id: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "value": self.value,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
            "tool": self.tool,
            "request_id": self.request_id,
            "ok": self.ok,
        }


def _safe_serialise(value: Any, *, depth: int = 0, max_depth: int = 8) -> Any:
    """Coerce arbitrary Python values into a JSON-serialisable
    shape. Caps recursion at ``max_depth`` so a self-referential
    object cannot stack-overflow the HTTP layer."""
    if depth > max_depth:
        return f"<truncated at depth {max_depth}>"
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(k): _safe_serialise(v, depth=depth + 1, max_depth=max_depth)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [
            _safe_serialise(v, depth=depth + 1, max_depth=max_depth)
            for v in value
        ]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        try:
            return _safe_serialise(value.to_dict(), depth=depth + 1, max_depth=max_depth)
        except Exception as exc:  # noqa: BLE001 — defensive serialisation
            return f"<to_dict failed: {type(value).__name__}: {exc}>"
    try:
        return json.loads(json.dumps(value, default=str))
    except (TypeError, ValueError):
        return f"<unserialisable: {type(value).__name__}>"


def _validate_against_schema(
    schema: dict[str, Any], args: dict[str, Any]
) -> list[str]:
    """Minimal JSON-Schema validator — only the bits we use
    (``required``, ``type`` per property, ``enum``). Returns a
    list of human-readable error strings (empty == valid).

    We deliberately don't pull in ``jsonschema`` as a runtime
    dep — keeping Hermes stdlib-only matches the v1.0
    "runtime base has zero non-stdlib dependencies" rule.
    """
    errors: list[str] = []
    required = schema.get("required", []) if isinstance(schema, dict) else []
    if isinstance(required, list):
        for key in required:
            if key not in args:
                errors.append(f"missing required arg: {key!r}")

    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    if not isinstance(properties, dict):
        return errors

    for key, value in args.items():
        spec = properties.get(key)
        if not isinstance(spec, dict):
            continue
        expected = spec.get("type")
        if expected == "string" and not isinstance(value, str):
            errors.append(f"{key!r}: expected string, got {type(value).__name__}")
        elif expected == "integer" and not isinstance(value, int):
            errors.append(f"{key!r}: expected integer, got {type(value).__name__}")
        elif expected == "boolean" and not isinstance(value, bool):
            errors.append(f"{key!r}: expected boolean, got {type(value).__name__}")
        elif expected == "array" and not isinstance(value, list):
            errors.append(f"{key!r}: expected array, got {type(value).__name__}")
        elif expected == "object" and not isinstance(value, dict):
            errors.append(f"{key!r}: expected object, got {type(value).__name__}")

        enum = spec.get("enum")
        if isinstance(enum, list) and value not in enum:
            errors.append(
                f"{key!r}: value {value!r} not in allowed enum {enum}"
            )

    return errors


class HermesCore:
    """The central programmatic surface. One instance per project
    root. Tools are registered via :meth:`register` and invoked via
    :meth:`invoke`.

    Both the TCL wrapper (:mod:`mythic_vibe_cli.agent_api.tcl`)
    and the HTTP API (:mod:`mythic_vibe_cli.agent_api.http_api`)
    delegate here, so behaviour is identical across modes.
    """

    def __init__(self, root: Path | str = "."):
        self.root = Path(root).resolve()
        self._tools: dict[str, tuple[ToolSpec, ToolCallable]] = {}

    # -- registration ---------------------------------------------

    def register(self, spec: ToolSpec, fn: ToolCallable) -> None:
        """Register a tool. ``fn`` receives ``(core, args)`` and
        must return an :class:`InvocationResult`."""
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name!r}")
        self._tools[spec.name] = (spec, fn)

    def list_tools(self) -> list[ToolSpec]:
        """Return all registered tool specs in alphabetical order
        (stable for snapshot tests + agent introspection)."""
        return [spec for spec, _ in sorted(self._tools.values(), key=lambda pair: pair[0].name)]

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    # -- invocation -----------------------------------------------

    def invoke(self, invocation: Invocation) -> InvocationResult:
        """Run one invocation and return the result. Never
        raises — every error path produces an
        :class:`InvocationResult` with a non-ok ``status``."""
        import time

        start = time.monotonic()
        if invocation.tool not in self._tools:
            return InvocationResult(
                status="unknown_tool",
                error=(
                    f"unknown tool: {invocation.tool!r}. "
                    f"Available: {sorted(self._tools)}"
                ),
                elapsed_ms=(time.monotonic() - start) * 1000.0,
                tool=invocation.tool,
                request_id=invocation.request_id,
            )

        spec, fn = self._tools[invocation.tool]
        validation_errors = _validate_against_schema(
            spec.input_schema, invocation.args
        )
        if validation_errors:
            return InvocationResult(
                status="validation_error",
                error="; ".join(validation_errors),
                elapsed_ms=(time.monotonic() - start) * 1000.0,
                tool=invocation.tool,
                request_id=invocation.request_id,
            )

        try:
            result = fn(self, dict(invocation.args))
        except Exception as exc:  # noqa: BLE001 — Hermes never raises into the caller
            return InvocationResult(
                status="error",
                error=f"{type(exc).__name__}: {exc}",
                elapsed_ms=(time.monotonic() - start) * 1000.0,
                tool=invocation.tool,
                request_id=invocation.request_id,
            )

        # Defensive serialisation — even tool implementations
        # that return exotic types can't crash the HTTP layer.
        safe_value = _safe_serialise(result.value)
        elapsed = (time.monotonic() - start) * 1000.0
        emit_audit_event(
            self.root,
            tool=invocation.tool,
            request_id=invocation.request_id,
            status=result.status,
            elapsed_ms=elapsed,
        )
        return InvocationResult(
            status=result.status,
            value=safe_value,
            error=result.error,
            elapsed_ms=elapsed,
            tool=invocation.tool,
            request_id=invocation.request_id,
        )


def emit_audit_event(
    root: Path,
    *,
    tool: str,
    request_id: str | None,
    status: str,
    elapsed_ms: float,
) -> None:
    """Best-effort audit event for every Hermes invocation. Wired
    into the existing PH-09 ``runtime/event_log`` primitive so
    operators can see what an agent did via the same Recent
    Events panel that surfaces plugin events."""
    try:
        from ..runtime.event_log import append_event, event_log_path_for
    except ImportError:
        return
    payload = {
        "tool": tool,
        "request_id": request_id,
        "status": status,
        "elapsed_ms": round(elapsed_ms, 2),
    }
    try:
        append_event(event_log_path_for(root), "hermes_invoke", payload)
    except Exception:  # noqa: BLE001 — audit emission must never crash a tool call
        return


__all__ = [
    "HermesCore",
    "Invocation",
    "InvocationResult",
    "InvocationStatus",
    "ToolCallable",
    "ToolSpec",
    "emit_audit_event",
]
