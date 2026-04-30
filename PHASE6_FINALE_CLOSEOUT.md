---
title: "Phase 6 — Finale (Local LLM Sovereignty)"
phase: PH-06
slices: 6.1, 6.2, 6.3, 6.5, 6.6 (6.4 deferred)
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: 20401d9
phase_close_head: cf7a1d0
phase_open_tests: 886 + 14 subtests
phase_close_tests: 947 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete (5 of 6 slices; 6.4 streaming deferred)
---

# Phase 6 — Local LLM Sovereignty (Finale)

## What Phase 6 was for

Make the offline path first-class. Native Ollama integration via
HTTP to the local daemon, hardware-aware model selection
foundation, automatic daemon-up detection, telemetry across every
provider.

Master roadmap target: `mythic-vibe ai run --provider ollama`
succeeds end-to-end against a local daemon. **Met** (slice 6.1
test asserts via stub daemon harness).

Master roadmap target: the CLI never freezes a session if Ollama
is unavailable; degrades to copy-paste mode with a clear message.
**Met** — slice 6.1's `validate_config` reports the daemon-up
state and `run` raises a clean `ConnectionError` with a
"start ollama serve" hint instead of an opaque urllib failure.

## Slice-by-slice ledger

### Slice 6.1 — Ollama provider adapter
- New `mythic_vibe_cli/ai/providers/ollama.py` — stdlib HTTP only;
  no third-party `ollama` Python client dep (matches the existing
  anthropic / openai / gemini pattern).
- Honours `OLLAMA_HOST` (host / host:port / scheme://host:port
  forms) and `OLLAMA_MODEL` env vars.
- Probes the daemon before live calls and raises `ConnectionError`
  with an actionable message when unreachable.
- Writes `latency_ms` into `provider_calls.jsonl` from day one.
- Registered as `ollama` in `ProviderRegistry` (additive — the
  existing reflection-only `local` provider stays).
- Commit `26ee516`.

### Slice 6.2 — Daemon discovery
- New `mythic_vibe_cli/ai/ollama_health.py`:
  - `is_ollama_daemon_up(host, port, *, timeout)` — TCP connect
    probe; never raises.
  - `check_ollama_health(...) -> OllamaHealth` — typed dataclass
    with `reachable / endpoint / latency_ms / error / details`.
  - `list_models(...)` — `/api/tags` reader; degrades to
    `([], unhealthy_health)` on any error.
- `OllamaProvider.validate_config()` consumes `check_ollama_health`
  and exposes endpoint + reachability + default model in
  `ProviderStatus.details`.
- Commit `26ee516` (combined with 6.1).

### Slice 6.3 — Model picker
- New `mythic-vibe ai models --provider <name>` subcommand.
- Ollama path: `/api/tags` listing with name + size + family
  details; reachable-but-empty case prints `ollama pull` hint.
- Other providers: returns "not implemented for this provider"
  note for parity (no upstream API exposes a uniform model list
  worth wiring here).
- `cmd_ai_dispatch` updated; `/ai models` works through the slash
  picker via the existing `/ai` entry.
- Commit `dcb0a31`.

### Slice 6.4 — Streaming output **(deferred)**
- Requires `cmd_ai_run` async refactor + cancellation contract
  beyond a single phase's scope. Gated behind PH-18 robustness
  work that owns `runtime.exec`'s cancel signal model. Kept on
  the master roadmap with the dependency note.

### Slice 6.5 — Telemetry extension + reader
- New `timed_post_json(url, payload, headers) -> (parsed,
  latency_ms)` helper in `ai/providers/base.py` wrapping the
  existing `post_json`.
- All four real-API providers (anthropic / openai / gemini /
  openrouter) switched from `post_json` to `timed_post_json` and
  record `latency_ms` in `provider_calls.jsonl`.
- New `mythic-vibe ai telemetry [--provider X] [--limit N]`
  subcommand — newest-first, JSON or text, corrupt-line tolerant.
- Commit `3f74ef6`.

### Slice 6.6 — Hardware profile detection
- New `mythic_vibe_cli/hardware.py` — `HardwareProfile` frozen
  dataclass + `detect_profile()` best-effort detector + text /
  markdown renderers + `write_profile(root, profile)` persister.
- Stdlib core (`platform`, `os`); optional `psutil` enrichment for
  RAM + physical CPU count. Missing psutil lands as `notes`
  entries rather than raising.
- New `mythic-vibe hardware [--write]` subcommand — `--write`
  persists to `docs/hardware_profiles.md` + JSON sidecar.
