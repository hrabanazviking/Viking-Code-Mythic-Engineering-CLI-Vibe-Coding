---
title: "Phase 13 — Finale (Drift Detection & Self-Healing)"
phase: PH-13
slices: 13.1–13.4
opened: 2026-04-29
closed: 2026-04-29
phase_open_head: ec06f12
phase_close_head: d396de7
phase_open_tests: 686 + 14 subtests
phase_close_tests: 724 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# Phase 13 — Drift Detection & Self-Healing (Finale)

## Roadmap dependency note

Master roadmap declared `depends_on: [PH-05, PH-11]`. PH-05
(Knowledge Graph & Persistent Memory) hasn't shipped yet, and slice
13.1 was specified as "graph-backed query for orphaned functions,
undocumented modules, superseded decisions". Pragmatic adaptation:
**filesystem-heuristic v1**. When PH-05 lands, individual detectors
in `mythic_vibe_cli/drift.py` can be re-implemented over the graph
without changing the public surface. Slices 13.2 / 13.3 / 13.4
don't change either.

PH-11 (Security/Sandbox/Permissions) was notionally about safe
`heal` execution. Today's heal v2 (slice 13.3) is **additive only,
operator-gated, and writes only into `mythic/heal/`** — that
contract makes the PH-11 dependency soft, not blocking.

## Slice-by-slice ledger

### Slice 13.1 — Drift index foundation
- New `mythic_vibe_cli/drift.py` with `DriftFinding` frozen
  dataclass + three heuristic detectors:
  - `detect_undocumented_handlers` — every `cmd_*` function in
    commands.py without a docstring (severity: warning)
  - `detect_undocumented_modules` — Python modules under
    `mythic_vibe_cli/` whose first significant statement is not a
    string literal (severity: info)
  - `detect_superseded_decisions` — markdown decision files marked
    `status: superseded` / `status: deprecated` still referenced
    by markdown outside the decision dirs (severity: warning)
- `scan_for_drift(root)` aggregator + `summarize_findings`,
  `render_findings_text`, `to_payload` helpers
- New `mythic-vibe drift` top-level subcommand + `/drift` slash
- 26 tests; commit `fbc5dc1`.
- Smoke verification on this project itself: 121 findings.

### Slice 13.2 — Doctor surfaces drift findings
- `cmd_doctor` calls `scan_for_drift` after its existing checks
- JSON output gains `drift` array; text output adds Drift-findings
  list (empty case explicit)
- Severity does not bump exit code (heuristics today emit only
  info / warning); future error-severity detector promotes via
  existing `report["errors"]` path
- 3 tests; commit `b09aaab`.

### Slice 13.3 — heal v2 reconciliation packet
- `cmd_heal` grew from print-only scaffold into a real packet
  generator
- Writes `mythic/heal/<timestamp>-reconciliation.md` + JSON sidecar
- Packet body: header + reconciliation principles (additive-only,
  operator-gated, per-category) + grouped findings + per-category
  Proposal stanza for the Scribe agent
- `--dry-run` honoured; `--json` returns full payload with paths
  and preview
- Argparse gains `--json` / `--dry-run`; `--failing-test` kept as
  informational
- 6 tests (3 new + 3 rewritten); commit `afa0363`.

### Slice 13.4 — TUI drift panel
- New `mythic_vibe_cli/tui/drift_panel.py` with `DriftScreen`
  wrapping `scan_for_drift` on a 5-second refresh interval
- Pulse-style header: red/yellow/cyan counts per severity, with
  severity word always present in monochrome (slice 4.9
  non-colour-fallback discipline)
- Uniform keymap: `escape`/`q` back, `r` refresh, `?` help, `t`
  theme — every slice 4.7 / 4.8 audit lock-in passes
- StatusScreen gains `d` binding to push DriftScreen
- Audit modules (test_help_overlay, test_tui_themes,
  test_accessibility) updated to walk the new module
- 5 tests (2 formatter + 3 integration); commit `d396de7`.

## Cumulative numbers

