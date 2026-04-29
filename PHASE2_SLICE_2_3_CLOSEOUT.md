---
title: "Phase 2 — Slice 2.3 Close-out (Workflow-Phase Capture Commands)"
phase: PH-02
slice: 2.3
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 26ee284
head_at_close: 8be5745
test_baseline_open: 327 + 14 subtests
test_baseline_close: 340 + 14 subtests
slash_builtins_open: 46
slash_builtins_close: 51
ruff_status: clean
mypy_status: clean
status: complete
new_findings: none
---

# Phase 2 Slice 2.3 — Workflow-Phase Capture Commands Close-out

## Purpose

Implement the five workflow-phase capture commands from the original
production-roadmap stage 4: `intent`, `constraints`, `architecture`,
`plan`, `build`. Each writes a Mythic Phase Record to
`mythic/checkins/<iso-timestamp>-<phase>.md` so the operator's
narrative for each phase becomes a durable artifact.

Strictly additive: no existing handler changed, no argparse
subcommand removed, no slash entry renamed.

## What landed

### Public command surface

```bash
mythic-vibe intent capture        --task X --summary Y [...]
mythic-vibe constraints capture   --task X --summary Y [...]
mythic-vibe architecture capture  --task X --summary Y [...]
mythic-vibe plan capture          --task X --summary Y [...]
mythic-vibe build capture         --task X --summary Y [...]
```

Common flags on every `capture` subcommand:

| Flag | Required | Purpose |
|---|---|---|
| `--task` | yes | Short task name (also recorded inside the file) |
| `--summary` | yes | One-paragraph summary for the phase |
| `--note` | no, repeatable | Additional bullet points |
| `--confidence` | no | One of `high` / `medium` / `low` / `unspecified` |
| `--risk` | no | Free-form short risk note |
| `--next-step` | no | What the operator intends to do next |
| `--operator` | no | Override `$USER` / `$USERNAME` for the record header |
| `--path` | no | Project directory (default `.`) |
| `--dry-run` | no | Preview without writing |
| `--json` | no | Machine-readable output |
| `--quiet` / `--verbose` | no | Standard runtime flags |

### File layout written

```
mythic/
  checkins/
    2026-04-29T19-21-05Z-intent.md
    2026-04-29T19-22-30Z-constraints.md
    2026-04-29T19-25-12Z-architecture.md
    ...
```

ISO 8601 timestamp with hyphenated time (NTFS-safe), then phase name,
then `.md`. Each file uses the canonical Mythic Phase Record template
from the production roadmap stage 4 spec.

### Phase Record template

```markdown
# Mythic Phase Record

- Phase: <phase>
- Task: <task>
- Timestamp: <iso-timestamp>
- Operator: <operator>
- Confidence: <high|medium|low|unspecified>
- Risk: <free-form text or "unspecified">

## Summary

<one-paragraph summary>

## Notes

- <bullet 1>
- <bullet 2>
- (or "(none)" if no --note flags supplied)

## Action Taken

(filled in during the build phase or after this capture)

## Verification

(filled in during the verify phase)

## Reflection

(filled in during the reflect phase)

## Next Step

<from --next-step or "(not specified)">
```

### Implementation notes

- A single `_write_phase_record(args, *, phase)` helper in
  `commands.py` is the shared body. The five `cmd_<phase>_capture`
  functions are one-line forwarders that pin the phase string.
- Each phase parent has a per-phase dispatcher
  (`cmd_intent_dispatch`, `cmd_constraints_dispatch`, ...) that today
  only routes `capture` but leaves room for future `show` / `list`
  subcommands without rewriting the surface.
- Subparser dest names use a phase-specific suffix
  (`intent_command`, `constraints_command`, etc.) — the F-023 pattern
  from slice 2.2. No risk of clobbering top-level `dest="command"`.
- `_filename_safe_timestamp` strips colons from the ISO timestamp so
  every phase record file is writable on Windows / NTFS.
- The argparse parsers were built in a `for _phase in (...):` loop in
  `app.py` so the five surfaces stay structurally identical and any
  future flag addition only needs editing in one place.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 327 | **340** (+13) |
| Slash builtin entries | 46 | **51** |
| Argparse handlers | 44 unique | **49 unique** |
| Ruff / mypy | clean | clean |

## Tests added (13)

- `PhaseCaptureHappyPathTests`
  - `test_each_phase_writes_record_with_template_fields` — parametric over all five phases.
- `PhaseCaptureFilenameShapeTests`
  - `test_filename_uses_iso_timestamp_with_safe_separators`
  - `test_filename_has_no_colons` — Windows portability invariant.
- `PhaseCaptureDryRunTests`
  - `test_dry_run_writes_no_file`
  - `test_dry_run_json_payload_shape`
- `PhaseCaptureFieldRenderingTests`
  - `test_repeated_note_flags_render_as_bullet_list`
  - `test_no_notes_renders_none_marker`
  - `test_confidence_risk_and_next_step_recorded`
- `PhaseCaptureMissingFieldTests`
  - `test_missing_task_argparse_blocks` — required=true at parser level.
  - `test_missing_summary_argparse_blocks`
  - `test_blank_task_after_strip_returns_user_error` — handler-side guard against empty strings that argparse accepts.
- `PhaseCaptureDispatcherFallthroughTests`
  - `test_intent_dispatcher_unknown_subcommand_emits_error`
  - `test_build_dispatcher_unknown_subcommand_emits_error`

## What this slice deliberately did not do

- Did not implement `<phase> show` or `<phase> list` — the dispatcher
  pattern is in place; the subcommands wait for a future operator
  need.
- Did not gate phase progression (e.g., refusing `architecture
  capture` if no `intent capture` exists yet). The production roadmap
  flagged this as a future enhancement; PH-14 (Policy Engine) is the
  natural home.
- Did not surface phase records in `status` / `next` output. The
  status command still reads from `mythic/status.json`, not from the
  per-phase markdown records. PH-03 / PH-04 (forge + TUI) will wire
  these together.
- Did not validate that `--summary` is well-formed Markdown. The
  text is recorded verbatim.
- Did not auto-populate the `Action Taken` / `Verification` /
  `Reflection` sections — those remain operator-filled placeholders
  until later phases grow the workflow.

## Phase 2 progress

| Slice | Status |
|---|---|
| 2.1 catalog mirror | ✅ done |
| 2.2 dev-tool shortcuts | ✅ done |
| 2.3 workflow-phase capture | ✅ done |
| 2.4 provider/AI aliases | PH-03 dependency |
| 2.5 diagnostic aliases | PH-11 dependency |
| 2.6 plugin-contributed slash | PH-04 dependency |
| 2.7 slash help & introspection | open |
| 2.8 REPL/TUI/plugin parity tests | open |

## Next slice options

Three viable next moves under Phase 2 alone:

1. **Slice 2.7 — slash help & introspection** — `/help <command>`
   prints the underlying argparse help; `mythic-vibe slash inspect`
   shows full provenance. No new dependencies.
2. **Slice 2.8 — REPL/TUI/plugin parity tests** — lock in that every
   slash entry resolves identically through every surface. Test-only
   slice, no behaviour change.
3. **Begin Phase 3 (Multi-Agent Forge)** — slice 3.1 (agent contract
   spec) is dependency-free and builds the foundation for slices 2.4
   and 2.5.

The slices that depend on later phases (2.4, 2.5, 2.6) need their
dependency phase to ship first.
