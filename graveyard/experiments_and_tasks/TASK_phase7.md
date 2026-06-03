---
title: "Phase 7 — Voice & Multimodal"
phase: PH-07
slices: 7.1, 7.2, 7.3, 7.4
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 716b5f5
status: in_progress
---

# Phase 7 — Voice & Multimodal

## Goal (master roadmap)

Optional voice-to-intent input (Whisper) and TTS notification
output (Chatterbox), behind feature flags. Strictly local-first;
no cloud speech services in the default path.

## Architecture reality check

The master roadmap names heavyweight deps (sounddevice +
openai-whisper for capture, Chatterbox for TTS). Each carries
~hundreds of MB of binary wheels and (whisper) needs ffmpeg.
Pragmatic adaptation:

- **Orchestration layer ships pure-stdlib.** Every voice surface
  goes through a typed adapter Protocol so the CLI / argparse /
  test harness build cleanly without any audio dep.
- **Real backends are opt-in via try-import.** When the operator
  installs `whisper` / `sounddevice` / `chatterbox`, the matching
  adapter activates; without them, the stub adapters surface a
  clear "install the extra to enable" message.
- **Strictly local-first.** No cloud audio. The Whisper /
  Chatterbox adapters are local-only; cloud-API variants are
  out of scope.
- **Default-disabled.** `MYTHIC_VOICE_TTS_ENABLED` defaults to
  False; `mythic-vibe voice transcribe` defaults to the stub
  engine.

## Slices

### 7.1 — `mythic-vibe voice transcribe`

- New `mythic_vibe_cli/voice/__init__.py` package.
- `mythic_vibe_cli/voice/transcribe.py`:
  - `TranscriptionRequest` frozen dataclass: source (file path or
    "stub"), engine name, language, model, duration_seconds.
  - `TranscriptionResult` frozen dataclass: text, source_path,
    engine, model, language, dry_run, error.
  - `Transcriber` Protocol with `transcribe(request) ->
    TranscriptionResult`.
  - `StubTranscriber` — always works; returns canned text or the
    file's basename. Used as default + in tests.
  - `WhisperTranscriber` — try-imports `whisper`; raises
    `MissingExtraError` with install hint when absent.
  - `make_transcriber(name)` factory.
- `mythic-vibe voice transcribe --file PATH [--engine stub|whisper]
  [--language LANG] [--model NAME] [--json]` subcommand.

### 7.2 — Intent capture wiring

- New `--capture-intent` flag on `voice transcribe` that pipes the
  transcribed text into a fresh `mythic/checkins/<ts>-intent.md`
  Mythic Phase Record (re-using slice 2.3's capture writer).
- Operator must supply `--task` summarising the intent — no
  silent record creation.
- Returns the path to the written record in the JSON envelope.

### 7.3 — TTS notifications

- `mythic_vibe_cli/voice/tts.py`:
  - `TTSEngine` Protocol with `say(text) -> TTSResult`.
  - `StubTTSEngine` — logs to stderr, never plays audio.
  - `ChatterboxEngine` — try-imports the package; falls back to
    stub when missing.
  - `make_tts_engine(name)` factory.
  - `is_tts_enabled()` reads `MYTHIC_VOICE_TTS_ENABLED`.
- `mythic-vibe voice say "text" [--engine stub|chatterbox]`
  subcommand for direct testing.
- Phase-transition hook is **deferred** — wiring TTS into every
  capture / verify / handoff site is a separate sub-slice once
  the engine surface is stable.

### 7.4 — Cross-platform audio test harness

- Stub adapters (slice 7.1 + 7.3) keep tests audio-free.
- Fixture file `tests/fixtures/voice_sample.txt` simulates a
  pre-transcribed result for `--file` testing.
- Headless smoke test confirms `voice transcribe` and `voice say`
  succeed under the stub engine on any platform without audio
  hardware.
- Real backends (`WhisperTranscriber` / `ChatterboxEngine`) are
  unit-tested via mocked import to confirm the missing-extra
  error path.

## Definition of done

- All four slices' tests green; existing 1005 stay green.
- Ruff + mypy clean throughout.
- PHASE7_FINALE_CLOSEOUT.md after slice 7.4.
- Tracker + memory updated to "PH-07 fully complete".
- Pushed.

## Constraints (recorded for the future operator)

- Cross-platform: stdlib only on the must-work path.
- Open-source only (whisper MIT, chatterbox open-source).
- No cloud APIs.
- Default feature-disabled; operator explicitly opts in.
- File-based input always works (the `--file` path doesn't need
  any audio dep — the file just needs to be a readable text /
  audio file the chosen engine knows how to handle).
