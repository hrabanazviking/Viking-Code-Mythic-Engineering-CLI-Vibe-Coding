# TASK — Follow-up sub-slices (4 deferred items)

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `7db32f2` (PH-07 finale)

This task closes four deferred items from already-shipped phases.
Each sub-slice is a single-session-sized closing of a loose thread.
They are independent — any one can ship in isolation if a session
ends mid-task — but the natural order is the one Volmarr asked for:

1. Routing wire-up (PH-08 deferred)
2. Mic-capture (PH-07 deferred)
3. TTS phase-transition hook (PH-07 deferred)
4. Graph auto-population (PH-05 deferred)

After all four ship, the four "deferred" entries in
`project_mythic_engineering_cli_status.md` are closed and the
roadmap is clean of half-done threads inside completed phases.

---

## Sub-slice 1 — Routing wire-up (PH-08 deferred)

**Goal:** swap `provider.run` for `run_with_fallback` in `cmd_ai_run`
so the configured routing chain is honoured at runtime, not just
when explained via `mythic-vibe ai route`.

**Default behaviour:** routing on. New `--no-fallback` flag opts
out and preserves the legacy direct-`provider.run` path. Default
off would change behaviour silently across every project; we keep
the operator's choice explicit.

**Files:**
- `mythic_vibe_cli/commands.py` — `cmd_ai_run` (~line 1015–1121).
  - Build `RoutingTable.load(root)` and call `route(...)` with the
    operator's `--provider` mapped onto an injected `RoutingRule`
    so the chain is `[operator-provider, fallbacks-from-table,
    copy-paste]`. Use `run_with_fallback` with a resolver that
    walks the existing `ProviderRegistry`.
  - Surface `used_provider`, `primary_provider`, `fell_back`, and
    the per-attempt list in the JSON payload so operators can see
    which fallback fired.
  - Conversation-log auto-record uses `result.response` (the same
    `ProviderResponse` shape today) — minimal disruption.
- `mythic_vibe_cli/app.py` — add `--no-fallback` to the `ai run`
  subparser.
- `tests/test_ai_routing_runtime.py` — new integration test class
  exercising `cmd_ai_run` end-to-end with a mocked registry: one
  test for "primary succeeds, no fallback", one for "primary fails,
  copy-paste catches", one for `--no-fallback` opt-out preserving
  legacy behaviour.

**Acceptance:**
- All existing tests pass.
- `cmd_ai_run` defaults to fallback chain.
- Operators get `used_provider`/`fell_back` fields in JSON output.
- `--no-fallback` explicit opt-out works.

**Progress:** [ ] not started

---

## Sub-slice 2 — Mic-capture (PH-07 deferred)

**Goal:** `mythic-vibe voice transcribe --mic [--duration N]` records
audio from the system microphone (via `sounddevice` + `soundfile`)
to a temp WAV, then pipes the path into the existing Transcriber
pipeline.

**Optional dep:** `sounddevice` + `soundfile` via try-import.
`MissingExtraError` with install hint when missing. Cross-platform
(works on Linux ALSA / macOS CoreAudio / Windows WASAPI).

**Files:**
- `mythic_vibe_cli/voice/transcribe.py` — new `MicSource` helper
  + `record_to_temp_wav(duration, sample_rate, channels)` function.
- `mythic_vibe_cli/app.py` — add `--mic` (action="store_true") and
  `--duration` (float, default 5.0) flags to `voice transcribe`.
  Make `--file` not-required when `--mic` is set; require exactly
  one of the two.
- `mythic_vibe_cli/commands.py:cmd_voice_transcribe` — when `--mic`
  is set, call `record_to_temp_wav` first and substitute its path
  into the `TranscriptionRequest`. On `MissingExtraError`, surface
  the install hint cleanly. Always clean up the temp file.
- `tests/test_voice.py` — new test class covering: argparse parses
  `--mic --duration 3`, mocked recorder produces a temp wav and
  feeds it into a stub transcriber, missing-dep path raises
  `MissingExtraError` with the expected install hint.

**Acceptance:**
- `--mic` records when sounddevice present; clean error otherwise.
- `--file` and `--mic` are mutually exclusive (or `--mic` overrides).
- Temp WAV is cleaned up after transcription.

**Progress:** [ ] not started

---

## Sub-slice 3 — TTS phase-transition hook (PH-07 deferred)

