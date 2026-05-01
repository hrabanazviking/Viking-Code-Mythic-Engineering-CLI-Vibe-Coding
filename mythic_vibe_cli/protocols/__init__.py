"""Standards-based protocol surfaces (PH-16).

Four adapters connecting the Mythic Vibe CLI to the wider
ecosystem of agent / observability tooling:

- :mod:`mcp_server` — Model Context Protocol server. Exposes
  CLI handlers as JSON-RPC tools so external agents (Claude,
  Cursor, etc.) can invoke them.
- :mod:`mcp_client` — JSON-RPC client that spawns MCP servers
  and calls their tools. Used by forge plugins to integrate
  external MCPs.
- :mod:`acp_bridge` — minimal Agent Communication Protocol
  shim for VS Code / JetBrains plugin co-piloting.
- :mod:`otel` — opt-in OpenTelemetry OTLP exporter. Tracing
  spans for every command when the deps + env flag are set.

All four protocols are **opt-in**. Default flow is unchanged.
"""

from __future__ import annotations
