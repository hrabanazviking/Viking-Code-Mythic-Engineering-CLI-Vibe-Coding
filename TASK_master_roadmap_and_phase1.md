---
task_id: TASK_master_roadmap_and_phase1
title: Unified Mythic Vibe CLI Master Roadmap + Phase 1 Execution
opened_at: 2026-04-29
opened_by: Runa Gridweaver Freyjasdottir (assistant) on behalf of Volmarr
branch: development
head_at_open: 164b7de
status: in_progress
---

# TASK — Unified Mythic Vibe CLI Master Roadmap + Phase 1 Execution

## Why this task exists

Volmarr asked for two things in one breath:

1. Read the development branch in full — current state, every roadmap MD,
   all rules, the active runtime, the tests, and the aggregate feature
   report — and synthesise it into **one** huge multi-phase development
   roadmap as a data MD file.
2. After that file is on disk, **begin Phase 1**.

Three separate roadmaps already exist (`MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`,
`MYTHIC_VIBE_CLI_EXPANSION_ROADMAP_V2.md`,
`Mythic_Vibe_CLI_ The_2026_Expansion_Roadmap.md`), plus `TODO.md` adds four
robustness sweeps, Pi plundering, and the full Vibe-Coding aggregate
feature implementation. None of those documents is currently authoritative
on its own. The **master roadmap** unifies them all so future work has
one north star instead of three competing ones.

This file is the resumption-friendly task description so that if the
session is interrupted (context limit, crash, disconnect) any future
session can read this file and continue without losing thread.

---

## Repo snapshot at task open

- Path: `C:/Users/volma/runa/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`
- Remote: `git@github.com:hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git`
- Branch: `development`
- HEAD: `164b7de` (`README: Quick start now walks a novice through a full first session`)
- Tree: clean except untracked `research_data/vibe_research_part1_tier1a.md`
  (obsolete partial; ignore unless explicitly resurrected)
- Tests: **270 passed, 14 subtests passed** in 33s — verified before this
  task file was committed
- Lint/type: ruff and mypy clean (per `project_mythic_engineering_cli_status.md`)

### Active runtime layout (`mythic_vibe_cli/`)

| File / dir | Role |
|---|---|
| `__main__.py`, `cli.py`, `app.py` | Entry, argparse, app composition |
| `commands.py` (~2,645 lines) | Command registry + implementations |
| `workflow_engine.py`, `workflow.py` | Six-role plans, packet readiness |
| `codex_bridge.py` | `PacketBuilder` (formerly CodexBridge) |
| `ai/providers/` | copy-paste, local, openai, anthropic, gemini, openrouter |
| `ai/prompts/roles.py` | Role catalog (Skald is first-class) |
| `context/` | Scanner, indexer, file filters → project_index.json |
| `core/state.py` | Schema-versioned project state |
| `persistence/` | JSON store + migrations |
| `plugins/` | API + loader + registry + 8 hooks dispatcher |
| `plunder/` | Lawful single-file reuse with provenance |
| `verify/` | Test runner, git diff, doc checker, invariant checker |
| `runtime/` | Eight Pi-derived primitives (MIT) |
| `tui/` | Textual TUI: status, picker, preview, runner |
| `handoff.py` | Durable session handoff artifacts |
| `mythic_data.py` | Method profile + manifest + freshness |
| `ux.py` | Stage 14 UX (examples/guide/next/explain/tutorial/completion) |
| `resources/schemas/` | JSON schemas |
| `errors.py`, `exit_codes.py`, `output.py` | Cross-cutting helpers |

### Active runtime primitives ported from Pi (MIT, attributed in `THIRD_PARTY_NOTICES.md`)

1. `runtime.exec` — subprocess executor with timeout + cancel
2. `runtime.output_guard` — stdout cleanliness for `--json` modes
3. `runtime.event_bus` — synchronous pub/sub
4. `runtime.event_log` — bounded JSONL at `mythic/events.jsonl`
5. `runtime.timings` — `MYTHIC_TIMING=1` profiler
6. `runtime.slash_commands` — typed catalog
7. `runtime.source_info` — provenance type
8. `runtime.file_mutation_queue` — per-path serializer

### Existing roadmap inventory

| File | Purpose | Status |
|---|---|---|
| `TODO.md` | Top-of-stack backlog | active, short |
| `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md` | 16-stage production plan | mostly complete (Stages 0,1,2,5,6,7,8,10,11,12,13,14,15 done; 3,4,9 partial) |
| `MYTHIC_VIBE_CLI_EXPANSION_ROADMAP_V2.md` | 10-phase 24-month V2 | Phase 1 partially landed |
| `Mythic_Vibe_CLI_ The_2026_Expansion_Roadmap.md` | 10-phase 24-month deep plan | superset of V2; not yet started |
| `Vibe_Coding_CLI_Tools_-_Aggregate_Feature_and_Interface_Report.md` | feature catalogue from all known vibe-coding CLIs | source-of-truth feature list |
| `Aider_Plundering_Guide.md`, `Goose_Plundering_Guide.md`, `Gemini_CLI_Plundering_Guide.md` | upstream plundering guides | reference |

### Immutable rules (per CLAUDE-style governance)

- `REPO_BOUNDARY.md` + `docs/ACTIVE_PRODUCT_BOUNDARY.md` + `docs/DORMANT_ISLANDS.md`
  define the live product vs. dormant islands.
- ADRs `ADR-0001` through `ADR-0004` govern boundary, vendor imports,
  verification gates, and doctor diagnostics.
- 100% cross-platform (Windows/macOS/Linux) — no per-OS branches.
- 100% open-source — no proprietary platform SDKs.
- Strictly additive expansion — no destructive edits.
- Mythic Engineering loop is the operating method.

