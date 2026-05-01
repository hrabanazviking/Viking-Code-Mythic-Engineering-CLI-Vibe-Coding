# ADR-0008: Island E (Chatterbox TTS) Adapter

## Status

Accepted

## Context

Chatterbox is a third-party open-source (MIT) text-to-speech
package — voice synthesis without cloud calls. PH-07 already
wired it into the CLI as the optional `chatterbox` engine in
`mythic_vibe_cli/voice/tts.py`, behind try-import +
`MYTHIC_VOICE_TTS_ENABLED` (the broader voice gate).

PH-09 Slice 9.4 formalises the boundary so all four islands
share the same shape: ADR-governed adapter, dedicated per-island
feature flag, parity tests with the other islands.

## Decision

The PH-07 adapter at `mythic_vibe_cli/voice/tts.py:ChatterboxEngine`
is treated as Island E. Two changes formalise the contract:

1. **Per-island feature flag** — new env var
   `MYTHIC_ISLAND_CHATTERBOX_ENABLED` (default off). The
   `chatterbox` engine emits audio only when **both** of the
   following are true:
   - `MYTHIC_VOICE_TTS_ENABLED=1` (the broader voice gate)
   - `MYTHIC_ISLAND_CHATTERBOX_ENABLED=1` (this island gate)

   Either off (or both off) → the orchestrator returns a
   non-spoken `TTSResult` with a clean `skipped_reason` naming
   the missing flag. The stub engine is unchanged — it remains
   gated by the broader TTS flag only.

2. **`force=True` bypasses both** — direct testing via
   `voice say --force` continues to work without needing either
   flag.

3. **No new module** — Chatterbox already lives in
   `mythic_vibe_cli/voice/tts.py`. Adding a separate file would
   fragment the TTS implementation for no gain. The new constant
   `CHATTERBOX_ISLAND_ENV` and helper `is_chatterbox_island_enabled()`
   live in the same module as the engine.

## Why two flags

The broader `MYTHIC_VOICE_TTS_ENABLED` controls the entire voice
output surface (notify_phase, voice say, future TTS hooks). The
per-island flag controls only whether the chatterbox backend is
permitted to actually emit audio.

This separation lets operators:

- Enable TTS broadly with the stub engine only (logs to stderr,
  no audio dep needed) — useful for headless CI.
- Enable both flags in interactive sessions where the chatterbox
  audio output is wanted.
- Keep chatterbox installed but turned off (e.g. dev machines
  where the package is cached but the operator wants silence).

## Provenance

- Chatterbox is a third-party MIT-licensed Python package; not
  vendored. Operators install via `pip install chatterbox`.
- The PH-07 adapter writes new code in `mythic_vibe_cli/voice/`;
  no upstream source is copied. Per ADR-0002, no direct imports
  from the in-tree `chatterbox/` vendor mirror.

## Consequences

- Chatterbox parity with the other three islands (each has a
  dedicated `MYTHIC_ISLAND_<NAME>_ENABLED` flag).
- Backwards compatibility: existing PH-07 chatterbox usage that
  set only `MYTHIC_VOICE_TTS_ENABLED=1` will now skip audio with
  a clear message — operators must additionally set the new flag.
  Stub engine usage is unchanged.
- The DORMANT_ISLANDS.md table can show all four islands with
  matching shapes.

## Verification

```bash
# Stub engine still works with only the broader flag.
MYTHIC_VOICE_TTS_ENABLED=1 mythic-vibe voice say "hello"
# spoken=False (stub never plays audio); both flags not required

# Chatterbox now requires both flags.
MYTHIC_VOICE_TTS_ENABLED=1 mythic-vibe voice say --engine chatterbox "hello"
# skipped_reason mentions Chatterbox island disabled

MYTHIC_VOICE_TTS_ENABLED=1 \
  MYTHIC_ISLAND_CHATTERBOX_ENABLED=1 \
  mythic-vibe voice say --engine chatterbox "hello"
# real audio (when chatterbox package is installed)

# --force bypasses both gates.
mythic-vibe voice say --engine chatterbox --force "hello"

pytest tests/test_island_chatterbox.py
```
