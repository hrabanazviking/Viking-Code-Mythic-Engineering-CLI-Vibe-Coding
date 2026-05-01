# Follow-up Sub-slices — Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `301a67c`
**Resume from:** `7db32f2` (PH-07 finale)

Four deferred items from already-shipped phases, all closed in
order. Working tree clean, every commit pushed, no test leaks.

---

## What landed

| Sub-slice | Phase | Commit | Net |
|---|---|---|---|
| TASK file | — | `c07b45f` | +198 lines |
| 1. Routing wire-up | PH-08 | `03d8346` + `4c4113f` (test-isolation hot-fix) | +303 / +14 lines, +7 tests |
| 2. Mic-capture | PH-07 | `9633fdd` | +416 lines, +10 tests |
| 3. TTS phase-transition hook | PH-07 | `8dcbaf2` | +358 lines, +11 tests |
| 4. Graph auto-population | PH-05 | `301a67c` | +540 lines, +15 tests |

**Test delta:** 1042 → 1085 (+43 net across the four sub-slices).
**Coverage:** 76% (unchanged — additions trended with their tests).
**Lint / type:** clean throughout.

---

## Capability summary

### Sub-slice 1 — Routing wire-up

`mythic-vibe ai run --provider X --packet Y` now routes through
`run_with_fallback` by default. A primary failure (raised exception
or unconfigured provider) falls forward onto `copy-paste` rather
than crashing or returning `USER_INPUT_ERROR`. The JSON payload
exposes `used_provider`, `primary_provider`, `fell_back`, and a
per-attempt list. New `--no-fallback` flag preserves the legacy
direct-`provider.run` path (and its strict `USER_INPUT_ERROR` for
unconfigured providers).

Cost-guard estimation still runs against the operator's chosen
provider — the spend they consented to. If fallback fires to
copy-paste, the actual call is free; the projected spend is still
honoured against the daily cap.

**Test-isolation hot-fix:** the existing
`test_ai_providers_test_run_and_ingest_response` invoked
`app.main(["ai", "run", ...])` without `--path`, so the new
routing-attempt log leaked into the repo's cwd. Threaded the
test's tempdir into the invocation; untracked the leaked file.

### Sub-slice 2 — Mic-capture

`mythic-vibe voice transcribe --mic [--duration N]` records N
seconds (default 5.0) from the system microphone, writes a temp
WAV via stdlib `wave`, pipes the path through the existing
`Transcriber` pipeline, and cleans up the temp file in a finally
block. Cross-platform via `sounddevice` + PortAudio.

`--file` is no longer argparse-required; the handler enforces
"exactly one of --file or --mic" with a clean `USER_INPUT_ERROR`
otherwise. Missing `sounddevice` → `OPERATIONAL_FAILURE` with a
`pip install sounddevice numpy` hint.

### Sub-slice 3 — TTS phase-transition hook

New `mythic_vibe_cli/voice/notify.py` module. Single
`notify_phase(phase, status, *, message=None)` helper that speaks a
short status line on operator success events. Wired into three
sites:

- `_write_phase_record` (intent / constraints / architecture / plan
  / build captures) → `notify_phase(phase, "captured")`
- `cmd_verify` → `notify_phase("verify", result)` where result is
  `pass` / `fail` / `blocked`
- `_create_handoff` → `notify_phase("handoff", "written")`

Default-disabled via the slice 7.3 `MYTHIC_VOICE_TTS_ENABLED` env
gate. Engine exceptions are contained — they surface via
`TTSResult.error` and never crash the parent command.

### Sub-slice 4 — Graph auto-population

New `mythic_vibe_cli/context/autopopulate.py` module with two
helpers that side-effect into `mythic/graph.sqlite3`:

- `populate_from_scan(root, index)` — walks `ProjectIndex.docs /
  tests / important_files` (Python files only) and upserts
  `kind="doc"` / `kind="test"` / `kind="module"` entities tagged
  per the slice 5.3 retriever convention.
- `populate_from_checkin(root, *, phase, update_text, timestamp,
  status_path, devlog_path)` — one `kind="checkin"` entity per
  successful `workflow.check_in`, tagged `phase:<phase>` +
  `kind:checkin`.

Wired into `cmd_checkin` (after `workflow.check_in`) and `cmd_scan`
(after `indexer.build`, inside the dispatcher's `with` block).
Dry-run paths still skip — the graph DB is only created on real
runs. Best-effort throughout: any sqlite / I/O failure surfaces in
`AutoPopulateResult.errors` but never raises.

---

## Roadmap impact

All four "deferred" entries on the master tracker for already-
shipped phases now close. The status file's "Targets for tomorrow"
section under `project_mythic_engineering_cli_status.md` had four
small follow-ups at the top — all four landed in this batch.

**Phases now fully closed (no deferred items remaining):**
PH-01, PH-02, PH-03, PH-04, **PH-05** (was missing graph auto-pop),
PH-06 (5/6 still — slice 6.4 streaming refactor lives with PH-18),
**PH-07** (was missing mic + TTS hook), **PH-08** (was missing
routing wire-up), PH-13, PH-15.

**Remaining phases:** PH-09 (Island Integrations), PH-10 (Plugin
Ecosystem), PH-11 (Security/Sandbox), PH-12 (CI/CD), PH-14 (Policy
Engine — PH-11 still blocking), PH-16 (MCP/ACP/OpenTelemetry),
PH-17 (Multi-Surface Access), PH-18 (Robustness Sweeps), PH-19
(Distribution), PH-20 (v1.0.0 Sovereign OS Launch).

**Recommended next move:** PH-09 (Island Integrations) — all deps
closed, naturally next on the roadmap. PH-11 (Security/Sandbox) is
the strategic alternative if Volmarr wants to anchor security
before extending integrations.

---

## Operational notes

- All four shipped under the ME laws: stdlib-first, optional deps
  via try-import + `MissingExtraError`, default-off feature gates,
  cross-platform.
- Memory updated incrementally after each sub-slice (per the
  durable rule about not batching).
- The TASK file (`TASK_followup_subslices.md`) was the resume
  contract — written + pushed before any code touched.
- One real bug found en route: pre-existing test leaked
  `mythic/ai/provider_calls.jsonl` into the repo cwd. Hot-fixed in
  commit `4c4113f`; the routing wire-up is correct and the test now
  threads `--path tempdir` properly.
