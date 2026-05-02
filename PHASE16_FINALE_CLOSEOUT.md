# PH-16 — Phase Finale Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `c1c1518` (this memo will land the next commit)
**Resume from:** `a135505` (PH-18 finale)

PH-16 ships three protocol adapters connecting the Mythic Vibe
CLI to the wider ecosystem of agent + observability tooling:
**MCP** (Model Context Protocol — Anthropic's open standard),
**ACP** (Agent Communication Protocol — IDE bridges), and
**OpenTelemetry** (OTLP tracing). All four slices shipped in
one bundled commit; 1642 tests pass; lint + mypy clean.

---

## What landed

| Slice | Title | Commit | Net |
|---|---|---|---|
| TASK file | — | `c0eb1d7` | +120 lines |
| 16.1 + 16.2 + 16.3 + 16.4 (bundled) | MCP server + client + ACP bridge + OTel | `c1c1518` | +1,800 lines, +58 tests |

**Test delta:** 1584 → 1642 (+58 net).
**Coverage:** 76% (held).
**Lint / type:** clean throughout.

---

## Capability summary

### Slice 16.1 — MCP server adapter

`mythic_vibe_cli/protocols/mcp_server.py` is a stdlib JSON-RPC
2.0 server speaking Anthropic's Model Context Protocol over
stdio. Each request / response is one JSON object per line —
NDJSON framing, no LSP-style headers (matches MCP spec).

Implemented methods: `initialize`, `notifications/initialized`,
`tools/list`, `tools/call`, `ping`. Unknown methods return
`METHOD_NOT_FOUND`; notifications on unknown methods are
silently ignored.

`mcp_tools.build_tool_catalogue()` derives one MCP tool per
`COMMAND_HANDLERS` entry, skipping aliases (start/imbue/evoke/
scry). Each tool's `inputSchema` is a single `argv` array of
strings — `tools/call` parses argv through the standard CLI
parser and runs the handler.

CLI: `mythic-vibe protocols mcp-server` binds the server to
stdio. Operators wire it into Claude Desktop / Cursor / etc.
via the client's MCP server config.

### Slice 16.2 — MCP client adapter

`mythic_vibe_cli/protocols/mcp_client.py` provides a JSON-RPC
2.0 client that can spawn an MCP server subprocess (via
`McpClient.spawn(argv)`) or operate against in-process pipes
(via `McpClient.from_streams`).

`call() / notify() / initialize() / list_tools() / call_tool()`
cover the standard client lifecycle. The reader skips unrelated
`id` responses while waiting for the matching request — servers
may interleave notifications mid-call. `close()` and `__exit__`
properly reap the subprocess.

### Slice 16.3 — ACP minimal IDE bridge

`mythic_vibe_cli/protocols/acp_bridge.py` is a small stdlib
JSON-RPC 2.0 shim for IDE-agent co-piloting. Three methods:
- `agent.status` — server info + active run list.
- `agent.execute(command, argv)` — run a Mythic CLI command,
  return stdout + stderr + exit_code in the response.
- `agent.cancel(run_id)` — set a `threading.Event` for the
  named run.

Run ids generated via `secrets.token_hex(6)`. The active-run
table is guarded by a `Lock`. Today's CLI is mostly synchronous
so cancellation is best-effort — the event is set but the
in-flight handler may not observe it until it returns. Future
work can wire long-running commands through `cancel_event`.

CLI: `mythic-vibe protocols acp-bridge` binds the bridge to
stdio.

### Slice 16.4 — OpenTelemetry exporter

`mythic_vibe_cli/protocols/otel.py` provides opt-in OTLP
tracing. The `command_span(name, attributes)` context manager
constructs an OpenTelemetry span when both:
- `MYTHIC_OTEL_ENABLED=1` (env flag), AND
- `opentelemetry-api` is importable.

When either condition fails, `command_span` is a **zero-cost
no-op** — no tracer construction, no span emission. Hot path
stays clean for operators who never opt in.

Exceptions raised inside the span are recorded via
`span.record_exception` + `set_status(ERROR)`, then re-raised.
Span recording failures are contained — never crash callers.

CLI: `mythic-vibe protocols otel-status` is a diagnostic
snapshot showing env flag + SDK availability + active state.
New `mythic-vibe[otel]` extra in `pyproject.toml` brings in
`opentelemetry-api`, `opentelemetry-sdk`, and the OTLP HTTP
exporter.

---

## Master-roadmap impact

PH-16 closed. All 4 slices shipped:
- 16.1 MCP server ✓
- 16.2 MCP client ✓
- 16.3 ACP bridge ✓
- 16.4 OpenTelemetry exporter ✓

**Phases now fully closed:** PH-01..16 + PH-18. (17 of 20 — 85%
of roadmap.)

PH-16 unblocks **PH-17 (Multi-Surface Access)** — its
`depends_on: [PH-04, PH-16]` is now fully satisfied.

Remaining phases: **PH-17 (newly unblocked)**, PH-19, PH-20.

**Recommended next move:** **PH-17 (Multi-Surface Access)** —
newly unblocked, builds on PH-16's protocol surfaces +
PH-04's TUI to reach across surfaces (REPL, TUI, Web, mobile,
telegram). PH-19 (Distribution) is the alternative if you want
to ship `mythic-vibe` to PyPI / brew / scoop / aur / winget
first.

---

## Operational notes

- All four protocols are **opt-in**. Default flow is unchanged
  for projects that don't invoke `protocols mcp-server` /
  `protocols acp-bridge` / set `MYTHIC_OTEL_ENABLED`.
- JSON-RPC framing across all three protocols is **NDJSON**
  (one JSON object per line) — matches the MCP spec and keeps
  the server / client / bridge implementations identical in
  shape.
- Cancellation contract via `threading.Event` mirrors PH-06
  Slice 6.4's streaming + PH-10 Slice 10.2's sandbox — one
  pattern across the codebase.
- Memory updated incrementally (per the durable rule).
- No new ADRs required. PH-17 may want ADR-0010 on multi-
  surface dispatch architecture.

---

## Update Notice — 2026-05-02 (additive)

A later audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`, HEAD `e0953b6`) re-measured the project on 2026-05-02. The original closeout above is preserved unchanged; this notice is purely additive.

- **Coverage:** any "76%" figure in this or sibling closeouts was a stale carry-over. Live measurement (`pytest --cov=mythic_vibe_cli --cov-report=term-missing`) on 2026-05-02 reports **82%** branch+line coverage on the production package (1694 passed, 1 skipped, 14 subtests). Current coverage is ~6 points higher than recorded.

— *Sólrún Hvítmynd & Runa, additive correction*
