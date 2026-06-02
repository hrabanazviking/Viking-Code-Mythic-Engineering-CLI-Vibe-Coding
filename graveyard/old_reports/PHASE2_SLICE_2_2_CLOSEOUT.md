---
title: "Phase 2 — Slice 2.2 Close-out (Developer-Tool Shortcuts)"
phase: PH-02
slice: 2.2
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: c49c1ae
head_at_close: a78c0bb
test_baseline_open: 310 + 14 subtests
test_baseline_close: 327 + 14 subtests
slash_builtins_open: 40
slash_builtins_close: 46
ruff_status: clean
mypy_status: clean
status: complete
new_findings: F-023
---

# Phase 2 Slice 2.2 — Developer-Tool Shortcuts Close-out

## Purpose

Six new top-level argparse subcommands and their matching slash
catalog entries: `test`, `lint`, `typecheck`, `scaffold`, `changelog`,
`version`. Each is a thin operator-ergonomics wrapper around either
existing tooling (pytest / ruff / mypy / `scripts/check_changelog.py`)
or pure-Python helpers (ADR template, version metadata).

This slice is strictly additive — no existing handler changed, no
argparse subcommand removed, no slash entry renamed.

## What landed

### Tool-runner shortcuts (test / lint / typecheck)

A shared `_run_tool()` helper in `commands.py` provides consistent
behaviour across all three:

- Default invocation:
  - `test` → pytest (auto-discovered if `tests/` exists) or
    `python -m pytest -q`
  - `lint` → `ruff check .`
  - `typecheck` → `mypy .`
- `--command argv...` overrides the default invocation.
- `--dry-run` reports the planned argv without invoking the tool.
- `--json` writes a structured payload with stdout/stderr/exit_code.
- Exit code maps to the tool's exit code: `SUCCESS` if 0, otherwise
  `VERIFICATION_FAILURE`.

The wrappers do NOT write a verification record (unlike
`mythic-vibe verify --record`). They are operator shortcuts, not
verification gates. A user who wants verification persistence keeps
using `verify`.

### `scaffold adr`

`mythic-vibe scaffold adr --title <text>` writes the next-numbered
ADR template under `docs/ADRS/`. Numbering walks every existing
`ADR-NNNN-*.md` file, takes `max(N) + 1`, and creates the slug from
the title.

Other artefact types (task / interface / invariant / risk) are
deliberately not implemented in this slice — `argparse` constrains
the `artefact` positional to `choices=["adr"]` so any other value
fails at parse time with a clear error. The full extension-point
work belongs to PH-10 slice 10.4.

### `changelog`

`mythic-vibe changelog` prints the `## [Unreleased]` section of
`CHANGELOG.md`. The walker stops at the next `## ` heading or end of
file. `--check` runs `scripts/check_changelog.py` if present and
returns its exit code; missing validator script is reported as a
clear `USER_INPUT_ERROR`.

### `version`

`mythic-vibe version` is the subcommand form of the existing root
`--version` flag, exposing the same shape from inside the slash /
shell / TUI surfaces. `--verbose` adds Python and platform metadata
to the human-readable output; `--json` always includes it.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 310 | **327** |
| Slash builtin entries | 40 | **46** |
| Argparse handlers | 38 unique | **44 unique** |
| Ruff / mypy | clean | clean |

## Argparse footgun discovered (F-023)

While wiring `--command` for the tool-runner shortcuts I hit a real
argparse interaction that's worth recording for future contributors:

### F-023 — `--command` collides with top-level `dest="command"` from subparsers

| Field | Value |
|---|---|
| Tag | CONVENTION (cross-cutting) |
| Severity | warning |
| Discovery | While running `mythic-vibe lint --dry-run`, every invocation returned `Unknown command` because `args.command` was `None`. |
| Cause | The top-level `parser.add_subparsers(dest="command")` records the chosen subcommand under `args.command`. Adding a per-subparser `--command` flag re-uses the same Namespace attribute and clobbers it (sets it to `None` when not given). |
| Resolution | Use explicit `dest="override_command"` on per-subparser flags whose user-facing name might shadow a top-level dest. Public flag stays `--command`; only the attribute renames. |
| Lesson | Whenever adding a new `--command` / `--workflow` / `--ai` / `--phase` flag at the subparser level, check the parent's subparser dest names (currently `"command"`, `"slash_command"`, `"ai_command"`, `"workflow_command"`, etc.) and explicitly override `dest=` to avoid the silent clobber. |
| Target slice | Documented here — no further code action needed. Future slices that add subparser flags should follow the dest-override pattern. |

## Pre-existing test brittleness fixed in passing

The TUI picker filter test
(`test_picker_renders_options_and_filters_on_input`) used a single
`await pilot.pause()` after `search.value = "scan"`. With the
catalog at 14 entries this was reliable; growing to 46 entries (~3×)
crossed the threshold where one frame is no longer enough for the
`Input.Changed` message to traverse the message queue and rebuild
the OptionList. Fixed by pumping five frames instead of one. This is
a test-reliability improvement, not a behaviour change.

## What this slice deliberately did not do

- Did not implement workflow-phase capture commands (`/intent`,
  `/constraints`, `/architecture`, `/plan`, `/build`) — those land
  in slice 2.3.
- Did not extend `scaffold` beyond `adr` — task / interface /
  invariant / risk wait for PH-10 slice 10.4.
- Did not auto-generate changelog entries from Conventional Commits
  — that's PH-12 slice 12.3.
- Did not rebuild the TUI command runner to surface tool exit codes
  inline — that's PH-04 work.
- Did not add `--watch` / continuous-test modes — that's a PH-03
  forge concern.

## Slice 2.2 close

All six handlers shipped, all six slash entries added, the parity
test from slice 2.1 still passes (every argparse handler has a
matching slash entry, with the same documented exclusions), and
328 tests pass green. Ruff and mypy both clean.

The slice 2.1 → 2.2 progression has grown the catalog from 14 to
46 entries (3.3×), the argparse handler set from 38 to 44 (+6),
and added 17 new tests in `test_dev_tool_shortcuts.py`.

## Next slice (PH-02 slice 2.3)

**Workflow-phase capture commands.** Implement `/intent`,
`/constraints`, `/architecture`, `/plan`, `/build` as new handlers
that write durable phase artefacts under `mythic/checkins/` (the
shape proposed in the original Production Roadmap stage 4). Each
records the operator's input as a phase record alongside the
existing `checkin` flow.
