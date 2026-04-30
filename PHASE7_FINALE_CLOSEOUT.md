---
title: "Phase 7 — Finale (Voice & Multimodal)"
phase: PH-07
slices: 7.1, 7.2, 7.3, 7.4
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: 716b5f5
phase_close_head: b0fa860
phase_open_tests: 1005 + 14 subtests
phase_close_tests: 1042 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 7 — Voice & Multimodal (Finale)

## What Phase 7 was for

Optional voice-to-intent input (Whisper) and TTS notification
output (Chatterbox), behind feature flags. Strictly local-first;
no cloud speech services in the default path.

## Architecture choice (recorded for the future operator)

Master roadmap target backends are heavyweight (whisper:
torch + ffmpeg; chatterbox: torch + audio drivers; sounddevice:
PortAudio). Pragmatic adaptation:

- **Orchestration layer ships pure-stdlib.** Every voice surface
  goes through a typed adapter Protocol; the CLI / argparse /
  test harness build cleanly without any audio dep.
- **Real backends are opt-in via try-import.** Constructor
  raises `MissingExtraError` with a clean install hint when the
  package isn't importable; orchestrator catches and surfaces in
  `result.error`.
- **Strictly local-first.** Whisper / Chatterbox adapters are
  local-only; cloud APIs are out of scope.
- **Default-disabled.** `MYTHIC_VOICE_TTS_ENABLED` defaults to
  False; `voice transcribe` defaults to the stub engine.

This makes the phase **fully testable on any platform** without
audio hardware or downloaded model weights — the stub engine
reads text fixtures verbatim and the TTS stub logs to stderr.

## Slice-by-slice ledger

### Slice 7.1 — `mythic-vibe voice transcribe`
- New `mythic_vibe_cli/voice/__init__.py` package.
- `mythic_vibe_cli/voice/transcribe.py` — `TranscriptionRequest`
  / `TranscriptionResult` / `Transcriber` Protocol /
  `StubTranscriber` / `WhisperTranscriber` / `make_transcriber` /
  `transcribe()` orchestrator.
- `voice transcribe --file PATH [--engine stub|whisper] [--language
  LANG] [--model NAME]` subcommand.
- `MissingExtraError` raised by Whisper constructor when
  `openai-whisper` not importable; orchestrator catches and
  surfaces install hint in `result.error`.

### Slice 7.2 — `--capture-intent` wiring
- `voice transcribe --capture-intent --task TASK` pipes the
  transcription into a fresh `mythic/checkins/<ts>-intent.md`
  Mythic Phase Record via the slice 2.3 `_write_phase_record`
  path.
- Operator must supply `--task`; missing task →
  `USER_INPUT_ERROR`.
- Failed transcription blocks the phase-record write with a
  clear error.

### Slice 7.3 — TTS notifications
- `mythic_vibe_cli/voice/tts.py` — `TTSRequest` / `TTSResult` /
  `TTSEngine` Protocol / `StubTTSEngine` (logs stderr;
  `spoken=False`) / `ChatterboxEngine` (try-import; calls
  `module.speak`) / `make_tts_engine` / `say()` orchestrator.
- `voice say "text" [--engine stub|chatterbox] [--force]`
  subcommand for direct testing.
- `MYTHIC_VOICE_TTS_ENABLED` env var (default disabled);
  `--force` overrides for direct test calls.
- Phase-transition hook (auto-speak on capture / verify /
  handoff success) **deferred** — wiring TTS into every site is
  a separate sub-slice once the engine surface is stable.

### Slice 7.4 — Cross-platform audio test harness
- Stub adapters keep tests audio-free — every test path either
  uses the stub engine or mocks the optional package's import.
- 37 tests in `tests/test_voice.py` cover every adapter, every
  factory, every CLI handler path, and the slash-catalog +
  TUI-runner allow-list.
- The harness *is* the tests — no separate fixtures module
  needed.

## Cumulative numbers

| Metric | Phase open | Phase close | Δ |
|---|---|---|---|
| Tests | 1005 | **1042** | +37 |
| Source files | 92 | **95** | +3 |
| Slash builtins | 58 | **59** | +1 (`voice`) |
| Argparse handlers | 56 | **57** | +1 (`voice` dispatch; `voice transcribe` and `voice say` are sub-actions) |
| New modules | 0 | **3** | `voice/__init__.py`, `voice/transcribe.py`, `voice/tts.py` |

