# Mythic Vibe CLI: The 2026 Expansion Roadmap

**Author:** Manus AI  
**Date:** April 28, 2026  
**Target Repository:** [`hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`](https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding)  
**Branch:** `development`  
**Status:** Strategic Planning Document

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Design Laws and Expansion Principles](#design-laws-and-expansion-principles)
4. [Phase 1 — Architectural Unification and Core Hardening](#phase-1--architectural-unification-and-core-hardening-months-12)
5. [Phase 2 — Domain-Shaped Architecture Refactor](#phase-2--domain-shaped-architecture-refactor-months-34)
6. [Phase 3 — Terminal User Interface Revolution](#phase-3--terminal-user-interface-revolution-months-56)
7. [Phase 4 — Local LLM Orchestration and Provider Layer](#phase-4--local-llm-orchestration-and-provider-layer-months-78)
8. [Phase 5 — Multi-Agent Workflow Engine](#phase-5--multi-agent-workflow-engine-months-910)
9. [Phase 6 — Persistent Memory and Knowledge Graph](#phase-6--persistent-memory-and-knowledge-graph-months-1112)
10. [Phase 7 — Dormant Island Integration](#phase-7--dormant-island-integration-months-1315)
11. [Phase 8 — Plugin Ecosystem and Community Infrastructure](#phase-8--plugin-ecosystem-and-community-infrastructure-months-1618)
12. [Phase 9 — Advanced AI Capabilities and Drift Detection](#phase-9--advanced-ai-capabilities-and-drift-detection-months-1920)
13. [Phase 10 — Release, Distribution, and Community Growth](#phase-10--release-distribution-and-community-growth-months-2124)
14. [Command Expansion Reference](#command-expansion-reference)
15. [Target Package Architecture](#target-package-architecture)
16. [Quality Gates and Success Metrics](#quality-gates-and-success-metrics)
17. [References](#references)

---

## Executive Summary

The `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding` repository is built on a rare and valuable premise: that AI-assisted software development ("vibe coding") produces better outcomes when it is governed by an explicit, artifact-preserving methodology rather than raw generative momentum. The Mythic Engineering loop — `intent -> constraints -> architecture -> plan -> build -> verify -> reflect` — is not merely a workflow; it is a philosophy of recoverable, auditable, and durable software creation.

The current implementation, however, remains an early skeleton. The active `mythic_vibe_cli` package is a tight six-file runtime floating in a monorepo of five disconnected "islands" — the Norse Saga Engine, MindSpark ThoughtForge, the WYRD Protocol, upstream vendor mirrors, and the CLI itself. The CLI can scaffold projects, generate prompt packets for ChatGPT and Codex, and track phase state in a JSON file. It cannot yet orchestrate local models, render interactive terminal interfaces, maintain persistent cross-session memory, or coordinate multiple specialized AI agents.

This roadmap charts a 24-month expansion strategy organized into ten phases. It is designed to transform the Mythic Vibe CLI into the **command-line operating system for disciplined AI-assisted software engineering** — a tool that is local-first, provider-agnostic, architecturally rigorous, and genuinely beginner-safe while being capable enough for the most complex, long-lived codebases.

The expansion is organized around four strategic pillars:

1. **Structural integrity** — resolving the dormant islands, hardening the core, and enforcing domain boundaries with machine-checked contracts.
2. **Sensory richness** — building a Textual-based Terminal User Interface (TUI) that makes the Mythic Engineering loop visible, navigable, and interactive.
3. **Cognitive depth** — integrating local LLMs via Ollama, building a multi-agent orchestration engine, and implementing a persistent knowledge graph that survives session boundaries.
4. **Ecosystem breadth** — shipping a plugin architecture, community documentation, and a release pipeline that makes the tool installable, extensible, and trustworthy for external contributors.

---

## Current State Assessment

### The Five Islands

The repository is not one system. It is five islands sharing a root directory. Understanding their current state is the prerequisite for every expansion decision.

| Island | Key Directories | Status | Primary Blocker |
| :--- | :--- | :--- | :--- |
| **A — Mythic Vibe CLI** | `mythic_vibe_cli/`, `tests/`, `docs/` | **LIVE** — only working end-to-end path | Early skeleton; no provider layer, no plugin loading, no TUI |
| **B — Norse Saga Engine** | `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/` | **DORMANT** — broken imports | `yggdrasil_core` ghost import; cannot load cleanly |
| **C — MindSpark ThoughtForge** | `mindspark_thoughtform/` | **DORMANT** — self-contained, uninstalled | Not installed; no call contract from CLI |
| **D — WYRD Protocol** | `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | **DORMANT** — self-contained, complete | Expects HTTP bridges; no in-process adapter |
| **E — Upstream Vendors** | `ollama/`, `whisper/`, `chatterbox/` | **DORMANT** — source mirrors only | Not imported anywhere; no Python client wiring |

### Active Runtime Inventory

The current active CLI runtime is deliberately narrow. The following files constitute the entire working product:

```
mythic_vibe_cli/
  __init__.py
  cli.py           — argv parsing, command dispatch
  codex_bridge.py  — prompt packet rendering, excerpt limits
  config.py        — layered config resolution
  mythic_data.py   — GitHub corpus sync, local cache
  workflow.py      — seven-phase state, template writing, DEVLOG
```

The test surface covers `test_cli.py`, `test_config_and_bridge.py`, and `test_workflow.py`. The documentation surface is well-structured but not yet machine-enforced against the implementation.

### Implemented Commands

The CLI already implements a meaningful command vocabulary:

```
init / start / imbue      — project scaffolding
checkin                   — phase check-in and DEVLOG update
status                    — project state summary
import-md                 — import Mythic Engineering corpus
codex-pack / evoke        — generate AI prompt packets
codex-log                 — persist AI response summaries
sync                      — sync method corpus from GitHub
method                    — display method reference
doctor / scry             — diagnostic checks
weave                     — link artifacts
prune                     — remove stale artifacts
heal                      — repair broken state
oath                      — commit to a constraint
grimoire add|list         — manage ritual references
config / config set       — configuration management
db migrate                — SQLite schema migration
plunder                   — import from external repositories
```

### Architectural Weaknesses Requiring Expansion

The production roadmap must address the following structural gaps, each of which limits the tool's ability to fulfill its philosophical promises:

| Weakness | Impact | Expansion Phase |
| :--- | :--- | :--- |
| No provider abstraction layer | CLI is hard-coded to ChatGPT/Codex copy-paste workflow | Phase 4 |
| No plugin loading | `plugins/` directory exists but loads nothing | Phase 8 |
| No TUI | All output is plain text; no interactive review or diff visualization | Phase 3 |
| No local LLM support | Ollama vendor mirror is unused; no Python client | Phase 4 |
| No multi-agent orchestration | Single prompt generator; no Architect/Builder/Verifier separation | Phase 5 |
| No persistent knowledge graph | Context collapses between sessions | Phase 6 |
| Flat `status.json` | No schema versioning, no migration, no phase history | Phase 2 |
| Dormant islands unresolved | Five islands with no integration contracts | Phase 7 |
| No community plugin ecosystem | No registry, no contribution guide for extensions | Phase 8 |

---

## Design Laws and Expansion Principles

Every expansion decision must be evaluated against the core design laws established in the project's existing documentation. These laws are not aspirational — they are hard constraints.

> **Law 1 — The method is executable.** The CLI must not merely describe Mythic Engineering. It must enforce, guide, record, and verify the method.

> **Law 2 — No hidden memory.** Anything important must be written to disk in a predictable place.

> **Law 3 — Project state is a first-class object.** `status.json` must evolve into a real project state model with schema versioning, migrations, phase history, open tasks, risks, decisions, and verification records.

> **Law 4 — AI output is never automatically trusted.** The CLI must enforce the sequence: `proposal -> user review -> applied change -> verification -> reflection`.

> **Law 5 — Documents are not decoration.** Docs are part of the runtime method. Drift between docs and code is a diagnostic failure.

> **Law 6 — Every subsystem has an owner.** If a feature cannot be assigned to a domain, it is not ready to be implemented.

> **Law 7 — The CLI should be useful without cloud AI.** The offline/local path must still scaffold, scan, plan, diagnose, and preserve continuity.

> **Law 8 — The user owns the work.** The CLI must not lock the user into one AI vendor, one editor, one platform, or one worldview of software work.

Two additional laws are proposed for the expansion:

> **Law 9 — Islands integrate through contracts, not imports.** No dormant island may be wired into the active CLI without a documented ADR, a defined call contract, and a feature flag that allows the integration to be disabled without breaking the core.

> **Law 10 — Plugins fail safely.** Any plugin failure must be caught, logged, and surfaced as a diagnostic warning. It must never crash the CLI or corrupt project state.

---

## Phase 1 — Architectural Unification and Core Hardening (Months 1–2)

This phase establishes the structural foundation upon which all subsequent expansion depends. No new features are added. The goal is to make the existing CLI deterministic, observable, and boundary-safe.

### 1.1 Resolving the Ghost Import

The most urgent structural problem is the `yggdrasil_core` ghost import in Island B. The files `core/emotional.py` and `core/dream_system.py` import a package that does not exist anywhere in the repository. This creates false-positive coupling and prevents any future integration work from reasoning cleanly about the codebase.

The resolution strategy is to audit every file in `ai/`, `core/`, `systems/`, `sessions/`, and `yggdrasil/` for broken imports, and document the findings in a new `ISLAND_B_AUDIT.md`, so they can be integrated. The `yggdrasil/` directory should be renamed or reorganized to match the import path that Island B expects.

### 1.2 Domain Boundary Enforcement

The repository's `REPO_BOUNDARY.md` and `docs/ACTIVE_PRODUCT_BOUNDARY.md` define the active runtime path, but these rules are not machine-enforced. A boundary checker script must be added to the CI/CD pipeline.

The script should parse all Python import statements in `mythic_vibe_cli/` and verify that no file imports from the dormant islands (`ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, `mindspark_thoughtform/`, `WYRD-Protocol-*/`, `ollama/`, `whisper/`, `chatterbox/`) without an explicit ADR entry permitting the integration. Any violation should fail the CI build with a clear error message identifying the offending import and the relevant boundary document.

### 1.3 Structured Observability

The current CLI uses `print()` and basic `output.py` helpers for all user-facing messages. This must be replaced with a two-layer output system:

The **user-facing layer** continues to use Rich-formatted terminal output for human-readable messages. The **machine-readable layer** writes structured JSON log entries to `~/.mythic-vibe/logs/` with the following schema:

```json
{
  "run_id": "uuid4",
  "timestamp": "ISO-8601",
  "command": "codex-pack",
  "phase": "plan",
  "duration_ms": 342,
  "result": "success",
  "artifacts_written": ["mythic/codex_prompt.md"],
  "warnings": []
}
```

This structured log enables future performance budgeting, drift detection, and audit trail generation without requiring any changes to the user-facing output.

### 1.4 State Model Evolution

The current `mythic/status.json` is a flat key-value store. It must evolve into a versioned state model. The new schema should include:

```json
{
  "schema_version": "2.0.0",
  "project_id": "uuid4",
  "project_name": "string",
  "current_phase": "plan",
  "phase_history": [
    {"phase": "intent", "entered_at": "ISO-8601", "completed_at": "ISO-8601", "artifacts": []}
  ],
  "open_tasks": [],
  "risks": [],
  "decisions": [],
  "verification_records": [],
  "last_session": "ISO-8601",
  "last_handoff": "path/to/handoff.md"
}
```

A migration command (`mythic-vibe db migrate`) must be extended to handle upgrades from the v1 schema to v2 without data loss.

### 1.5 Golden-Path Test Suite

The existing test suite covers basic CLI invocation but lacks golden-path tests for the most critical command sequences. The following test scenarios must be implemented before Phase 2 begins:

| Test Scenario | Commands Covered | Success Criterion |
| :--- | :--- | :--- |
| Full project initialization | `init`, `status`, `doctor` | All scaffold files present; status shows `intent` phase |
| Phase progression | `checkin`, `status` | Phase advances correctly; DEVLOG updated |
| Codex packet generation | `codex-pack`, `codex-log` | Packet file written; log entry persisted |
| Config resolution | `config`, `config set` | Correct precedence order honored |
| Diagnostic failure detection | `doctor` | Missing files reported with actionable messages |

### Phase 1 Success Metrics

| Metric | Target |
| :--- | :--- |
| Forbidden import violations in CI | 0 |
| Command failures without actionable error text | 0 |
| Core command test pass rate | > 90% |
| `status.json` schema version | 2.0.0 |
| Structured log entries per command run | 1 minimum |

---

## Phase 2 — Domain-Shaped Architecture Refactor (Months 3–4)

The current flat package structure (`cli.py`, `workflow.py`, `codex_bridge.py`, `config.py`, `mythic_data.py`) conflates concerns that will become unmanageable as the CLI grows. This phase introduces a domain-shaped architecture that separates the UI layer from the core domain logic.

### 2.1 Proposed Package Structure

The refactored package should follow the domain-shaped layout proposed in the existing `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md`:

```
mythic_vibe_cli/
  __init__.py
  __main__.py

  cli/
    app.py              — Typer/Click application entry point
    commands/
      init.py           — project initialization
      status.py         — status display
      checkin.py        — phase check-in
      doctor.py         — diagnostics
      plan.py           — planning commands
      codex.py          — prompt packet generation and logging
      ai.py             — AI provider commands
      scan.py           — repository scanning
      verify.py         — verification gates
      reflect.py        — reflection and handoff
      config.py         — configuration management
      db.py             — database migrations
      plugin.py         — plugin management
      plunder.py        — external repository import
      ritual.py         — ritual aliases
    output.py           — Rich-formatted terminal output
    errors.py           — user-facing error messages

  core/
    phases.py           — phase definitions and transitions
    method.py           — Mythic Engineering method enforcement
    project.py          — project model and state management
    state.py            — status.json schema and migrations
    artifacts.py        — artifact registry and validation
    events.py           — event bus for cross-domain communication
    errors.py           — domain error types

  workflow/
    engine.py           — phase transition engine
    transitions.py      — valid transition rules
    checkins.py         — check-in logic and DEVLOG updates
    handoff.py          — session handoff generation
    reflection.py       — reflection artifact generation

  ai/
    providers/
      base.py           — abstract provider interface
      openai.py         — OpenAI/Codex adapter
      ollama.py         — Ollama local model adapter
      anthropic.py      — Anthropic Claude adapter
      gemini.py         — Google Gemini adapter
    bridge.py           — prompt packet assembly
    router.py           — hardware-aware provider routing
    response.py         — response parsing and logging

  context/
    scanner.py          — repository scanning and entity extraction
    graph.py            — local knowledge graph (SQLite-backed)
    retriever.py        — contextual retrieval for prompt packets
    rehydrator.py       — session context rehydration

  persistence/
    store.py            — unified persistence interface
    migrations.py       — schema migration engine
    session.py          — session record management

  plugins/
    loader.py           — plugin discovery and loading
    registry.py         — plugin registry
    sandbox.py          — plugin fault isolation

  verify/
    gates.py            — verification gate definitions
    runner.py           — gate execution engine
    reporter.py         — verification report generation

  diagnostics/
    checker.py          — diagnostic check implementations
    reporter.py         — diagnostic report formatting
```

### 2.2 Migration Strategy

The refactor must be executed without breaking the existing command interface. The migration strategy is:

1. Create the new package structure alongside the existing flat files.
2. Move logic incrementally, one domain at a time, starting with `core/`.
3. Keep the existing `cli.py` as a thin shim that delegates to the new `cli/commands/` modules until the migration is complete.
4. Run the golden-path test suite after each domain migration to verify no regressions.
5. Remove the old flat files only after all commands pass their tests against the new structure.

---

## Phase 3 — Terminal User Interface Revolution (Months 5–6)

The CLI's current output is entirely text-based. While this is appropriate for scripting and automation, it creates a significant usability gap for the interactive, exploratory nature of AI-assisted development. This phase introduces a rich TUI that makes the Mythic Engineering loop visible, navigable, and interactive. [1]

### 3.1 The Mythic Dashboard (`mythic-vibe ui`)

The primary TUI mode is invoked with `mythic-vibe ui` and presents a full-terminal dashboard organized into four panels:

**Panel 1 — The Loop Navigator (left sidebar).** A visual representation of the seven-phase Mythic Engineering loop. The current phase is highlighted. Completed phases show a checkmark and the timestamp of completion. Blocked phases show a warning indicator. The user can navigate between phases using keyboard shortcuts.

**Panel 2 — The Artifact Viewer (main panel, left).** A scrollable view of the current phase's required artifacts. Each artifact is listed with its file path, last-modified timestamp, and a status indicator (present/missing/stale). Selecting an artifact opens it in the editor panel.

**Panel 3 — The AI Packet Viewer (main panel, right).** When a codex packet has been generated, this panel displays the full packet content with syntax highlighting. The user can edit the packet directly before sending it to an AI provider, ensuring that no context is sent without explicit review.

**Panel 4 — The Status Bar (bottom).** Displays the current project name, active phase, last check-in time, and any active diagnostic warnings.

### 3.2 Interactive Diff Review

When an AI response is logged via `codex-log`, the CLI will attempt to parse any code blocks in the response and present them as a diff against the current codebase. The diff view will:

- Highlight additions in green and deletions in red, following standard diff conventions.
- Allow the user to accept or reject individual hunks using keyboard shortcuts (`a` to accept, `r` to reject, `s` to skip).
- Write only the accepted changes to disk, ensuring that the user remains sovereign over every modification.

This enforces Law 4 (AI output is never automatically trusted) at the interface level, making it structurally impossible to apply AI-generated changes without explicit user review.

### 3.3 Real-Time Diagnostics Panel

The `doctor` command currently runs as a one-shot check. In TUI mode, diagnostics run continuously in a background thread and surface warnings in real time. The diagnostic panel will display:

- Missing required artifacts for the current phase.
- Stale artifacts (modified more than 7 days ago without a corresponding DEVLOG entry).
- Import boundary violations detected by the boundary checker.
- Configuration drift (environment variables overriding project config without a logged rationale).

### 3.4 Keyboard Navigation and Accessibility

The TUI must be fully keyboard-navigable, with no mouse dependency. The following keyboard shortcuts will be implemented:

| Key | Action |
| :--- | :--- |
| `Tab` / `Shift+Tab` | Cycle between panels |
| `j` / `k` | Scroll down / up within a panel |
| `Enter` | Open selected artifact in editor |
| `p` | Generate codex packet for current phase |
| `c` | Open check-in dialog |
| `d` | Toggle diagnostics panel |
| `q` | Quit TUI, return to standard CLI |
| `?` | Display keyboard shortcut reference |

---

## Phase 4 — Local LLM Orchestration and Provider Layer (Months 7–8)

The current CLI is designed around a copy-paste workflow with ChatGPT and Codex. This is a pragmatic starting point, but it creates vendor lock-in, requires internet connectivity, and exposes project context to external services. This phase introduces a proper provider abstraction layer and native Ollama integration. [2]

### 4.1 The Provider Abstraction Layer

All AI interactions must flow through a unified provider interface defined in `ai/providers/base.py`. The interface contract is:

```python
class BaseProvider:
    def complete(self, prompt: str, context: dict) -> str: ...
    def stream(self, prompt: str, context: dict) -> Iterator[str]: ...
    def embed(self, text: str) -> list[float]: ...
    def health_check(self) -> ProviderStatus: ...
```

Each concrete provider adapter implements this interface. The CLI's `codex-pack` command will no longer generate a static file for manual copy-paste; instead, it will route the packet directly to the configured provider and stream the response back to the terminal.

### 4.2 Native Ollama Integration

The repository currently contains a full Go source mirror of the Ollama project in the `ollama/` directory. This mirror must be removed and replaced with the official `ollama` Python package. The `ai/providers/ollama.py` adapter will:

- Detect whether an Ollama daemon is running on the default port (11434).
- If the daemon is not running, offer to start it automatically (with user confirmation).
- Support model selection from the user's locally installed models.
- Stream responses back to the CLI in real time, displaying a progress indicator.

The existing `ai/local_providers.py` file in Island B already contains compatible logic for Ollama integration. Once the ghost import issue is resolved in Phase 1, this file can serve as a reference implementation for the new adapter.

### 4.3 Hardware-Aware Provider Routing

Not all tasks require the same model capability. The CLI will implement a routing strategy based on task complexity and available hardware:

| Task Type | Local Route (Ollama) | Cloud Route (OpenAI/Anthropic) |
| :--- | :--- | :--- |
| Simple scaffolding | Llama 3.2 (3B) | GPT-4.1-mini |
| Phase planning | Llama 3.1 (8B) | GPT-4.1 |
| Architecture review | Mistral (7B) | Claude 3.7 Sonnet |
| Code generation | Qwen2.5-Coder (7B) | GPT-4.1 / Claude 3.7 |
| Verification review | Llama 3.1 (70B) via API | GPT-4.1 |

The routing decision is made based on the `docs/hardware_profiles.md` file (which already exists in the repository) and the user's configured provider preferences. Cloud routes are only used when explicitly configured or when the user's hardware cannot run the required local model.

### 4.4 Whisper Integration for Voice-Driven Workflows

The `whisper/` directory contains a full source mirror of OpenAI's Whisper speech recognition model. This mirror should be replaced with the `openai-whisper` package, and a new `mythic-vibe voice` command should be introduced that allows developers to dictate intent, constraints, and check-in notes using their microphone. The transcribed text is then processed through the standard Mythic Engineering workflow, with the user reviewing the transcription before it is committed to any artifact.

---

## Phase 5 — Multi-Agent Workflow Engine (Months 9–10)

The Mythic Engineering loop is inherently multi-perspective. A single AI model generating both the architecture and the code is analogous to having the same person write the requirements and perform the code review — the conflicts of interest are structural. This phase introduces a multi-agent orchestration engine that assigns specialized roles to different AI instances. [3]

### 5.1 Agent Role Definitions

The orchestration engine defines four canonical agent roles, each with a specific input contract, output contract, and verification gate:

| Agent | Role | Input Contract | Output Contract | Verification Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Rúnhild (Architect)** | System design and boundary definition | `intent.md`, `constraints.md` | `ARCHITECTURE.md`, `DOMAIN_MAP.md`, `DATA_FLOW.md` | Architecture review by Verifier |
| **Volmarr (Planner)** | Task breakdown and sequencing | `ARCHITECTURE.md`, `DOMAIN_MAP.md` | `mythic/plan.md`, `tasks/current_GOALS.md` | Plan review by Architect |
| **Skald (Builder)** | Code generation and implementation | `mythic/plan.md`, source context | Code diffs, new files | Test suite pass rate |
| **Védis (Verifier)** | Adversarial review and testing | Code diffs, `ARCHITECTURE.md`, test suite | Verification report, pass/fail status | Human approval |

The agent names are drawn from the project's existing Norse mythology theme, honoring the cultural identity of the codebase.

### 5.2 Orchestration Engine

The orchestration engine (`workflow/engine.py`) manages the handoffs between agents. The engine enforces the following invariants:

The Builder (Skald) cannot receive a task until the Architect (Rúnhild) has produced and the Planner (Volmarr) has sequenced it. The Verifier (Védis) cannot sign off on code until the test suite has been run and the results have been attached to the verification report. The human user must approve the Verifier's report before any changes are committed to the project's artifact store.

The engine exposes a new CLI command, `mythic-vibe forge`, that initiates a full multi-agent cycle for a given task:

```bash
mythic-vibe forge --task "Implement the plugin loader" --phase build
```

This command will:
1. Invoke the Architect agent to review the existing architecture for the relevant domain.
2. Invoke the Planner agent to break the task into implementation steps.
3. Present the plan to the user for review and approval.
4. Invoke the Builder agent to generate code for each approved step.
5. Run the test suite automatically.
6. Invoke the Verifier agent to review the code against the architecture and test results.
7. Present the Verifier's report to the user for final approval.
8. Write the approved changes and a reflection entry to the project's artifact store.

### 5.3 Agent Configuration

There are 6 agents, as per https://github.com/hrabanazviking/Mythic-Engineering
```

This configuration honors Law 8 (the user owns the work) by making every AI interaction explicit, configurable, and replaceable.

---

## Phase 6 — Persistent Memory and Knowledge Graph (Months 11–12)

The most significant limitation of current AI coding assistants is context collapse — they forget the project's history between sessions [4]. The Mythic Engineering methodology already addresses this through Markdown artifacts, but flat files are not queryable. This phase introduces a local knowledge graph that makes the repository's accumulated knowledge searchable, retrievable, and persistently available across sessions.

### 6.1 The Local Knowledge Graph

The knowledge graph is implemented as a SQLite database stored at `<project>/.mythic/knowledge.db`. It is populated by the `context/scanner.py` module, which parses the repository on each `checkin` and updates the graph with any changes.

The graph models the following entity types and relationships:

| Entity Type | Attributes | Relationships |
| :--- | :--- | :--- |
| `Module` | name, path, language, last_modified | `imports`, `imported_by`, `documented_by` |
| `Function` | name, signature, docstring, path | `calls`, `called_by`, `defined_in` |
| `Document` | name, path, type, last_modified | `describes`, `references`, `supersedes` |
| `Decision` | id, title, date, status, rationale | `affects`, `supersedes`, `implements` |
| `Phase` | name, entered_at, completed_at | `produced`, `consumed`, `transitioned_to` |
| `Task` | id, title, status, phase | `blocks`, `blocked_by`, `implements` |

### 6.2 Contextual Retrieval for Prompt Packets

When generating a codex packet, the current implementation reads a fixed set of files and applies a character budget. The new retriever (`context/retriever.py`) will query the knowledge graph to identify the most relevant context for the current task:

1. Parse the task description to extract key entities (module names, function names, document types).
2. Query the graph for entities related to those keys.
3. Rank the related entities by relevance score (recency, centrality in the graph, phase alignment).
4. Retrieve the top-ranked artifacts and assemble them into the packet, respecting the `MYTHIC_PACKET_CHAR_BUDGET`.

This approach ensures that the prompt packet contains the most relevant context rather than a fixed set of files, dramatically improving the quality of AI-generated outputs for complex, long-lived projects.

### 6.3 Session Rehydration

At the start of each session, the CLI will run a rehydration sequence:

1. Read the most recent `SESSION_HANDOFF_TEMPLATE.md` entry.
2. Query the knowledge graph for any changes since the last session (new modules, modified documents, completed tasks).
3. Generate a "session brief" — a concise summary of the project's current state, open threads, and recommended next actions.
4. Display the session brief in the terminal and offer to include it as the opening context for the first AI interaction.

This eliminates the most common productivity loss in AI-assisted development: the time spent re-explaining the project to an AI that has forgotten everything since the last session. [4]

### 6.4 Drift Detection Engine

The knowledge graph enables a new class of diagnostic: drift detection. The drift detector (`diagnostics/checker.py`) will compare the graph's model of the codebase against the documented architecture and flag discrepancies:

- Functions that exist in the code but are not documented in any `ARCHITECTURE.md` or `DOMAIN_MAP.md`.
- Documents that describe modules that no longer exist.
- Architectural decisions that were made but whose implementation cannot be found in the codebase.
- Phase artifacts that are older than the configured staleness threshold without a corresponding DEVLOG update.

Drift is reported as a structured warning in the `doctor` output and in the TUI's real-time diagnostics panel.

---

## Phase 7 — Dormant Island Integration (Months 13–15)

With the core hardened, the architecture refactored, the TUI active, the provider layer in place, the agents orchestrated, and the knowledge graph operational, the dormant islands can be integrated safely. Each integration follows the same contract-first process: define the ADR, write the adapter, implement the feature flag, and run the integration tests before merging.

### 7.1 Yggdrasil Router Integration (Island B)

The Yggdrasil router is the most architecturally significant dormant component. Once the ghost import issue is resolved (Phase 1), the router can be integrated as an optional reasoning backend for the Architect agent.

The integration contract (Seam S-1 from `ARCHITECTURE.md`) requires:
- A CLI subcommand (`mythic-vibe yggdrasil route`) that invokes the router for a given intent.
- A feature flag (`yggdrasil.enabled: false` by default) that allows the integration to be disabled without affecting the core CLI.
- A provider adapter in `ai/providers/` that wraps the Yggdrasil router as a local inference backend.

### 7.2 MindSpark ThoughtForge Integration (Island C)

MindSpark ThoughtForge is labeled v1.0.0 / Production-Stable in its own `pyproject.toml`. Its `thoughtforge.cognition` module can be integrated as an optional cognitive enhancement layer for the Planner agent.

The integration contract (Seam S-2 from `ARCHITECTURE.md`) requires:
- Installing MindSpark as an optional dependency (`pip install mythic-vibe[mindspark]`).
- A feature flag (`mindspark.enabled: false` by default).
- A call contract that allows the Planner agent to invoke `thoughtforge.cognition.plan()` with a task description and receive a structured plan in return.

### 7.3 WYRD Protocol Integration (Island D)

The WYRD Protocol (World-Yielding Real-time Data) is the most complete dormant island, labeled v1.0.0 RELEASED in its own documentation. Its `passive_oracle` module can be integrated as a world-modeling backend for the Verifier agent.

The integration contract (Seam S-3 from `ARCHITECTURE.md`) requires:
- Building an in-process binding that wraps the WYRD HTTP API in a Python function call.
- A feature flag (`wyrd.enabled: false` by default).
- A verification gate that invokes the WYRD oracle to validate that a proposed code change is consistent with the project's documented world model.

### 7.4 Chatterbox TTS Integration (Island E)

The Chatterbox TTS library (from Resemble AI) can be integrated as an optional voice output layer for the CLI. When enabled, the CLI will read important notifications aloud — phase transitions, verification failures, and session handoff summaries — using a configurable voice profile.

This integration is lower priority than the reasoning backends but aligns with the project's Norse mythology theme: the CLI becomes a literal skald, narrating the engineering saga as it unfolds.

---

## Phase 8 — Plugin Ecosystem and Community Infrastructure (Months 16–18)

The `mythic_vibe_cli/plugins/` directory exists but loads nothing. This phase builds the plugin infrastructure that allows the community to extend the CLI with custom rituals, provider adapters, scanners, and verification gates. [6]

### 8.1 Plugin Architecture

Plugins are Python packages that implement one or more of the following extension points:

| Extension Point | Interface | Example Use Case |
| :--- | :--- | :--- |
| `RitualPlugin` | `execute(context: ProjectContext) -> RitualResult` | Custom phase transition rituals |
| `ProviderPlugin` | `BaseProvider` interface | New AI provider adapters |
| `ScannerPlugin` | `scan(path: Path) -> ScanResult` | Custom repository scanners |
| `VerificationGate` | `check(context: ProjectContext) -> GateResult` | Custom verification rules |
| `ArtifactTemplate` | `render(context: ProjectContext) -> str` | Custom document templates |

Plugins are discovered via Python entry points, following the standard `importlib.metadata` plugin pattern. [6] A plugin declares itself by adding an entry point in its `pyproject.toml`:

```toml
[project.entry-points."mythic_vibe.plugins"]
my_plugin = "my_package.plugin:MyPlugin"
```

### 8.2 Plugin Fault Isolation

Following Law 10 (plugins fail safely), the plugin loader wraps every plugin invocation in a try/except block and logs any exception as a structured warning. Plugin failures are surfaced in the `doctor` output and the TUI diagnostics panel, but they never propagate to the core CLI. The `plugins/sandbox.py` module implements this isolation layer.

### 8.3 Community Infrastructure

To support external contributors, the following community infrastructure must be established:

- A `CONTRIBUTING.md` guide that explains the plugin architecture, the ADR process, and the contribution workflow.
- A `plugins/REGISTRY.md` file that lists known community plugins with their installation instructions and feature flags.
- A `docs/PLUGIN_AUTHORING_GUIDE.md` that provides a step-by-step tutorial for building a new plugin.
- A GitHub Actions workflow that validates plugin packages against the plugin interface contract before they are listed in the registry.

---

## Phase 9 — Advanced AI Capabilities and Drift Detection (Months 19–20)

With the full infrastructure in place, this phase introduces the most advanced AI capabilities: adaptive context curation, policy-aware command planning, resilience simulation, and the full drift detection engine.

### 9.1 Adaptive Context Curation

The knowledge graph retriever (Phase 6) provides relevance-ranked context. This phase extends it with adaptive curation: the CLI learns from the user's feedback on AI responses to improve future context selection.

When the user accepts or rejects a codex packet's suggested changes, the CLI records the outcome in the knowledge graph. Over time, the retriever builds a model of which context artifacts produce high-quality AI responses for which types of tasks, and adjusts its ranking accordingly.

### 9.2 Policy-Aware Command Planning

The CLI will introduce a policy engine that evaluates proposed commands against the project's documented constraints before executing them. If a command would violate a documented constraint (e.g., adding a dependency that was explicitly excluded in `constraints.md`), the CLI will warn the user and require explicit override confirmation.

This enforces Law 1 (the method is executable) at the command level, making it structurally difficult to violate the project's own constraints accidentally.

### 9.3 Resilience Simulation Mode

The CLI will introduce a `mythic-vibe simulate` command that runs the project's verification gates against a set of synthetic failure scenarios:

- Network timeout during `sync` or `import-md`.
- Malformed `status.json` (simulating file corruption).
- Missing required artifact at phase transition.
- Provider API failure during codex packet generation.

The simulation results are written to `docs/RESILIENCE_REPORT.md` and surfaced in the `doctor` output. This allows developers to verify that their project's error handling is robust before encountering failures in production.

---

## Phase 10 — Release, Distribution, and Community Growth (Months 21–24)

The final phase transforms the CLI from a development-stage tool into a production-ready, community-supported open-source project.

### 10.1 Release Pipeline

A fully automated release pipeline must be established using GitHub Actions:

1. **Lint and format check** — `ruff`, `black`, `mypy`.
2. **Boundary violation check** — the domain boundary enforcement script from Phase 1.
3. **Unit and integration tests** — `pytest` with coverage reporting.
4. **Snapshot tests** — codex packet rendering snapshots from Phase 2.
5. **Security audit** — `pip-audit` for dependency vulnerabilities.
6. **License check** — verify all dependencies are compatible with Apache 2.0.
7. **Build and publish** — `python -m build` and `twine upload` to PyPI.

### 10.2 Distribution Strategy

The CLI should be distributable via multiple channels to maximize accessibility:

| Channel | Command | Target Audience |
| :--- | :--- | :--- |
| PyPI | `pip install mythic-vibe` | Python developers |
| pipx | `pipx install mythic-vibe` | Isolated CLI installation |
| Homebrew | `brew install mythic-vibe` | macOS users |
| Scoop | `scoop install mythic-vibe` | Windows users |
| Docker | `docker run mythic-vibe` | Containerized environments |

### 10.3 Documentation Site

The existing `docs/` directory should be published as a static documentation site using MkDocs or Docusaurus. The site should include:

- The full command reference (`docs/api.md`).
- The quickstart guide (`docs/quickstart.md`).
- The plugin authoring guide.
- The Mythic Engineering methodology reference.
- A searchable changelog.

---

## Command Expansion Reference

The following table documents the full command vocabulary for the expanded CLI, organized by domain. Commands marked with `[NEW]` are additions to the current implementation. Commands marked with `[ENHANCED]` are existing commands with significantly expanded capabilities.

| Command | Domain | Status | Description |
| :--- | :--- | :--- | :--- |
| `mythic-vibe init` | Scaffolding | EXISTING | Initialize a new project with Mythic Engineering scaffold |
| `mythic-vibe imbue` | Scaffolding | EXISTING | Add Mythic Engineering structure to an existing project |
| `mythic-vibe ui` | TUI | **NEW** | Launch the interactive terminal dashboard |
| `mythic-vibe checkin` | Workflow | ENHANCED | Phase check-in with automated handoff generation |
| `mythic-vibe status` | Workflow | ENHANCED | Rich project state display with graph-backed context |
| `mythic-vibe forge` | Agents | **NEW** | Run a full multi-agent cycle for a given task |
| `mythic-vibe architect` | Agents | **NEW** | Invoke the Architect agent for system design |
| `mythic-vibe plan` | Agents | **NEW** | Invoke the Planner agent for task breakdown |
| `mythic-vibe build` | Agents | **NEW** | Invoke the Builder agent for code generation |
| `mythic-vibe verify` | Agents | **NEW** | Invoke the Verifier agent for adversarial review |
| `mythic-vibe codex-pack` | AI Bridge | ENHANCED | Generate prompt packet and route to configured provider |
| `mythic-vibe codex-log` | AI Bridge | ENHANCED | Log AI response with diff review interface |
| `mythic-vibe provider list` | AI | **NEW** | List configured AI providers and their health status |
| `mythic-vibe provider set` | AI | **NEW** | Configure the active AI provider |
| `mythic-vibe voice` | AI | **NEW** | Dictate intent or check-in notes via microphone |
| `mythic-vibe doctor` | Diagnostics | ENHANCED | Run diagnostics with drift detection and graph analysis |
| `mythic-vibe scry` | Diagnostics | EXISTING | Alias for `doctor` |
| `mythic-vibe scan` | Context | **NEW** | Scan repository and update knowledge graph |
| `mythic-vibe graph query` | Context | **NEW** | Query the knowledge graph directly |
| `mythic-vibe graph visualize` | Context | **NEW** | Render a visual map of the knowledge graph |
| `mythic-vibe simulate` | Resilience | **NEW** | Run resilience simulation against failure scenarios |
| `mythic-vibe plugin list` | Plugins | **NEW** | List installed plugins and their status |
| `mythic-vibe plugin install` | Plugins | **NEW** | Install a plugin from PyPI or a local path |
| `mythic-vibe plugin disable` | Plugins | **NEW** | Disable a plugin without uninstalling it |
| `mythic-vibe sync` | Method | EXISTING | Sync Mythic Engineering corpus from GitHub |
| `mythic-vibe method` | Method | EXISTING | Display Mythic Engineering method reference |
| `mythic-vibe weave` | Artifacts | EXISTING | Link artifacts across domains |
| `mythic-vibe prune` | Artifacts | EXISTING | Remove stale artifacts |
| `mythic-vibe heal` | Artifacts | EXISTING | Repair broken state |
| `mythic-vibe oath` | Constraints | EXISTING | Commit to a documented constraint |
| `mythic-vibe grimoire add` | Rituals | EXISTING | Add a ritual reference |
| `mythic-vibe grimoire list` | Rituals | EXISTING | List ritual references |
| `mythic-vibe config` | Config | EXISTING | Display active configuration |
| `mythic-vibe config set` | Config | EXISTING | Set a configuration value |
| `mythic-vibe db migrate` | Persistence | ENHANCED | Run schema migrations including v1→v2 state upgrade |
| `mythic-vibe plunder` | Import | EXISTING | Import from external repositories |
| `mythic-vibe reflect` | Workflow | **NEW** | Generate a structured reflection artifact for the current phase |
| `mythic-vibe handoff` | Workflow | **NEW** | Generate a session handoff document |
| `mythic-vibe rehydrate` | Context | **NEW** | Rehydrate session context from the last handoff and knowledge graph |

---

## Target Package Architecture

The following diagram illustrates the target layered architecture for the expanded CLI, showing the relationships between the major subsystems:

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI Layer (Typer)                        │
│  init  ui  forge  checkin  status  doctor  codex  plugin  ...   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                      Workflow Engine                             │
│         phases  transitions  checkins  handoff  reflection       │
└──────┬──────────────────────────────────────────────────────────┘
       │
┌──────▼──────────┐  ┌──────────────────┐  ┌────────────────────┐
│   Core Domain   │  │   AI / Agents    │  │  Context / Memory  │
│  project state  │  │  providers       │  │  scanner           │
│  artifacts      │  │  bridge          │  │  knowledge graph   │
│  method         │  │  router          │  │  retriever         │
│  events         │  │  agents          │  │  rehydrator        │
└──────┬──────────┘  └──────┬───────────┘  └────────┬───────────┘
       │                    │                        │
┌──────▼────────────────────▼────────────────────────▼───────────┐
│                       Persistence Layer                         │
│           SQLite (status, graph, sessions, logs)                │
│           Filesystem (artifacts, templates, packets)            │
└─────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│                    Plugin Sandbox Layer                          │
│      RitualPlugin  ProviderPlugin  ScannerPlugin  GatePlugin    │
└─────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────────────────────────┐
│               Optional Island Integrations (feature-flagged)    │
│    Yggdrasil Router  |  MindSpark ThoughtForge  |  WYRD Oracle  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quality Gates and Success Metrics

Every phase of this roadmap must pass a defined set of quality gates before the next phase begins. The following table summarizes the key metrics for each phase:

| Phase | Key Success Metrics |
| :--- | :--- |
| **1 — Core Hardening** | 0 boundary violations in CI; > 90% command test pass rate; `status.json` at schema v2.0.0 |
| **2 — Architecture Refactor** | All existing commands pass golden-path tests against new structure; no regression in command latency |
| **3 — TUI** | TUI launches without error; all four panels render correctly; diff review accepts/rejects individual hunks |
| **4 — Provider Layer** | Ollama adapter routes prompts to local models; cloud adapter routes to OpenAI/Anthropic; hardware-aware routing selects correct model |
| **5 — Multi-Agent** | `forge` command completes a full cycle without human intervention beyond approval gates; Verifier agent catches at least one architectural violation in integration tests |
| **6 — Knowledge Graph** | Graph populated on `checkin`; retriever selects more relevant context than fixed-file approach (measured by token efficiency); drift detection flags at least one real drift in integration tests |
| **7 — Island Integration** | Each island integration passes its feature-flag toggle test; no regression in core CLI when island is disabled |
| **8 — Plugin Ecosystem** | Plugin loader discovers and loads a reference plugin; plugin failure is isolated and does not crash CLI |
| **9 — Advanced AI** | Policy engine blocks at least one constraint violation in integration tests; resilience simulation completes without crashing |
| **10 — Release** | PyPI package installable via `pip install mythic-vibe`; documentation site live; changelog up to date |

---

## Conclusion

The `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding` repository is built on a profound and correct insight: that the discipline of software engineering — not merely the speed of code generation — is what makes AI-assisted development sustainable. The Mythic Engineering methodology, with its explicit loop of intent, constraints, architecture, planning, building, verification, and reflection, is not a bureaucratic overhead. It is the difference between a codebase that accumulates wisdom and one that accumulates debt.

This roadmap charts a 24-month path from the current early skeleton to a fully realized, multi-agent, knowledge-graph-backed, TUI-equipped operating system for disciplined AI-assisted software creation. Each phase builds on the last, and each is governed by the ten design laws that define what this tool is and what it refuses to become.

The forge is lit. The hall is wide enough. The work is worthy.

---

Now move on to the plan in (MYTHIC_VIBE_CLI_EXPANSION_ROADMAP_V2.md).

---

## References

[1] Real Python. "Python Textual: Build Beautiful UIs in the Terminal." https://realpython.com/python-textual/

[2] Ajit Kumar. "The Complete Guide to Ollama: Run Large Language Models Locally." DEV Community, Feb 16, 2026. https://dev.to/ajitkumar/the-complete-guide-to-ollama-run-large-language-models-locally-2mge

[3] AWS Open Source Blog. "Introducing CLI Agent Orchestrator: Transforming Developer CLI Tools into a Multi-Agent Powerhouse." Oct 21, 2025. https://aws.amazon.com/blogs/opensource/introducing-cli-agent-orchestrator-transforming-developer-cli-tools-into-a-multi-agent-powerhouse/

[4] Augment Code. "claude-mem hits 65.8K stars as a persistent memory plugin for AI coding assistants." 2026. https://www.augmentcode.com/learn/claude-mem-65k-stars

[5] Harness Engineering Blog. "Your Repo Is a Knowledge Graph. You Just Don't Query It Yet." Apr 1, 2026. https://www.harness.io/blog/your-repo-is-a-knowledge-graph-you-just-dont-query-it-yet

[6] Majid Basharat. "Designing Plugin-Based Architectures in Python." LinkedIn, 2025. https://www.linkedin.com/pulse/designing-plugin-based-architectures-python-majid-basharat-ilcqf

[7] hrabanazviking. `ARCHITECTURE.md` — Layered Decomposition. Viking-Code-Mythic-Engineering-CLI-Vibe-Coding, branch `development`, 2026-04-23. https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/blob/development/ARCHITECTURE.md

[8] hrabanazviking. `ROBUSTNESS_ADVANCEMENT_ROADMAP.md` — Toward the Most Advanced and Durable Form. Viking-Code-Mythic-Engineering-CLI-Vibe-Coding, branch `development`, 2026-04-23. https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/blob/development/ROBUSTNESS_ADVANCEMENT_ROADMAP.md

[9] hrabanazviking. `MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md` — Best-in-Class Production Roadmap. Viking-Code-Mythic-Engineering-CLI-Vibe-Coding, branch `development`, 2026-04-24. https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/blob/development/MYTHIC_VIBE_CLI_PRODUCTION_ROADMAP.md

[10] Memgraph. "GraphRAG for Devs: Graph-Code Demo Overview." Aug 28, 2025. https://memgraph.com/blog/graphrag-for-devs-coding-assistant
