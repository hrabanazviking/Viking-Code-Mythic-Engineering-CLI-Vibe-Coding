---
title: "Phase 6 — Local LLM Sovereignty"
phase: PH-06
slices: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 20401d9
status: in_progress
---

# Phase 6 — Local LLM Sovereignty

## Goal (master roadmap)

Make the offline path first-class. Native Ollama integration via
HTTP to the local daemon, hardware-aware model selection, streaming
responses, automatic daemon-up detection.

## Constraint reality check

Master-roadmap slice 6.1 specifies "the official `ollama` Python
client". Pragmatic adaptation: this slice ships the adapter via
**stdlib `urllib.request`** so the dep group stays empty — same
strategy the existing anthropic / openai / gemini adapters use.
Adding the `ollama` Python client as an optional extra is a
follow-up sub-slice if its higher-level features become necessary.

Slice 6.4 (streaming) requires an async refactor of `cmd_ai_run`
plus a cancellation contract. **Deferred** — kept in the master
roadmap, gated behind PH-18 robustness work that owns
`runtime.exec`'s cancel signal model.

## Slices

### 6.1 — `ai/providers/ollama.py`

- New `OllamaProvider` modelled on `AnthropicProvider`.
- HTTP-only via stdlib (`http://127.0.0.1:11434/api/generate`).
- `OLLAMA_HOST` env var override; default model via
  `OLLAMA_MODEL` (fallback: `llama3.2`).
- `validate_config()` reports daemon-up status (slice 6.2).
- Registered as `ollama` in `ProviderRegistry`.
- The placeholder `local` provider stays — `ollama` is additive,
  not a replacement.

### 6.2 — Daemon discovery

- `mythic_vibe_cli/ai/ollama_health.py` with
  `is_ollama_daemon_up(host, port, timeout) -> bool` (stdlib
  `socket.create_connection`) and a richer
  `check_ollama_health(host=None, port=None, timeout=0.5) ->
  OllamaHealth` returning a typed dataclass with reachable /
  endpoint / latency_ms.
- `OllamaProvider.validate_config()` calls into this helper.
- `mythic-vibe ai providers` already shows configured status —
  the new daemon-up info appears as an additional "details" line
  for the `ollama` row.

### 6.3 — Model picker

- New `mythic-vibe ai models --provider ollama` subcommand.
- Lists installed models via `/api/tags`.
- JSON or text output.
- Graceful when daemon is not up — surfaces the same daemon-up
  message slice 6.2 reports.

### 6.4 — Streaming output **(deferred)**

- Requires `cmd_ai_run` async refactor + cancellation contract.
- Gated behind PH-18 robustness work.

### 6.5 — Telemetry extension

- `OllamaProvider.run` calls `write_provider_log` (already exists)
  with `latency_ms` measured around the HTTP call.
- New `mythic-vibe ai telemetry [--limit N] [--provider NAME]`
  subcommand to read `mythic/ai/provider_calls.jsonl` and surface
  recent calls (timestamp / provider / model / latency / cost
  estimate).
- Other providers gain the same `latency_ms` field for
  consistency.

### 6.6 — Hardware profile detection

- New `mythic_vibe_cli/hardware.py` with
  `detect_profile() -> HardwareProfile` — CPU info via
  `platform.processor()` and `os.cpu_count()`; RAM via optional
  `psutil` (try/except — falls back to "unknown" when not
  installed).
- New `mythic-vibe hardware [--write]` subcommand. With
  `--write`, persists profile to `docs/hardware_profiles.md` (and
  JSON sidecar).

## Definition of done

- All shipped slices' tests green; existing 886 stay green.
- Ruff + mypy clean throughout.
- Each slice ships a commit + close-out memo (or a combined
  close-out at phase end).
- PHASE6_FINALE_CLOSEOUT.md after the last shipped slice.
- Tracker + memory updated; "PH-06 partially closed (5/6; streaming
  deferred)".
- Pushed.