Ruff + mypy clean throughout.

## Master-roadmap target table

| Gate | Status |
|---|---|
| Voice-to-intent input | ✅ slice 7.1 (stub) + slice 7.2 (capture-intent wiring) |
| Whisper backend | ✅ slice 7.1 (try-import; clean install hint when absent) |
| TTS notification output | ✅ slice 7.3 (stub) |
| Chatterbox backend | ✅ slice 7.3 (try-import; calls `module.speak` when installed) |
| Behind feature flags | ✅ TTS env-gated; `--force` for direct testing |
| Strictly local-first | ✅ no cloud APIs anywhere on the default path |
| No cloud speech in default | ✅ stub engines never touch the network |

## What Phase 7 deliberately did not do

- **Did not adopt sounddevice.** Real-microphone capture is a
  follow-up sub-slice — the foundation accepts a `--file` path
  today; mic capture would feed into the same transcribe pipeline
  via a future `--mic` flag once `sounddevice` joins the optional
  extras.
- **Did not auto-speak phase transitions.** Slice 7.3 ships the
  TTS engine surface; wiring it into capture / verify / handoff
  hook points is a separate sub-slice. Recording the wire-up
  before the engine is battle-tested would couple too many
  surfaces at once.
- **Did not support cloud STT/TTS.** The roadmap explicitly
  excludes it ("strictly local-first"). The Provider layer's
  copy-paste / OpenAI / Anthropic adapters cover cloud LLM use
  cases via prompt-text; voice stays local.
- **Did not add a TUI voice screen.** A future sub-slice could
  surface `voice say` / `voice transcribe` from the picker, but
  the CLI surface is sufficient today.

## Phase progression after PH-07

Master roadmap status snapshot:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash command surface expansion | ✅ closed |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed |
| PH-05 Knowledge graph & persistent memory | ✅ closed |
| PH-06 Local LLM sovereignty | ✅ closed (5/6; 6.4 streaming deferred) |
| PH-07 Voice & multimodal | ✅ closed (this finale) |
| PH-08 Provider routing & hardware-aware selection | ✅ closed |
| PH-13 Drift detection & self-healing | ✅ closed |
| PH-15 Conversation memory & compaction | ✅ closed |
| Other phases | open |

**Ten master-roadmap phases now closed.**

Natural follow-ups:

- **Mic-capture sub-slice** — wire `sounddevice` (optional dep)
  into a `--mic` flag on `voice transcribe`.
- **TTS phase-transition hook** — auto-speak on capture / verify
  / handoff success, gated by `MYTHIC_VOICE_TTS_ENABLED`.
- **Routing wire-up sub-slice** (deferred from PH-08) — swap
  `provider.run` for `run_with_fallback` in `cmd_ai_run`.
- **PH-09** Island Integrations (depends on PH-05 + PH-06).
- **PH-10** Plugin Ecosystem & Community Infrastructure.
- **PH-11** Security/Sandbox/Permissions.
- **PH-12** CI/CD & Deployment Integration.
- **PH-16** MCP / ACP / OpenTelemetry Protocols.
- **PH-18** Robustness Sweeps — would unblock deferred 6.4
  streaming.

## How to verify

```bash
# Stub engine (always works):
$ echo "Refactor the router into modules" > /tmp/intent.txt
$ mythic-vibe voice transcribe --file /tmp/intent.txt

# Capture intent in one go:
$ mythic-vibe voice transcribe --file /tmp/intent.txt \
    --capture-intent --task "Refactor router"
# -> writes mythic/checkins/<ts>-intent.md

# TTS stub (logs to stderr, default-disabled gate):
$ mythic-vibe voice say "hello operator" --json
# -> result.spoken=false; skipped_reason mentions MYTHIC_VOICE_TTS_ENABLED

# Force the call:
$ mythic-vibe voice say "hello" --force

# Real backends (opt-in):
$ pip install openai-whisper        # adds whisper engine
$ pip install chatterbox            # adds chatterbox engine
$ mythic-vibe voice transcribe --file audio.wav --engine whisper
$ MYTHIC_VOICE_TTS_ENABLED=1 mythic-vibe voice say "hi" --engine chatterbox
```

## How to resume

`MEMORY.md` and `project_mythic_engineering_cli_status.md` updated
to HEAD `<close-head>`. `TASK_master_roadmap_and_phase1.md` tracker
extended through this finale.