---

## Inventory of deliverables for this task

| Deliverable | Path | Status |
|---|---|---|
| Resumption task file | `TASK_master_roadmap_and_phase1.md` | being written now |
| Unified master roadmap | `MYTHIC_VIBE_CLI_MASTER_ROADMAP.md` | next |
| Phase 1 audit | `PHASE1_RUNTIME_AUDIT.md` | after master roadmap |
| Memory refresh | `project_mythic_engineering_cli_status.md` + `MEMORY.md` | after Phase 1 slice 1 lands |
| Git commit + push | development branch | after each meaningful slice |

---

## Master roadmap shape (preview — full text in `MYTHIC_VIBE_CLI_MASTER_ROADMAP.md`)

The unified roadmap defines **20 phases** (every phase is strictly
additive, cross-platform, open-source):

1.  **Phase 1 — Foundation Audit & Quality Sweep** (current)
2.  **Phase 2 — Slash Command Surface Expansion** (39+ commands from the aggregate report)
3.  **Phase 3 — Multi-Agent Forge Command + Workflow Engine v2**
4.  **Phase 4 — TUI Revolution v2** (diff review, real-time diagnostics, full keymap)
5.  **Phase 5 — Knowledge Graph & Persistent Memory** (SQLite + entity graph)
6.  **Phase 6 — Local LLM Sovereignty** (Ollama deep integration, hardware-aware routing)
7.  **Phase 7 — Voice & Multimodal** (Whisper, Chatterbox TTS)
8.  **Phase 8 — Provider Routing & Hardware-Aware Selection**
9.  **Phase 9 — Island Integrations** (Yggdrasil / MindSpark / WYRD / Chatterbox)
10. **Phase 10 — Plugin Ecosystem & Community Infrastructure**
11. **Phase 11 — Security, Sandbox & Permissions Layer**
12. **Phase 12 — CI/CD & Deployment Integration**
13. **Phase 13 — Drift Detection & Self-Healing**
14. **Phase 14 — Policy Engine & Constraint Verification**
15. **Phase 15 — Conversation Memory & Compaction**
16. **Phase 16 — MCP / ACP / OpenTelemetry Protocols**
17. **Phase 17 — Multi-Surface Access** (web terminal, mobile, SSH, chat bridge)
18. **Phase 18 — Robustness Sweeps Round 1–4**
19. **Phase 19 — Distribution** (PyPI, pipx, Homebrew, Scoop, Docker)
20. **Phase 20 — Mythic Vibe CLI v1.0.0 — Sovereign OS Launch**

---

## Progress tracker

| # | Step | Status |
|---|---|---|
| 1 | Read repo state, all roadmap MDs, rules, active runtime, tests | done (in this session) |
| 2 | Write `TASK_master_roadmap_and_phase1.md` | done |
| 3 | Write `MYTHIC_VIBE_CLI_MASTER_ROADMAP.md` | done — pushed at d36a4ae |
| 4 | Commit + push task file and master roadmap | done — pushed at d36a4ae |
| 5 | Begin Phase 1 Slice 1.1 — `PHASE1_RUNTIME_AUDIT.md` | done — 20 findings catalogued |
| 6 | Update memory + project status | in progress |
| 7 | Hand off / await further instruction | end of slice |

## Phase 1 Slice 1.1 — Findings Summary

20 findings catalogued (0 errors, 7 warnings, 13 info). The CLI is
structurally sound; gaps are feature-shaped and each has a phase home
in the master roadmap. Most-visible gaps:

- **F-001 / F-002 / F-004 / F-005** — `prune`, `heal`, `oath`, `weave`
  are scaffold-only; real implementations land in PH-13/14.
- **F-006 / F-007** — silent-fall-through dispatchers (`slash`, `ai`)
  return exit code 2 with no message — quick-fix in slice 1.3.
- **F-008 / F-009** — TUI plugin-dispatch gap and direct
  `subprocess.Popen` in TUI runner — work for PH-02 / PH-04 / PH-18.
- **F-020** — no structured-log layer separate from user output —
  prerequisite for OpenTelemetry in PH-16.

See `PHASE1_RUNTIME_AUDIT.md` for the full table + remediation plan.

## Next slice (1.2)

Repo issue triage. `gh issue list` for the GitHub repo, match each
issue to a finding/slice/phase, and produce `PHASE1_ISSUE_TRIAGE.md`.
This is gated on Volmarr's go-ahead so we don't bombard GitHub with
automated comments.

---

## Exact next steps if a future session resumes this task

1. Read this file end-to-end.
2. Read `MYTHIC_VIBE_CLI_MASTER_ROADMAP.md` (Phase 1 in particular).
3. Read `PHASE1_RUNTIME_AUDIT.md` if it exists; otherwise it is the next
   deliverable.
4. Verify tree state: `git status`, `git log --oneline -5`,
   `python -m pytest tests/ -q --no-header` (expected ≥ 270 passing).
5. Continue from the first unchecked progress-tracker row above.

## Constraints binding every step

- **Additive only.** No removal of existing code unless it is genuinely
  dead (orphaned, unreachable, no tests reference it). Every removal
  needs an ADR.
- **Cross-platform only.** Windows + macOS + Linux. No `SIGUSR1`, no
  bash-isms in production code, forward-slash paths normalised through
  `pathlib`.
- **Open-source only.** No proprietary SDKs as required dependencies.
- **Verification before claim of done.** Every slice ends with `pytest -q`
  green and (where applicable) `ruff` and `mypy` clean.
- **Update the resumption file at the end of every slice** — including
  the progress tracker row and the head-at-close commit hash.
- **Update `MEMORY.md` quick-facts and `project_mythic_engineering_cli_status.md`**
  after every slice — not at end-of-task.
