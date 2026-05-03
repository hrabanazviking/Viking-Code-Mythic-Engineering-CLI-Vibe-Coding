"""Hermes Agent — programmatic control plane for Mythic Vibe CLI.

Two access modes share one core:

- **TCL** (Tool Calling Library) — in-process Python. Import
  :class:`HermesAgent` and call its methods directly.
- **HTTP API** — token-protected JSON endpoints over a stdlib
  HTTP server. Launch via ``mythic-vibe surface hermes``.

See ``docs/HERMES_AGENT.md`` for the operator + agent-author
guide.
"""

from .core import (
    HermesCore,
    Invocation,
    InvocationResult,
    InvocationStatus,
    ToolCallable,
    ToolSpec,
    emit_audit_event,
)
from .http_api import (
    DEFAULT_HOST as HTTP_DEFAULT_HOST,
    DEFAULT_PORT as HTTP_DEFAULT_PORT,
    HermesHttpConfig,
    HermesHttpServer,
    build_default_http_server,
)
from .tcl import HermesAgent, build_default_agent

__all__ = [
    "HTTP_DEFAULT_HOST",
    "HTTP_DEFAULT_PORT",
    "HermesAgent",
    "HermesCore",
    "HermesHttpConfig",
    "HermesHttpServer",
    "Invocation",
    "InvocationResult",
    "InvocationStatus",
    "ToolCallable",
    "ToolSpec",
    "build_default_agent",
    "build_default_http_server",
    "emit_audit_event",
]
