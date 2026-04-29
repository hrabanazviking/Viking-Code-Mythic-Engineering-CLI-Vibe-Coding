# TASK — Wire `before_packet` / `after_packet` Emitters

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `97dea12` — `PluginHookDispatcher` + `cmd_scan` first emitter.

---

## Why this slice

`cmd_scan` is the only emitter so far. Six declared hooks remain. The packet pair (`before_packet` / `after_packet`) is the second-most-touched lifecycle in the CLI — every packet artifact written to disk should fire both hooks. Plugins that observe packet creation (e.g., audit, telemetry, derivation pipelines) need the events to do their job.

## Goal

Land emissions at three packet-write call sites, all using the same `PluginHookDispatcher` pattern proven by `cmd_scan`:

1. **`cmd_packet_create`** — primary single-packet writer. Aliased by `cmd_codex_pack` (delegates) which is also reached via the `evoke` and `codex-pack` command names; one wiring covers all three.
2. **`cmd_packet_ingest`** — packet ingestion writer.
3. **`cmd_workflow_plan --packets`** — generates one packet per workflow step inside a loop. One dispatcher instance, N before/after pairs.

## Payload contract

Stable small-dict payloads, no large `index` blob, no rendered packet text:

```text
before_packet:
  {
    "source": "<command alias used>",  # e.g., "packet create", "evoke", "packet ingest", "workflow plan"
    "path": "<absolute project root>",
    "phase": "<phase>",
    "role": "<role>",
    "task": "<task text>",
    "audience": "<audience>",
    "format": "<output format>",
  }

after_packet:
  before_packet payload + {
    "packet_id": "<PKT-NNNNNN>",
    "packet_path": "<absolute path to the rendered packet>",
  }
```

## Out of scope

- `before_verify`/`after_verify` and `before_reflect`/`after_reflect` — separate slices each
- Refactoring `cmd_codex_pack` to do anything other than delegate to `cmd_packet_create`
- Migrating the bridge itself to be dispatcher-aware (the bridge stays plugin-agnostic; emission lives in command code)

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/commands.py` | Wire dispatcher around the three packet-write call sites |
| `tests/test_cli_kernel.py` | Add integration tests for each emission site + dry-run/non-packet skip |
| `docs/COMMAND_CONTRACTS.md` | Update plugin-hook section to record the new emitters |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Wire `cmd_packet_create` (real-work path; skip dry-run)
- [ ] Wire `cmd_packet_ingest` (real-work path; skip dry-run)
- [ ] Wire `cmd_workflow_plan --packets` loop (skip dry-run + skip when --packets not set)
- [ ] Integration tests (≥5 cases)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] `docs/COMMAND_CONTRACTS.md` updated
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. The dispatcher block goes around the bridge call and the after-emit, NOT around dry-run paths.
3. For `cmd_workflow_plan --packets`, subscribe once, emit per packet — N before/after pairs in one dispatcher.
4. Use `_command_name(args, default)` for the `source` field so aliases are surfaced correctly.