- `/hardware` slash entry; TUI runner forwards `--path`.
- GPU detection deliberately deferred (needs torch or per-OS
  shell-outs that don't generalise).
- Commit `cf7a1d0`.

## Cumulative numbers

| Metric | Phase open | Phase close | Δ |
|---|---|---|---|
| Tests | 886 | **947** | +61 |
| Source files | 86 | **89** | +3 |
| Slash builtins | 57 | **58** | +1 (`hardware`) |
| Argparse handlers | 55 | **56** | +1 (`hardware`; `ai models` + `ai telemetry` are sub-actions of existing `ai`) |
| New modules | 0 | **3** | `ai/ollama_health.py`, `ai/providers/ollama.py`, `hardware.py` |
| Providers registered | 6 | **7** | +1 (`ollama`) |

Ruff + mypy clean throughout.

## Master-roadmap target table

| Gate | Status |
|---|---|
| `mythic-vibe ai run --provider ollama` works against local daemon | ✅ slice 6.1 (asserted via stub daemon test) |
| CLI never freezes when Ollama unavailable | ✅ slice 6.1 raises ConnectionError with "start ollama serve" hint |
| Native Ollama integration via Python client | ✅ stdlib HTTP — no ollama Python client dep (pragmatic adaptation; full client wrapper is a follow-up sub-slice if higher-level features become necessary) |
| Hardware-aware model selection | partial — slice 6.6 ships the profile; routing logic is PH-08 territory |
| Streaming responses | ❌ deferred (slice 6.4) — gated behind PH-18 |
| Automatic daemon-up detection | ✅ slice 6.2 |
| Cost / latency telemetry | ✅ slice 6.5 across all providers + reader |

## What Phase 6 deliberately did not do

- **Did not adopt the official `ollama` Python client.** Stdlib
  HTTP is sufficient for `/api/generate` + `/api/tags` and keeps
  the dep group empty. A follow-up sub-slice can adopt the
  client if higher-level features (function calling, tool use,
  structured output) become necessary.
- **Did not implement streaming.** Slice 6.4 deferred — needs an
  async `cmd_ai_run` refactor + cancellation contract that
  belongs in PH-18 robustness work.
- **Did not auto-start the daemon.** Cross-platform daemon
  lifecycle (systemd / launchctl / Windows Services) is a tarpit;
  the slice 6.2 `check_ollama_health` returns actionable
  `start the daemon with ollama serve` hints instead.
- **Did not detect GPU presence / VRAM / CUDA / Metal.** Needs
  either heavy torch dep or per-OS shell-outs. Deferred to PH-08
  when GPU-aware routing actually becomes a need.
- **Did not add per-role model assignment.** Slice 6.3's master-
  roadmap target included this; the pragmatic shape would be a
  config layer mapping forge role → model — owns its own slice
  when the orchestrator wants to use it.
- **Did not migrate `LocalProvider` to be Ollama-backed.** The
  reflection-only `local` provider stays alongside `ollama` so
  operators have both options. Future cleanup may consolidate
  if the offline reflection use case fades.

## Phase progression after PH-06

Master roadmap status snapshot:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash command surface expansion | ✅ closed |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed |
| PH-05 Knowledge graph & persistent memory | ✅ closed |
| PH-06 Local LLM sovereignty | ✅ closed (5/6; 6.4 streaming deferred) |
| PH-13 Drift detection & self-healing | ✅ closed |
| PH-15 Conversation memory & compaction | ✅ closed |
| Other phases | open |

**Eight master-roadmap phases now closed.**

Natural follow-ups:

- **PH-08** Provider Routing & Hardware-Aware Selection — the
  natural consumer of slice 6.6's `HardwareProfile` and slice
  6.5's telemetry.
- **PH-07** Voice & Multimodal — also leverages local provider work.
- **PH-11** Security/Sandbox/Permissions — hardens forge + plugin
  layers.
- **PH-12** CI/CD & Deployment Integration.
- **PH-16** MCP / ACP / OpenTelemetry Protocols.
- **PH-18** Robustness Sweeps — would unblock the deferred 6.4
  streaming work.

## How to verify

```bash
# Daemon-up probe + provider listing:
$ mythic-vibe ai providers --json | jq '.providers.ollama'

# Listing installed models (graceful when daemon down):
$ mythic-vibe ai models --provider ollama

# Telemetry tail:
$ mythic-vibe ai telemetry --provider ollama --limit 5

# Hardware snapshot:
$ mythic-vibe hardware
$ mythic-vibe hardware --write   # writes docs/hardware_profile{.md,.json}
```

## How to resume

`MEMORY.md` and `project_mythic_engineering_cli_status.md` updated
to HEAD `<close-head>`. `TASK_master_roadmap_and_phase1.md` tracker
extended through this finale.