**Goal:** auto-speak on `capture` / `verify` / `handoff` success
when `MYTHIC_VOICE_TTS_ENABLED=1`. Single `notify_phase(phase,
status, *, message=None)` helper called from
`_write_phase_record`, `cmd_verify` (after success), and the
handoff writers.

**Default behaviour:** TTS is gated on `MYTHIC_VOICE_TTS_ENABLED`
(slice 7.3 env). The hook is silently a no-op when the gate is
off — no extra env var to set per phase.

**Files:**
- `mythic_vibe_cli/voice/notify.py` — new module with
  `notify_phase(phase, status, *, message=None) -> TTSResult` and
  a `compose_phase_message(phase, status, *, override)` helper that
  picks default phrasing per phase (e.g. "Intent capture recorded",
  "Verification passed", "Handoff written").
- `mythic_vibe_cli/commands.py`:
  - `_write_phase_record` — call `notify_phase(phase, "captured")`
    on the success path (after the file write).
  - `cmd_verify` — call `notify_phase("verify", "pass")` on
    success, `notify_phase("verify", "fail")` on failure if
    desired (slim version: pass-only first cut).
  - `_create_handoff` — call `notify_phase("handoff", "written")`
    after `write_handoff_record`.
- `tests/test_voice.py` — new test class for `notify.py`:
  composing default messages per phase, env-gate respected,
  injectable engine for assertion.

**Acceptance:**
- All existing tests pass — calls are no-ops when env unset.
- Setting `MYTHIC_VOICE_TTS_ENABLED=1` in a test fires the hook
  and the stub engine logs the expected text.
- One commit per integration site OR a single commit with all
  three sites + tests (we'll choose at implementation time).

**Progress:** [ ] not started

---

## Sub-slice 4 — Graph auto-population (PH-05 deferred)

**Goal:** hook `cmd_checkin` and `cmd_scan` to upsert entities into
`mythic/graph.sqlite3` so the slice 5.7 packet retriever has fresh
data without requiring an explicit `mythic-vibe graph` invocation.

**Entities upserted on `cmd_checkin`:**
- `(kind="checkin", name=f"{phase}-{timestamp}")` — one per
  successful check-in, path = the status file's path, metadata =
  `{phase, update_text, status_file, devlog_file}`.
- Tagged with `phase:<phase>` for retrieval.

**Entities upserted on `cmd_scan`:**
- `(kind="module", name=<dotted-path>)` for each Python module in
  the scan index (use `index.languages.get("Python", [])` or
  similar — check the actual scan output shape).
- `(kind="doc", name=<doc-path>)` for each markdown doc indexed.
- `(kind="test", name=<test-path>)` for each test file indexed.
- Tagged `language:python`, `kind:doc`, etc., per the slice 5.3
  retriever's tag-overlap ranking.

**Best-effort:** any sqlite / I/O failure during the upsert phase
is logged but never crashes the parent command (matches the slice
5.7 retriever's defensive read pattern).

**Files:**
- `mythic_vibe_cli/commands.py`:
  - `cmd_checkin` — after successful `workflow.check_in`, open a
    `GraphStore` and upsert the check-in entity.
  - `cmd_scan` — after `indexer.build`, walk the resulting index
    and upsert module/doc/test entities. Skip in dry-run.
- `tests/test_graph_store.py` (or new `test_graph_autopopulate.py`)
  — exercise both commands against a temp project, assert entities
  appear in `mythic/graph.sqlite3`, assert dry-run path skips, assert
  failure-injection (e.g. read-only graph file) doesn't crash the
  command.

**Acceptance:**
- All existing tests pass.
- `cmd_checkin` and `cmd_scan` populate the graph as a side-effect.
- Dry-run paths still skip side-effects.
- A graph-write failure logs but doesn't fail the command.

**Progress:** [ ] not started

---

## Operational notes

- ME laws apply: stdlib-first, optional deps via try-import +
  `MissingExtraError`, default-off feature gates, cross-platform.
- After each sub-slice ships, update `project_<name>_status.md`
  and `MEMORY.md` quick facts immediately (don't batch).
- Each sub-slice should be its own commit (or 2-3 if the test +
  implementation split helps review). Push after each commit.
- Final close-out memo (`FOLLOWUP_SUBSLICES_CLOSEOUT.md`) goes in
  after all four ship, summarising what closed and what tests grew.
