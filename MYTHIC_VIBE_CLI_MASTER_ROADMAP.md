---
title: "Mythic Vibe CLI — Master Development Roadmap (Unified)"
repo: "hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding"
branch: "development"
created: "2026-04-29"
created_by: "Runa Gridweaver Freyjasdottir on behalf of Volmarr"
supersedes:
  - "MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md (residual stages folded in)"
  - "MYTHIC_VIBE_CLI_EXPANSION_ROADMAP_V2.md (10 phases folded in)"
  - "Mythic_Vibe_CLI_ The_2026_Expansion_Roadmap.md (deep plan folded in)"
absorbs:
  - "Vibe_Coding_CLI_Tools_-_Aggregate_Feature_and_Interface_Report.md (full feature catalogue)"
  - "TODO.md (residual top-of-stack items)"
status: "active"
phases: 20
discipline: "additive-only / cross-platform / open-source / verified-before-done"
---

# Mythic Vibe CLI — Master Development Roadmap (Unified)

> *This is the single authoritative roadmap for the Mythic Vibe CLI.
> It folds three prior roadmaps and the aggregate feature catalogue
> into one twenty-phase plan. Every other planning document in the
> repo is now reference material; this document is the north star.*

## Table of Contents

- [0. Reading guide](#0-reading-guide)
- [1. Mission and standards](#1-mission-and-standards)
- [2. Source material absorbed](#2-source-material-absorbed)
- [3. Operating laws](#3-operating-laws)
- [4. Phase index](#4-phase-index)
- [5. The twenty phases](#5-the-twenty-phases)
  - [Phase 1 — Foundation Audit & Quality Sweep](#phase-1--foundation-audit--quality-sweep)
  - [Phase 2 — Slash Command Surface Expansion](#phase-2--slash-command-surface-expansion)
  - [Phase 3 — Multi-Agent Forge Command + Workflow Engine v2](#phase-3--multi-agent-forge-command--workflow-engine-v2)
  - [Phase 4 — TUI Revolution v2](#phase-4--tui-revolution-v2)
  - [Phase 5 — Knowledge Graph & Persistent Memory](#phase-5--knowledge-graph--persistent-memory)
  - [Phase 6 — Local LLM Sovereignty](#phase-6--local-llm-sovereignty)
  - [Phase 7 — Voice & Multimodal](#phase-7--voice--multimodal)
  - [Phase 8 — Provider Routing & Hardware-Aware Selection](#phase-8--provider-routing--hardware-aware-selection)
  - [Phase 9 — Island Integrations](#phase-9--island-integrations)
  - [Phase 10 — Plugin Ecosystem & Community Infrastructure](#phase-10--plugin-ecosystem--community-infrastructure)
  - [Phase 11 — Security, Sandbox & Permissions Layer](#phase-11--security-sandbox--permissions-layer)
  - [Phase 12 — CI/CD & Deployment Integration](#phase-12--cicd--deployment-integration)
  - [Phase 13 — Drift Detection & Self-Healing](#phase-13--drift-detection--self-healing)
  - [Phase 14 — Policy Engine & Constraint Verification](#phase-14--policy-engine--constraint-verification)
  - [Phase 15 — Conversation Memory & Compaction](#phase-15--conversation-memory--compaction)
  - [Phase 16 — MCP / ACP / OpenTelemetry Protocols](#phase-16--mcp--acp--opentelemetry-protocols)
  - [Phase 17 — Multi-Surface Access](#phase-17--multi-surface-access)
  - [Phase 18 — Robustness Sweeps Round 1–4](#phase-18--robustness-sweeps-round-14)
  - [Phase 19 — Distribution](#phase-19--distribution)
  - [Phase 20 — Mythic Vibe CLI v1.0.0 — Sovereign OS Launch](#phase-20--mythic-vibe-cli-v100--sovereign-os-launch)
- [6. Cross-cutting quality bar](#6-cross-cutting-quality-bar)
- [7. Method/role mapping](#7-methodrole-mapping)
- [8. Slash-command surface (target)](#8-slash-command-surface-target)
- [9. Provenance map of folded plans](#9-provenance-map-of-folded-plans)

---

## 0. Reading guide

Each phase has the same shape so a reader can scan or dive at will:

```yaml
phase_id: PH-NN
name: <human-readable>
mythic_role_bias: <skald|architect|forge|auditor|cartographer|scribe>
priority: <critical|high|medium|low>
depends_on: [...]
goal: <one paragraph>
constraints: [strictly additive, cross-platform, open-source, ...]
slices: [...]
deliverables: [...]
verification: [...]
done_when: [...]
quality_gate: [...]
```

*Slices* are the unit of execution — each is one or two PRs of work,
ending with a green test suite, a memory update, and a tracker tick.
Phases are large; slices are concrete.

---

## 1. Mission and standards

**Mission.** Make Mythic Vibe CLI the disciplined, local-first, multi-agent
command-line operating system for Mythic Engineering — the loop:

```
intent -> constraints -> architecture -> plan -> build -> verify -> reflect
```

**Standards.** This roadmap inherits the project's existing law and
adds explicit standards for execution:

| Standard | Meaning |
|---|---|
| **Additive only** | No destructive removal without an ADR; replace by wrapping, never by deleting. |
| **Cross-platform** | Every feature runs on Windows, macOS, and Linux unchanged. No per-OS branches in production code. |
| **Open-source** | All required dependencies are open-source. Proprietary integrations are optional adapters. |
| **Reality over theory** | A slice is not done until tests are green and the change is observable on disk. |
| **Continuity over speed** | Every slice ends with a memory update, a status update, and a commit. |
| **AI is co-pilot, not autopilot** | No automatic application of model output. User remains sovereign. |
| **Local-first** | The CLI must work fully without cloud AI. Cloud is opt-in. |
| **Boundary-respecting** | Active runtime stays in `mythic_vibe_cli/`. Dormant islands need ADRs. |

---

## 2. Source material absorbed

This unified roadmap incorporates and supersedes:

| Source | Contribution |
|---|---|
| `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md` | Stages 0–15 — most are complete; residual items absorbed (template profiles, phase commands, deep doctor) |
| `MYTHIC_VIBE_CLI_EXPANSION_ROADMAP_V2.md` | The 6-agent island integration framing |
| `Mythic_Vibe_CLI_ The_2026_Expansion_Roadmap.md` | The 24-month deep plan with knowledge graph, agent orchestration, provider layer |
| `Vibe_Coding_CLI_Tools_-_Aggregate_Feature_and_Interface_Report.md` | The complete vibe-coding feature universe (39+ slash commands, 75+ providers, MCP/ACP, multi-surface access) |
| `TODO.md` | 4 robustness sweeps, Pi plundering finalisation, V2 Phase 3+, V2 Phase 4 |
| `Aider_Plundering_Guide.md`, `Goose_Plundering_Guide.md`, `Gemini_CLI_Plundering_Guide.md`, `deep-research-report-Mythic_Vibe_CLI_Architect_Master_Plan.md` | Reference for lawful single-file reuse |
| Historical roadmap documents in `docs/` | Architecture and domain ownership context |

After this file lands, the prior roadmaps are *reference snapshots*.
The TODO list becomes the live execution view of the master roadmap.

---

## 3. Operating laws

The eight existing laws stand. Two new laws are added for this expansion.

**Law 1 — The method is executable.** The CLI must enforce, guide,
record, and verify the Mythic Engineering loop, not merely describe it.

**Law 2 — No hidden memory.** Every important state change is written
to disk in a predictable place under `mythic/`.

**Law 3 — Project state is a first-class object.** Schema-versioned,
migration-safe, append-recorded, atomic-write, backup-before-destroy.

**Law 4 — AI output is never automatically trusted.** The CLI separates
proposal → user review → applied change → verification → reflection.

**Law 5 — Documents are not decoration.** Drift between docs and code
is a diagnostic failure surfaced by `doctor`.

**Law 6 — Every subsystem has an owner.** A feature without a domain
home is not ready to land.

**Law 7 — The CLI must be useful without cloud AI.** Offline path
scaffolds, scans, plans, diagnoses, and preserves continuity.

**Law 8 — The user owns the work.** No vendor lock-in, no editor
lock-in, no platform lock-in.

**Law 9 — Islands integrate through contracts, not imports.** No
dormant island is wired into the active CLI without an ADR, a defined
call contract, and a feature flag that allows the integration to be
disabled without breaking the core.

**Law 10 — Plugins fail safely.** Any plugin failure is caught,
logged, and surfaced as a diagnostic warning. It never crashes the
CLI or corrupts project state.

---

## 4. Phase index

| # | Phase | Bias | Priority | Depends on |
|---|---|---|---|---|
| 1  | Foundation Audit & Quality Sweep                   | auditor      | critical | — |
| 2  | Slash Command Surface Expansion                    | forge        | high     | 1 |
| 3  | Multi-Agent Forge Command + Workflow Engine v2     | architect    | critical | 1, 2 |
| 4  | TUI Revolution v2                                  | cartographer | high     | 2, 3 |
| 5  | Knowledge Graph & Persistent Memory                | scribe       | critical | 1 |
| 6  | Local LLM Sovereignty                              | forge        | high     | 1 |
| 7  | Voice & Multimodal                                 | skald        | medium   | 6 |
| 8  | Provider Routing & Hardware-Aware Selection        | architect    | high     | 6 |
| 9  | Island Integrations (B/C/D/E)                      | architect    | medium   | 1, 5, 6 |
| 10 | Plugin Ecosystem & Community Infrastructure        | scribe       | high     | 1, 2 |
| 11 | Security, Sandbox & Permissions Layer              | auditor      | critical | 1 |
| 12 | CI/CD & Deployment Integration                     | forge        | medium   | 1, 11 |
| 13 | Drift Detection & Self-Healing                     | auditor      | high     | 5, 11 |
| 14 | Policy Engine & Constraint Verification            | auditor      | high     | 11, 13 |
| 15 | Conversation Memory & Compaction                   | scribe       | high     | 5 |
| 16 | MCP / ACP / OpenTelemetry Protocols                | architect    | high     | 1, 11 |
| 17 | Multi-Surface Access                               | cartographer | medium   | 4, 16 |
| 18 | Robustness Sweeps Round 1–4                        | auditor      | critical | spans all phases |
| 19 | Distribution                                       | scribe       | high     | 1, 12, 18 |
| 20 | Mythic Vibe CLI v1.0.0 — Sovereign OS Launch       | skald        | critical | all |

---

## 5. The twenty phases

### Phase 1 — Foundation Audit & Quality Sweep

```yaml
phase_id: PH-01
name: Foundation Audit & Quality Sweep
mythic_role_bias: auditor
priority: critical
depends_on: []
goal: >
  Before adding any new feature, comprehensively audit the active runtime
  for bugs, incomplete code, orphaned code, missing integrations, dead
  branches, and inefficiencies. Produce a strictly additive remediation
  plan and execute it slice by slice with the test suite green at each
  step.
constraints:
  - additive only
  - cross-platform
  - open-source
  - 270-test baseline must never regress
```

#### Slices

1. **Slice 1.1 — Runtime Audit** *(deliverable: `PHASE1_RUNTIME_AUDIT.md`)*
   - Walk every module under `mythic_vibe_cli/`.
   - Tag findings by category: `BUG`, `INCOMPLETE`, `ORPHAN`, `INTEGRATION_GAP`,
     `INEFFICIENCY`, `MISSING_TEST`, `DOC_DRIFT`.
   - For each finding: file, line range, severity (info/warning/error/blocked),
     additive remediation step, blast radius, test impact.
   - No code changes in this slice.
2. **Slice 1.2 — Repo Issue Triage** *(deliverable: `PHASE1_ISSUE_TRIAGE.md`)*
   - Pull every open issue from the GitHub repo via `gh issue list`.
   - Match each issue to a finding category, slice, or new phase.
   - Mark resolved or stale issues with proposed close comments (no
     pushes — Volmarr does any GitHub interaction).
3. **Slice 1.3 — Quick-fix Sweep**
   - Apply only the *additive*, *zero-risk* fixes from the audit
     (missing docstrings, missing `__all__`, missing tests for
     existing public surface).
   - Each fix is its own commit; tests must stay green.
4. **Slice 1.4 — Coverage and Test Hygiene**
   - Run `pytest -q --cov=mythic_vibe_cli` to identify untested public
     surface.
   - Add tests only — never refactor code while raising coverage.
   - Target ≥ 85% line coverage on `mythic_vibe_cli/` excluding TUI.
5. **Slice 1.5 — Boundary Re-audit**
   - Run `mythic-vibe doctor --repo-boundary` and capture diagnostics.
   - File ADRs for any missing-but-justified imports.
6. **Slice 1.6 — Phase 1 close-out memo** *(deliverable: `PHASE1_CLOSEOUT.md`)*
   - Summarise what landed, what was deferred, and what changed in the
     test/coverage baseline.

#### Verification

```bash
python -m pytest tests/ -q --no-header
python -m pytest tests/ -q --cov=mythic_vibe_cli
python -m mythic_vibe_cli doctor --repo-boundary
ruff check mythic_vibe_cli tests
mypy mythic_vibe_cli
```

#### Done when

- `PHASE1_RUNTIME_AUDIT.md`, `PHASE1_ISSUE_TRIAGE.md`, and
  `PHASE1_CLOSEOUT.md` are committed.
- Coverage ≥ 85% (or a documented exception).
- Test count ≥ 270 (no regression) and ideally ≥ 300 after slice 1.4.
- Doctor reports no boundary or invariant errors.

#### Quality gate

| Metric | Target |
|---|---|
| Test pass rate | 100% |
| Line coverage on active runtime | ≥ 85% |
| Ruff diagnostics | 0 |
| Mypy diagnostics | 0 |
| Doctor errors | 0 |
| Doctor warnings unaccounted-for | 0 |

---

### Phase 2 — Slash Command Surface Expansion

```yaml
phase_id: PH-02
name: Slash Command Surface Expansion
mythic_role_bias: forge
priority: high
depends_on: [PH-01]
goal: >
  Grow the slash-command catalogue toward the 39+ commands documented in
  the Aggregate Feature Report, plus Mythic-specific additions. Every
  new slash command is a thin façade over an underlying argparse
  command, so the CLI, the shell REPL, the TUI, and the future plugin
  loader all see the same surface.
constraints:
  - every slash command resolves to an existing argparse handler
  - new functionality is added in the handler layer, not in the slash
    catalog
  - additive only
```

#### Target slash command catalogue

```text
# Identity / state
/help /status /next /examples /guide /tutorial /completion /resume
/explain /method /grimoire /policy

# Workflow phases
/intent /constraints /architecture /plan /build /verify /reflect /handoff

# Packets
/packet /codex-pack /evoke /response /ingest

# Provider / AI
/provider /ai /forge /architect-agent /planner /builder /verifier
/voice /chat

# Context / scan / graph
/scan /graph /rehydrate /index /search

# Verification / quality
/test /lint /typecheck /audit /review /security /shield

# Project / scaffold
/init /imbue /scaffold /weave /prune /heal /oath

# Plugins / extensions / rituals
/plugin /ritual /extension /skill /prompt

# Integration
/plunder /sync /import-md /export

# Diagnostics
/doctor /scry /simulate /resilience /telemetry

# Memory / continuity
/checkin /reflect /handoff /memory

# Surface / display
/ui /tui /shell /web /mobile /telegram

# Release
/changelog /version /release /package /publish
```

#### Slices

1. **Slice 2.1 — Map every command to a handler** in
   `mythic_vibe_cli/runtime/slash_commands.py` with `BuiltinSlashCommand`
   entries.
2. **Slice 2.2 — Implement missing simple aliases** (`/test`, `/lint`,
   `/typecheck`, `/changelog`, `/version`).
3. **Slice 2.3 — Implement workflow-phase aliases** (`/intent`,
   `/constraints`, `/architecture`, `/plan`, `/build`).
4. **Slice 2.4 — Implement provider/AI aliases** (`/forge`,
   `/architect-agent`, `/planner`, `/builder`, `/verifier`, `/voice`,
   `/chat`).
5. **Slice 2.5 — Implement diagnostic aliases** (`/audit`, `/review`,
   `/security`, `/shield`, `/simulate`).
6. **Slice 2.6 — Plugin-contributed slash commands**: extend the
   discovery contract so plugins can add arbitrary slash entries that
   resolve via the dispatcher.
7. **Slice 2.7 — Slash help & introspection** — `/help <command>`
   prints the underlying argparse help; `mythic-vibe slash inspect`
   shows full provenance.
8. **Slice 2.8 — REPL + TUI + plugin parity tests** — every slash
   resolves identically through every surface.

#### Verification

```bash
python -m mythic_vibe_cli slash list --json
python -m mythic_vibe_cli slash inspect <each command>
python -m pytest tests/test_slash_commands.py tests/test_repl.py tests/test_tui.py
```

#### Done when

- `slash list` reports ≥ 50 entries (39 from aggregate + Mythic-specific).
- Every entry has `source_info`, a description, and a non-empty argparse
  resolution.
- Help, inspect, and dispatch are identical between CLI, REPL, and TUI.

---

### Phase 3 — Multi-Agent Forge Command + Workflow Engine v2

```yaml
phase_id: PH-03
name: Multi-Agent Forge Command + Workflow Engine v2
mythic_role_bias: architect
priority: critical
depends_on: [PH-01, PH-02]
goal: >
  Promote the existing six-role workflow engine into a real multi-agent
  orchestration loop with explicit handoffs, durable artefacts per
  agent, and a one-command `mythic-vibe forge` that runs a full
  Skald → Architect → Forge Worker → Auditor → Cartographer → Scribe
  cycle for a given task with human approval gates.
```

#### Slices

1. **Slice 3.1 — Agent contract spec** — define the input/output
   contract for each role in `ai/prompts/roles.py` and a new
   `workflow/agents.py` (no provider call yet).
2. **Slice 3.2 — Handoff ledger** — extend
   `mythic/workflow_history.json` to record every per-agent step with
   inputs, outputs, status, and duration.
3. **Slice 3.3 — `forge` command (dry-run)** — generate the full plan
   and packet sequence without invoking providers.
4. **Slice 3.4 — Approval gates** — between each agent, the CLI prints
   a short summary and waits for `y/n/?` (TUI version exposes a modal).
5. **Slice 3.5 — Provider-backed forge** — when providers are
   configured, route packets through the configured provider for each
   role, capturing structured responses.
6. **Slice 3.6 — Verifier integration** — the Auditor agent's output is
   compared against the project's invariants and tests; failures block
   the cycle.
7. **Slice 3.7 — Reflection capture** — the Scribe agent writes the
   per-cycle reflection to `mythic/reflections/` and updates the
   handoff.
8. **Slice 3.8 — `forge resume`** — resumes a partially completed
   cycle from the handoff ledger.

#### Verification

```bash
python -m mythic_vibe_cli forge --dry-run --task "Smoke task"
python -m mythic_vibe_cli forge --provider copy-paste --task "Smoke task"
python -m pytest tests/test_forge.py tests/test_workflow_engine.py
```

#### Done when

- `forge --dry-run` produces six durable role artefacts.
- Provider-backed `forge` completes with explicit human approval at
  each gate.
- The Auditor blocks at least one synthetic invariant violation in the
  integration tests.

---

### Phase 4 — TUI Revolution v2

```yaml
phase_id: PH-04
name: TUI Revolution v2
mythic_role_bias: cartographer
priority: high
depends_on: [PH-02, PH-03]
goal: >
  Lift the Textual TUI from "status + slash picker + runner" to a full
  Mythic dashboard: loop navigator, artifact viewer, AI packet viewer,
  diff review, real-time diagnostics, and full keymap, all keyboard-
  navigable and accessible.
```

#### Slices

1. **Slice 4.1 — Loop Navigator panel** — left sidebar showing the
   seven phases with state markers.
2. **Slice 4.2 — Artifact Viewer panel** — scrollable list of required
   artefacts for the current phase with present/missing/stale status.
3. **Slice 4.3 — Packet Viewer panel** — read/edit current packet
   before send.
4. **Slice 4.4 — Status bar** — project name, phase, last check-in,
   active warnings.
5. **Slice 4.5 — Diff review screen** — open from `codex-log`/`response
   ingest`; per-hunk accept/reject with `a`/`r`/`s`/`q` keys.
6. **Slice 4.6 — Real-time diagnostics** — background thread runs
   doctor every N seconds; surfaces warnings inline.
7. **Slice 4.7 — Full keymap and `?` help screen** — Tab cycle,
   `j`/`k` scroll, `p`/`c`/`d`/`q`/`?` actions.
8. **Slice 4.8 — Theme support** — dark/light, configurable colours,
   colour-blind safe palette.
9. **Slice 4.9 — Accessibility audit** — TUI fully keyboard-navigable,
   no mouse-only paths, screen-reader-friendly text.

#### Done when

- `mythic-vibe tui` opens a four-panel dashboard with no rendering
  errors on Windows Terminal, macOS Terminal.app/iTerm, and Linux gnome-
  terminal/alacritty.
- Diff review supports per-hunk accept/reject with persistence.
- Real-time diagnostics surface within ≤ 2 s of a state change.

---

### Phase 5 — Knowledge Graph & Persistent Memory

```yaml
phase_id: PH-05
name: Knowledge Graph & Persistent Memory
mythic_role_bias: scribe
priority: critical
depends_on: [PH-01]
goal: >
  Build a local SQLite-backed knowledge graph that models the
  repository's modules, functions, documents, decisions, phases, and
  tasks. Use it for relevance-ranked context retrieval, session
  rehydration, and drift detection.
```

#### Slices

1. **Slice 5.1 — Schema design** — entity tables, relationship tables,
   migration v1 → v2 from existing scanner indices.
2. **Slice 5.2 — `context/graph.py`** — SQLite store with safe
   migrations.
3. **Slice 5.3 — `context/retriever.py`** — relevance-ranked retrieval
   for packet building.
4. **Slice 5.4 — `context/rehydrator.py`** — session brief generator.
5. **Slice 5.5 — `mythic-vibe graph query`** — read-only graph queries.
6. **Slice 5.6 — `mythic-vibe graph visualize`** — Mermaid/DOT export
   for human review.
7. **Slice 5.7 — Packet retriever integration** — packets pull from
   the graph by relevance, respecting `MYTHIC_PACKET_CHAR_BUDGET`.
8. **Slice 5.8 — Drift detector wiring** — surfaces diagnostics in
   `doctor`.

#### Done when

- Graph populates on `checkin` and `scan`; survives a restart.
- Retriever measurably improves packet relevance vs. the current
  fixed-file approach (token-efficiency metric in tests).

---

### Phase 6 — Local LLM Sovereignty

```yaml
phase_id: PH-06
name: Local LLM Sovereignty
mythic_role_bias: forge
priority: high
depends_on: [PH-01]
goal: >
  Make the offline path first-class. Native Ollama integration via the
  official Python client (the in-repo Go mirror is reference only),
  hardware-aware model selection, streaming responses, automatic
  daemon-up detection.
```

#### Slices

1. **Slice 6.1 — `ai/providers/ollama.py`** — replace the existing
   `local` placeholder with a real Ollama adapter using the official
   `ollama` Python client, behind an optional dependency group.
2. **Slice 6.2 — Daemon discovery** — detect port 11434, offer to
   start the daemon (cross-platform).
3. **Slice 6.3 — Model picker** — list installed models, allow
   per-role assignment.
4. **Slice 6.4 — Streaming output** — TUI and CLI both render token
   stream with cancellation support via `runtime.exec`'s cancel signal
   model.
5. **Slice 6.5 — Cost/latency telemetry** — write per-call records to
   `mythic/ai/provider_calls.jsonl` (already exists; extend schema).
6. **Slice 6.6 — Hardware profile detection** — CPU/RAM/GPU sniff via
   `psutil` + `torch` (if installed); record in
   `docs/hardware_profiles.md`.

#### Done when

- `mythic-vibe ai run --provider ollama` succeeds end-to-end against a
  local daemon.
- The CLI never freezes a session if Ollama is unavailable; it
  degrades to copy-paste mode with a clear message.

---

### Phase 7 — Voice & Multimodal

```yaml
phase_id: PH-07
name: Voice & Multimodal
mythic_role_bias: skald
priority: medium
depends_on: [PH-06]
goal: >
  Optional voice-to-intent input (Whisper) and TTS notification output
  (Chatterbox), behind feature flags. Strictly local-first; no cloud
  speech services in the default path.
```

#### Slices

1. **Slice 7.1 — `mythic-vibe voice` command** — record N seconds via
   `sounddevice` (cross-platform) or fall back to a file path; pipe
   through `openai-whisper` (local, MIT).
2. **Slice 7.2 — Intent capture** — transcribed text feeds the
   existing `intent capture` flow with explicit user review.
3. **Slice 7.3 — TTS notifications** — optional Chatterbox adapter
   reads phase transitions, verification failures, and handoffs aloud,
   guarded by `voice.tts.enabled = false` default.
4. **Slice 7.4 — Cross-platform audio test harness** — non-blocking
   smoke test that doesn't require a real microphone.

---

### Phase 8 — Provider Routing & Hardware-Aware Selection

```yaml
phase_id: PH-08
name: Provider Routing & Hardware-Aware Selection
mythic_role_bias: architect
priority: high
depends_on: [PH-06]
goal: >
  Add a router that picks the right provider/model per task type and
  available hardware, with explicit user-overridable defaults.
```

#### Slices

1. **Slice 8.1 — Routing table** — declarative mapping in
   `ai/router.py` from (role, task type, hardware profile) to provider/model.
2. **Slice 8.2 — Cost guards** — each call estimates cost; a
   configurable per-day cap blocks runaway spend with a clear error.
3. **Slice 8.3 — Fallback chain** — preferred provider → secondary →
   copy-paste, with logging of every fallback.
4. **Slice 8.4 — `mythic-vibe ai route` command** — explain why a
   given task would route where, with `--explain` and `--dry-run`.

---

### Phase 9 — Island Integrations

```yaml
phase_id: PH-09
name: Island Integrations (B/C/D/E)
mythic_role_bias: architect
priority: medium
depends_on: [PH-01, PH-05, PH-06]
goal: >
  Bring the dormant islands online via ADR-governed adapters with
  feature flags, per Law 9.
```

#### Slices

1. **Slice 9.1 — Island B (Yggdrasil router)** — resolve the
   `yggdrasil_core` ghost import; add `ai/providers/yggdrasil.py` as an
   optional Architect-agent backend.
2. **Slice 9.2 — Island C (MindSpark ThoughtForge)** — install as
   optional dep `mythic-vibe[mindspark]`; bridge via a Planner-agent
   call contract.
3. **Slice 9.3 — Island D (WYRD Protocol)** — in-process binding for
   `passive_oracle` as a Verifier-agent world-model check.
4. **Slice 9.4 — Island E (Chatterbox TTS)** — optional voice output
   adapter (Phase 7 covers the integration; this slice formalises the
   contract and feature flag).
5. **Slice 9.5 — Feature-flag toggle tests** — each island can be
   enabled or disabled without breaking the core.

---

### Phase 10 — Plugin Ecosystem & Community Infrastructure

```yaml
phase_id: PH-10
name: Plugin Ecosystem & Community Infrastructure
mythic_role_bias: scribe
priority: high
depends_on: [PH-01, PH-02]
goal: >
  Mature the plugin layer from "hooks fire" to a real ecosystem with
  discovery, isolation, sandboxing, a plugin registry, an authoring
  guide, and a community contribution workflow.
```

#### Slices

1. **Slice 10.1 — Entry-point discovery** — Python entry-point group
   `mythic_vibe.plugins`; `plugin install` resolves PyPI packages.
2. **Slice 10.2 — `plugins/sandbox.py`** — exception isolation,
   timing budgets, resource caps (best-effort cross-platform).
3. **Slice 10.3 — Extension points** — `RitualPlugin`,
   `ProviderPlugin`, `ScannerPlugin`, `VerificationGate`,
   `ArtifactTemplate`, `SlashCommandPlugin`.
4. **Slice 10.4 — `docs/PLUGIN_AUTHORING_GUIDE.md`** — step-by-step
   tutorial.
5. **Slice 10.5 — `plugins/REGISTRY.md`** — index of known community
   plugins.
6. **Slice 10.6 — Reference plugin** — ship a minimal example plugin
   in `examples/plugins/` that exercises every extension point.
7. **Slice 10.7 — `CONTRIBUTING.md`** — contribution workflow, ADR
   process, plugin validation requirements.

---

### Phase 11 — Security, Sandbox & Permissions Layer

```yaml
phase_id: PH-11
name: Security, Sandbox & Permissions Layer
mythic_role_bias: auditor
priority: critical
depends_on: [PH-01]
goal: >
  Treat the CLI as a security-sensitive tool. Add approval modes,
  redaction, secret scanning, sandbox execution, and dangerous-pattern
  detection — all opt-in by default, never silent.
```

#### Slices

1. **Slice 11.1 — Approval modes** — `suggest` (prompt every action),
   `auto-approve` (run without prompting), `partial` (allow read,
   prompt for write). Configured per project and per command.
2. **Slice 11.2 — Redaction engine** — extend the existing
   `mythic/ai/provider_calls.jsonl` redaction to a configurable
   pattern set; default-deny `.env`, `*.pem`, `*.key`, `*.token`.
3. **Slice 11.3 — Secret scanner** — pre-packet check for hardcoded
   API keys, credentials, and tokens.
4. **Slice 11.4 — Sandbox execution** — `runtime.exec` already runs
   `shell=False`; add directory restriction and network-disabled mode
   guarded by `sandbox.enabled = true`.
5. **Slice 11.5 — Dangerous pattern detection** — `eval`, `exec`,
   shell injection, unparameterised SQL — surfaced as warnings.
6. **Slice 11.6 — Privacy mode** — when enabled, no provider call
   includes any code outside an explicit allow-list.
7. **Slice 11.7 — `mythic-vibe security audit`** — full repo scan
   with severity-tagged findings.

---

### Phase 12 — CI/CD & Deployment Integration

```yaml
phase_id: PH-12
name: CI/CD & Deployment Integration
mythic_role_bias: forge
priority: medium
depends_on: [PH-01, PH-11]
goal: >
  First-class CI/CD touchpoints — workflow generation, automated
  containerisation, semantic versioning, and rollback support.
```

#### Slices

1. **Slice 12.1 — `mythic-vibe ci scaffold`** — generates a project's
   GitHub Actions workflow tuned to its tech stack.
2. **Slice 12.2 — `mythic-vibe docker scaffold`** — produces a
   Dockerfile + .dockerignore + docker-compose for the detected stack.
3. **Slice 12.3 — `mythic-vibe release`** — semver-aware release
   command that tags, builds, and prepares the changelog entry.
4. **Slice 12.4 — Rollback helper** — uses git history to summarise
   what to revert if a release misbehaves.

---

### Phase 13 — Drift Detection & Self-Healing

```yaml
phase_id: PH-13
name: Drift Detection & Self-Healing
mythic_role_bias: auditor
priority: high
depends_on: [PH-05, PH-11]
goal: >
  Make divergence between docs, code, and decisions visible and
  actionable; provide a `heal` command that proposes additive
  reconciliations.
```

#### Slices

1. **Slice 13.1 — Drift index** — graph-backed query for orphaned
   functions, undocumented modules, superseded decisions.
2. **Slice 13.2 — Doctor integration** — drift findings show up with
   severity in `doctor`.
3. **Slice 13.3 — `heal` v2** — generates a packet for the Scribe
   agent describing the additive reconciliation; never overwrites
   without approval.
4. **Slice 13.4 — Drift dashboard panel** — TUI surfaces drift in
   real time.

---

### Phase 14 — Policy Engine & Constraint Verification

```yaml
phase_id: PH-14
name: Policy Engine & Constraint Verification
mythic_role_bias: auditor
priority: high
depends_on: [PH-11, PH-13]
goal: >
  Enforce documented constraints at command time. If a command would
  violate a recorded constraint (e.g., an `oath`, an ADR, a
  `constraints.md` rule), the CLI warns and requires explicit override.
```

#### Slices

1. **Slice 14.1 — Constraint store** — read constraints from `oath`s,
   ADRs, and `constraints.md` into a typed model.
2. **Slice 14.2 — Pre-command policy check** — every write command
   passes through the policy gate.
3. **Slice 14.3 — Override workflow** — `--override "<reason>"`
   records the override in the handoff and DEVLOG.
4. **Slice 14.4 — Policy report** — `mythic-vibe policy report`
   shows current constraints and the override history.

---

### Phase 15 — Conversation Memory & Compaction

```yaml
phase_id: PH-15
name: Conversation Memory & Compaction
mythic_role_bias: scribe
priority: high
depends_on: [PH-05]
goal: >
  Persist provider conversations and compact long histories so context
  windows are well-used without losing reasoning trail.
```

#### Slices

1. **Slice 15.1 — Conversation log** — every provider call writes a
   structured record to `mythic/ai/conversations/`.
2. **Slice 15.2 — Compaction summariser** — compress old turns into a
   running summary, retaining decisions and constraints.
3. **Slice 15.3 — `mythic-vibe memory show`** — read conversation
   history with provenance.
4. **Slice 15.4 — `mythic-vibe memory rehydrate`** — pull the latest
   handoff + recent conversation summary into a session brief.

---

### Phase 16 — MCP / ACP / OpenTelemetry Protocols

```yaml
phase_id: PH-16
name: MCP / ACP / OpenTelemetry Protocols
mythic_role_bias: architect
priority: high
depends_on: [PH-01, PH-11]
goal: >
  Speak the standards: Model Context Protocol for tools/resources,
  Agent Communication Protocol for IDE/agent interop, OpenTelemetry for
  observability.
```

#### Slices

1. **Slice 16.1 — MCP server adapter** — expose Mythic's commands as
   MCP tools so external agents can invoke them.
2. **Slice 16.2 — MCP client adapter** — call MCP servers from inside
   `forge` (e.g., a database MCP for the Architect agent).
3. **Slice 16.3 — ACP support** — minimal IDE-bridge adapter so VS
   Code / JetBrains plugins can co-pilot with Mythic.
4. **Slice 16.4 — OpenTelemetry exporter** — every command emits
   spans to an OTLP endpoint; opt-in.

---

### Phase 17 — Multi-Surface Access

```yaml
phase_id: PH-17
name: Multi-Surface Access
mythic_role_bias: cartographer
priority: medium
depends_on: [PH-04, PH-16]
goal: >
  Beyond the local terminal: web terminal, mobile-friendly TUI, SSH
  access, and a chat bridge (Telegram or Matrix) — all opt-in, all
  open-source-only.
```

#### Slices

1. **Slice 17.1 — Web terminal** — bundle xterm.js + a small server
   that exposes the shell REPL behind a token.
2. **Slice 17.2 — Mobile-friendly TUI** — narrow-layout fallback for
   small terminals.
3. **Slice 17.3 — SSH-ready packaging** — document and test the
   common SSH flow.
4. **Slice 17.4 — Chat bridge** — Matrix-first, Telegram-second
   adapters; both fully open-source.

---

### Phase 18 — Robustness Sweeps Round 1–4

```yaml
phase_id: PH-18
name: Robustness Sweeps Round 1–4
mythic_role_bias: auditor
priority: critical
depends_on: spans all phases
goal: >
  Four full passes of "make all code robust, error correcting, bug
  resistant, self-healing, platform agnostic, file-location agnostic,
  use API for internal communication, modular." Per Volmarr's TODO,
  literally four rounds — each at a different layer of depth.
```

#### Slices (one per round)

1. **Slice 18.1 — Round 1: Boundary & error paths**
   - Every public function defends inputs.
   - Every IO operation handles the four file-system error families
     (missing, permission, locked, full).
   - Every subprocess call uses `runtime.exec` with timeout +
     cancellation.
2. **Slice 18.2 — Round 2: Concurrency & file-location agnosticism**
   - Every writer goes through `file_mutation_queue`.
   - Every path resolves through `pathlib` from a configurable root.
   - No hardcoded `mythic/` paths outside `core/state.py`.
3. **Slice 18.3 — Round 3: Internal API surfaces**
   - Each subpackage exposes a typed module-level API.
   - Cross-subpackage calls go through public APIs only (mypy
     enforced).
   - ADR-0005 documents the internal API contract.
4. **Slice 18.4 — Round 4: Self-healing & resilience simulation**
   - `mythic-vibe simulate` injects synthetic failures (network
     timeout, malformed `status.json`, missing artefact, provider
     failure) and confirms graceful degradation.
   - Doctor offers `--fix` for safe automatic remediations.

#### Done when

- 270 baseline → ≥ 600 tests after the four rounds.
- Coverage ≥ 90% on the active runtime.
- No subprocess call bypasses `runtime.exec`.
- No file write bypasses the mutation queue.
- `simulate` runs cleanly through all canonical failure modes.

---

### Phase 19 — Distribution

```yaml
phase_id: PH-19
name: Distribution
mythic_role_bias: scribe
priority: high
depends_on: [PH-01, PH-12, PH-18]
goal: >
  Ship the CLI through multiple channels with clean install, working
  console scripts, and reproducible releases.
```

#### Slices

1. **Slice 19.1 — PyPI publication** — automated via GitHub Actions
   `release` workflow.
2. **Slice 19.2 — pipx-friendly metadata** — minimal install, no heavy
   default deps.
3. **Slice 19.3 — Homebrew formula** — `brew install mythic-vibe`.
4. **Slice 19.4 — Scoop manifest** — Windows install path.
5. **Slice 19.5 — Docker image** — multi-stage Dockerfile with a slim
   runtime layer.
6. **Slice 19.6 — Documentation site** — MkDocs from `docs/` with
   search, command reference, plugin guide.

---

### Phase 20 — Mythic Vibe CLI v1.0.0 — Sovereign OS Launch

```yaml
phase_id: PH-20
name: Mythic Vibe CLI v1.0.0 — Sovereign OS Launch
mythic_role_bias: skald
priority: critical
depends_on: [PH-01..PH-19]
goal: >
  Cut a real 1.0.0 release. Confirm every quality gate. Publish to
  every distribution channel. Issue the launch announcement and a
  sealed Mythic Engineering manifest.
```

#### Slices

1. **Slice 20.1 — Release candidate** — branch `release/1.0.0`, tag
   `v1.0.0-rc.1`, run the full release checklist.
2. **Slice 20.2 — Soak window** — at least one full week of feedback
   on the RC.
3. **Slice 20.3 — Launch artefacts** — `LAUNCH.md`, blog post,
   announcement template, demo recordings.
4. **Slice 20.4 — Tag v1.0.0** — full release, publish, announce.
5. **Slice 20.5 — Post-launch retrospective** — Skald-led reflection
   captured in `docs/RETROSPECTIVE_v1.0.0.md`.

---

## 6. Cross-cutting quality bar

Every slice in every phase must pass:

```yaml
quality_bar:
  tests: pytest -q must be green
  lint: ruff check must be 0 diagnostics
  types: mypy must be clean (or noqa with reason)
  docs: behaviour change → docs change in same PR
  changelog: every user-facing change appended to CHANGELOG.md
  memory: every slice updates project_mythic_engineering_cli_status.md
  task_file: TASK_<name>.md progress tracker updated
  cross_platform: no per-OS branches; tested on at least Windows + Linux
  open_source: no proprietary required dependencies
  additive: no destructive removal without ADR
```

---

## 7. Method/role mapping

The Mythic Engineering six roles map onto this roadmap as follows:

| Role | Phases primarily owned |
|---|---|
| **Skald** (vision, naming) | 7 (Voice as expression), 20 (launch) |
| **Architect** (boundaries) | 3, 8, 9, 16 |
| **Forge Worker** (build) | 2, 6, 12 |
| **Auditor** (verify) | 1, 11, 13, 14, 18 |
| **Cartographer** (map) | 4, 17 |
| **Scribe** (memory) | 5, 10, 15, 19 |

A slice can borrow other roles when needed — the bias names the
*primary* responsible role, not the only one.

---

## 8. Slash-command surface (target)

The full target slash-command surface (Phase 2) and the underlying
argparse commands they resolve to:

| Slash | Underlying command | Phase |
|---|---|---|
| `/help` | help | existing |
| `/status` | status | existing |
| `/next` | next | existing |
| `/scan` | scan | existing |
| `/packet` | packet | existing |
| `/codex-pack` | codex-pack | existing |
| `/evoke` | packet create (alias) | existing |
| `/verify` | verify | existing |
| `/reflect` | reflect | existing |
| `/resume` | resume | existing |
| `/method` | method | existing |
| `/handoff` | handoff | existing |
| `/workflow` | workflow | existing |
| `/plugin` | plugin | existing |
| `/grimoire` | grimoire | existing |
| `/quit` | shell exit | existing |
| `/intent` | intent capture | PH-02 |
| `/constraints` | constraints capture | PH-02 |
| `/architecture` | architecture map | PH-02 |
| `/plan` | plan create | PH-02 |
| `/build` | build packet | PH-02 |
| `/forge` | forge | PH-03 |
| `/architect-agent` | forge --role architect | PH-03 |
| `/planner` | forge --role planner | PH-03 |
| `/builder` | forge --role builder | PH-03 |
| `/verifier` | forge --role verifier | PH-03 |
| `/voice` | voice | PH-07 |
| `/chat` | ai run | PH-06 |
| `/graph` | graph | PH-05 |
| `/rehydrate` | memory rehydrate | PH-15 |
| `/index` | scan --write-index | existing |
| `/search` | graph query | PH-05 |
| `/test` | verify --commands "pytest -q" | PH-02 |
| `/lint` | verify --commands "ruff check ." | PH-02 |
| `/typecheck` | verify --commands "mypy ." | PH-02 |
| `/audit` | doctor --json | PH-02 |
| `/review` | review (PR review) | PH-02 |
| `/security` | security audit | PH-11 |
| `/shield` | sandbox status | PH-11 |
| `/init` | init | existing |
| `/imbue` | init (alias) | existing |
| `/scaffold` | scaffold | PH-02 |
| `/weave` | weave | existing |
| `/prune` | prune | existing |
| `/heal` | heal | existing |
| `/oath` | oath | existing |
| `/ritual` | ritual | PH-10 |
| `/extension` | extension | PH-10 |
| `/skill` | skill | PH-10 |
| `/prompt` | prompt | PH-10 |
| `/plunder` | plunder | existing |
| `/sync` | sync | existing |
| `/import-md` | import-md | existing |
| `/export` | export | PH-19 |
| `/doctor` | doctor | existing |
| `/scry` | doctor (alias) | existing |
| `/simulate` | simulate | PH-18 |
| `/resilience` | simulate --resilience | PH-18 |
| `/telemetry` | telemetry | PH-16 |
| `/checkin` | checkin | existing |
| `/memory` | memory | PH-15 |
| `/ui` | tui (alias) | PH-04 |
| `/tui` | tui | existing |
| `/shell` | shell | existing |
| `/web` | web | PH-17 |
| `/mobile` | (info text) | PH-17 |
| `/changelog` | changelog | PH-02 |
| `/version` | --version | PH-02 |
| `/release` | release | PH-12 |
| `/package` | package | PH-19 |
| `/publish` | publish | PH-19 |
| `/policy` | policy | PH-14 |

---

## 9. Provenance map of folded plans

| Origin doc | Folded into phases |
|---|---|
| Production Roadmap Stages 0–2, 5–8, 10–15 | already shipped — referenced as baseline |
| Production Roadmap Stage 3 (Templates & profiles) | PH-02 (slash) + PH-10 (artefact templates) |
| Production Roadmap Stage 4 (Phase commands) | PH-02 (`/intent`, `/constraints`, `/architecture`, `/plan`, `/build`) |
| Production Roadmap Stage 9 (Deep doctor) | PH-13 + PH-14 |
| V2 Roadmap Phase 1 (Architectural Unification) | PH-01 |
| V2 Roadmap Phase 2 (6-Agent Engine) | PH-03 |
| V2 Roadmap Phase 3 (TUI/UX) | PH-04 |
| V2 Roadmap Phase 4 (Local-First Sovereignty) | PH-06 + PH-07 |
| V2 Roadmap Phase 5 (Knowledge Graph) | PH-05 |
| V2 Roadmap Phase 6 (MindSpark) | PH-09 (Island C) |
| V2 Roadmap Phase 7 (Plugin Ecosystem) | PH-10 |
| V2 Roadmap Phase 8 (Plunder/Provenance) | already shipped baseline; PH-10 hardens |
| V2 Roadmap Phase 9 (Drift/Self-Healing) | PH-13 |
| V2 Roadmap Phase 10 (Distribution) | PH-19 + PH-20 |
| 2026 Roadmap Phase 1 (Core Hardening) | PH-01 |
| 2026 Roadmap Phase 2 (Domain Refactor) | folded — already largely done |
| 2026 Roadmap Phase 3 (TUI Revolution) | PH-04 |
| 2026 Roadmap Phase 4 (Local LLM) | PH-06 + PH-08 |
| 2026 Roadmap Phase 5 (Multi-Agent) | PH-03 |
| 2026 Roadmap Phase 6 (Knowledge Graph) | PH-05 |
| 2026 Roadmap Phase 7 (Island Integration) | PH-09 |
| 2026 Roadmap Phase 8 (Plugin Ecosystem) | PH-10 |
| 2026 Roadmap Phase 9 (Advanced AI) | PH-13 + PH-14 + PH-15 |
| 2026 Roadmap Phase 10 (Release/Distribution) | PH-19 + PH-20 |
| Aggregate Feature Report — slash commands | PH-02 |
| Aggregate Feature Report — multi-provider | PH-06 + PH-08 |
| Aggregate Feature Report — sandbox/approval | PH-11 |
| Aggregate Feature Report — MCP/ACP | PH-16 |
| Aggregate Feature Report — telemetry | PH-16 |
| Aggregate Feature Report — multi-surface | PH-17 |
| Aggregate Feature Report — code review/PR/changelog | PH-12 |
| TODO.md — 4 robustness sweeps | PH-18 |
| TODO.md — Pi plundering | already shipped (8 primitives); residual reuse via PH-10 |
| TODO.md — V2 Phase 3+ | PH-04 |
| TODO.md — V2 Phase 4 | PH-06 |
| TODO.md — repo issues | PH-01 slice 1.2 |
| TODO.md — bug/incomplete sweep | PH-01 |

---

*The forge is lit. The hall is wide. The work begins at Phase 1.*
