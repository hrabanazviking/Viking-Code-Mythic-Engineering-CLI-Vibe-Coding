# TASK — PH-16 MCP / ACP / OpenTelemetry Protocols

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `a135505` (PH-18 finale)

PH-16 teaches the CLI to speak three industry-standard protocols:

- **MCP** (Model Context Protocol) — Anthropic's open standard
  for tool/resource exposure to LLM agents. JSON-RPC 2.0 over
  stdio.
- **ACP** (Agent Communication Protocol) — minimal IDE-bridge
  shim so VS Code / JetBrains plugins can co-pilot with Mythic.
- **OpenTelemetry** — opt-in OTLP exporter for observability.

**Master roadmap dependency:** `[PH-01, PH-11]` — both closed.

---

## Slice 16.1 — MCP server adapter

**Goal:** new `mythic_vibe_cli/protocols/` package with
`mcp_server.py` — a stdlib JSON-RPC 2.0 server reading requests
on stdin, writing responses on stdout. Exposes every
`COMMAND_HANDLERS` entry as an MCP tool. Methods implemented:

- `initialize` — protocol handshake.
- `tools/list` — returns tool catalogue derived from
  `COMMAND_HANDLERS` + argparse subparsers.
- `tools/call` — invokes a CLI handler with args coming from
  the JSON `arguments` object.
- `notifications/initialized` — accepts the post-init notification.

**Files:**
- `mythic_vibe_cli/protocols/__init__.py` (new package).
- `mythic_vibe_cli/protocols/mcp_server.py` — server runtime.
- `mythic_vibe_cli/protocols/mcp_tools.py` — derive tool
  schemas from CLI handlers.
- `mythic_vibe_cli/commands.py` — `cmd_protocols_mcp_server`.
- argparse + `/mcp` slash entry.
- Tests.

**Acceptance:** `mythic-vibe protocols mcp-server` boots,
responds to `initialize` + `tools/list` + `tools/call` correctly
when fed JSON-RPC frames on stdin (test uses subprocess).

**Progress:** [ ] not started

---

## Slice 16.2 — MCP client adapter

**Goal:** `mcp_client.py` — JSON-RPC 2.0 over stdio client that
can spawn an MCP server subprocess and call its tools. Used by
forge plugins to call external MCP servers (e.g., a database
MCP for the Architect agent).

**Files:**
- `mythic_vibe_cli/protocols/mcp_client.py`.
- Tests (against an in-process fake MCP server).

**Progress:** [ ] not started

---

## Slice 16.3 — ACP minimal IDE bridge

**Goal:** `acp_bridge.py` — minimal Agent Communication Protocol
shim. JSON-RPC over stdio with `agent.execute` (run a Mythic
command) and `agent.cancel` (set a threading.Event the run
respects).

**Files:**
- `mythic_vibe_cli/protocols/acp_bridge.py`.
- argparse + `/acp` slash entry.
- Tests.

**Progress:** [ ] not started

---

## Slice 16.4 — OpenTelemetry exporter

**Goal:** opt-in OTLP exporter. Try-imports
`opentelemetry-api` + `opentelemetry-exporter-otlp` (declared
in `pyproject.toml` as `mythic-vibe[otel]` extra). When
available AND `MYTHIC_OTEL_ENABLED=1`, every command emits a
span. Missing dep / flag off → graceful no-op (no crash, no
overhead).

**Files:**
- `mythic_vibe_cli/protocols/otel.py`.
- `mythic_vibe_cli/cli.py` — wrap top-level dispatch in a span.
- `pyproject.toml` — `otel` optional dep.
- Tests (against fake tracer to avoid the heavy real dep).

**Progress:** [ ] not started

---

## Phase finale

After all 4 slices ship:
- `PHASE16_FINALE_CLOSEOUT.md` — summary memo.
- Update memory + status.
- Push.

---

## Operational notes

- ME laws: stdlib-first (MCP/ACP servers + clients use only
  stdlib JSON-RPC), default-off, cross-platform.
- All four protocols are **opt-in** — no protocol surface
  activates unless the operator explicitly invokes the relevant
  command or sets the OTEL flag.
- JSON-RPC 2.0 framing: each message is one JSON object per
  line (LSP-style headers are NOT used by MCP/ACP).
- Memory updated after each slice.