| Metric | Phase open | Phase close | Δ |
|---|---|---|---|
| Tests | 686 | **724** | +38 |
| Source files | 75 | **77** | +2 (`drift.py`, `tui/drift_panel.py`) |
| Slash builtins | 54 | **55** | +1 (`drift`) |
| Argparse handlers | 52 | **53** | +1 (`drift`; `heal` rewired) |

Ruff + mypy clean throughout.

## Master-roadmap target table

The Phase 13 "goal" from the master roadmap:

> Make divergence between docs, code, and decisions visible and
> actionable; provide a `heal` command that proposes additive
> reconciliations.

| Goal element | Status |
|---|---|
| Divergence visible | ✅ `mythic-vibe drift` + `doctor` + TUI panel (3 surfaces) |
| Divergence actionable | ✅ slice 13.3 packet groups by category + Proposal stanzas |
| `heal` proposes additive reconciliations | ✅ slice 13.3 — additive-only by contract |
| Never overwrites without approval | ✅ — packets land in `mythic/heal/`, never edit existing files |

## What Phase 13 deliberately did not do

- **Did not implement graph-backed queries.** Filesystem-heuristic
  v1 covers the same drift categories; PH-05 will provide the
  graph and the detectors can swap implementations behind the same
  public surface.
- **Did not auto-apply heal proposals.** The packet is a
  recommendation for the Scribe agent / operator. Auto-apply with
  approval gates is PH-15 territory (operator-conversation
  workflows).
- **Did not detect orphaned functions.** Requires call-graph
  analysis (effectively PH-05 again). Today's detectors focus on
  documentation drift, which is the most common and most
  user-impacting category.
- **Did not detect stale TODOs / dead code.** Out of scope for v1;
  the detector contract makes adding them additive.
- **Did not promote drift severity to errors.** Today's heuristics
  are info / warning by design — they identify *suggestions*, not
  *failures*. A future detector that finds a security violation or
  contract break should emit `error` and bump `cmd_doctor`'s exit
  code via the existing `report["errors"]` path.
- **Did not surface drift in the slice 4.4 status bar.** The bar
  is already dense; surfacing per-finding counts there would
  duplicate what slice 13.4's dashboard does on demand.

## Phase progression after PH-13

Master roadmap status snapshot:

| Phase | Status |
|---|---|
| PH-01 Audit & runtime hygiene | ✅ closed |
| PH-02 Slash command surface expansion | ✅ closed |
| PH-03 Multi-agent forge engine | ✅ closed |
| PH-04 TUI layout & interaction | ✅ closed |
| PH-13 Drift detection & self-healing | ✅ closed (this finale) |
| PH-05 / PH-06 / PH-07 / PH-08 etc. | open — Volmarr's choice |

Five master-roadmap phases now closed. Untouched candidates next:

- **PH-05** Knowledge Graph & Persistent Memory — natural follow-up
  to PH-13 (would let drift detectors use real graph queries)
- **PH-11** Security, Sandbox & Permissions — would harden plugin
  dispatch and forge-loop execution
- **PH-12** CI/CD & Deployment Integration
- **PH-16** MCP / ACP / OpenTelemetry Protocols

## How to resume

`MEMORY.md` quick-facts line and `project_mythic_engineering_cli_status.md`
both updated to HEAD `<close-head>` and "PH-13 closed".
`TASK_master_roadmap_and_phase1.md` tracker is up to date through
this finale.

A future session can resume by opening that tracker, locating the
"next" row at the bottom, and starting that slice.

---

## Update Notice — 2026-05-02 (additive)

A later audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`, HEAD `e0953b6`) re-measured the project on 2026-05-02. The original closeout above is preserved unchanged; this notice is purely additive.

- **Coverage:** any "76%" figure in this or sibling closeouts was a stale carry-over. Live measurement (`pytest --cov=mythic_vibe_cli --cov-report=term-missing`) on 2026-05-02 reports **82%** branch+line coverage on the production package (1694 passed, 1 skipped, 14 subtests). Current coverage is ~6 points higher than recorded.

— *Sólrún Hvítmynd & Runa, additive correction*
