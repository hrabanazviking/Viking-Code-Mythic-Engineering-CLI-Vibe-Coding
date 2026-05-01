# TASK — PH-06 Slice 6.4: Streaming output + cancellation

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `56bbd71` (PH-12 finale)

Closes the last open slice in PH-06 (Local LLM Sovereignty).
Master roadmap spec:

> Slice 6.4 — Streaming output. TUI and CLI both render token
> stream with cancellation support via `runtime.exec`'s cancel
> signal model.

This slice implements provider-side streaming (Ollama native;
generic fallback for providers that don't support it) and a
new `mythic-vibe ai stream` CLI surface that emits chunks to
stdout as they arrive. Cancellation uses the same
`threading.Event` pattern `runtime.exec_command` already uses.

TUI integration is **out of scope** for this slice — the TUI's
2-second refresh model would need its own async story to render
streaming chunks live. Slice 6.4's goal here is the streaming
contract + CLI consumer; TUI streaming is a future PH-04
follow-up.

---

## Step 1 — streaming contract + base `StreamChunk` + fallback

**Goal:** add a typed streaming surface to
`mythic_vibe_cli/ai/providers/base.py` so every provider has a
stable streaming contract. Providers that don't natively stream
(`copy-paste`, `local`, `openai`/etc HTTP-call providers) get a
default fallback that wraps `run()` into a single chunk.

**Files:**
- `mythic_vibe_cli/ai/providers/base.py` — add:
  - `StreamChunk` frozen dataclass (`text`, `done`, `usage`,
    `metadata`).
  - `StreamingProvider` runtime_checkable Protocol with
    `run_stream(packet, *, cancel_event=None, dry_run=False) ->
    Iterator[StreamChunk]`.
  - `single_chunk_stream(provider, packet, *, dry_run, cancel_event)` —
    helper that adapts a non-streaming `run()` into the streaming
    contract.

**Acceptance:** existing tests pass. New tests cover the
fallback wrapper emitting exactly one chunk with `done=True`.

**Progress:** [ ] not started

---

## Step 2 — Ollama native streaming

**Goal:** flip `OllamaProvider.run_stream` to use Ollama's
`stream: True` mode. Ollama's HTTP API returns NDJSON (one JSON
object per line); each line carries either an incremental
`response` chunk or the final `done: true` packet with usage
stats.

**Files:**
- `mythic_vibe_cli/ai/providers/ollama.py` — add `run_stream`
  method. Parses NDJSON via `http_resp.readline()` loop. Yields
  `StreamChunk(text=chunk, done=False)` per token until the
  `done: true` line, then yields final
  `StreamChunk(text="", done=True, usage={...}, metadata={...})`.
- Honours `cancel_event`: checks between chunks; on set, closes
  the response and yields a final chunk with
  `metadata["cancelled"]=True`.

**Acceptance:** Ollama streaming smoke-test parses a fake NDJSON
stream end-to-end. Cancellation test confirms `cancel_event.set()`
mid-stream stops emission.

**Progress:** [ ] not started

---

## Step 3 — `mythic-vibe ai stream` CLI command

**Goal:** new top-level subcommand that takes the same
`--provider` + `--packet` shape as `ai run`, but emits chunks
to stdout as they arrive.

**Files:**
- `mythic_vibe_cli/commands.py` — `cmd_ai_stream`. Calls the
  provider's `run_stream` (falling back to `single_chunk_stream`
  for non-streaming providers). Renders each chunk's `.text`
  to stdout (no newline between chunks — operators see a
  flowing output). On Ctrl-C / SIGINT, sets the cancel_event
  and the stream stops cleanly.
- `mythic_vibe_cli/app.py` — argparse subcommand
  `mythic-vibe ai stream --provider X --packet Y [--json]`.
  When `--json` is set, emits one JSON line per chunk.

**Acceptance:** chunks render to stdout in order; final usage
stats land in the last chunk; `--json` mode emits NDJSON;
Ctrl-C cancellation works.

**Progress:** [ ] not started

---

## Step 4 — Closeout + memory update

- `SLICE_6_4_CLOSEOUT.md` — summary memo.
- Update `project_mythic_engineering_cli_status.md` to
  reflect PH-06 fully closed (6/6).
- Update `MEMORY.md`.
- Push.

---

## Operational notes

- ME laws: stdlib-first (no `httpx` / `aiohttp`), default-off
  feature gates, cross-platform.
- Cancellation contract uses `threading.Event` to mirror
  `runtime.exec_command`'s shape; no `asyncio` is introduced
  (keeps the surface synchronous and predictable).
- The streaming contract is **additive** — every existing
  caller of `provider.run()` continues to work unchanged.
- TUI integration deliberately out of scope; landed as a future
  PH-04 follow-up.
