# MYTHIC VIBE CLI EXPANSION ROADMAP V2
## The 6-Agent Multi-Island Integration Protocol

> **Status:** Version 2.0 (Production-Ready)
> **Methodology:** Mythic Engineering (Strictly Additive / No Stubs / Full Code Only)
> **Scope:** Expansion of `hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`
> **Author:** Manus (Guided by the 6-Agent Protocol)

---

## 1. Executive Intent: The Sovereign System
This roadmap defines the 24-month trajectory to transform the `mythic_vibe_cli` from a 6-file skeleton into a **multi-agent, knowledge-graph-backed, TUI-equipped operating system** for disciplined AI-assisted software engineering. 

Following the **Mythic Engineering Protocol**, this plan is **strictly additive**. We do not subtract existing logic; we wrap, adapt, and expand it. We do not use stubs or fake code; every integration must be a full, working pathway.

---

## 2. The 6-Agent Orchestration Architecture
The core of this expansion is the transition from a single-assistant model to the full **6-Agent Mythic Protocol**. These roles are not mere prompts; they are the functional pillars of the CLI's multi-agent workflow engine.

| Agent | Identity | Focus | CLI Domain |
| :--- | :--- | :--- | :--- |
| **Skald** | Sigrún Ljósbrá | Vision, Naming, Philosophy | `docs/`, `SYSTEM_VISION.md` |
| **Architect** | Rúnhild Svartdóttir | Boundaries, Ownership, Law | `core/`, `DOMAIN_MAP.md` |
| **Forge Worker** | (The Maker) | Implementation, Refinement | `workflow/`, `build/` |
| **Auditor** | Sólrún Hvítmynd | Scrutiny, Truth, Verification | `verify/`, `tests/` |
| **Cartographer** | Védis Eikleið | Orientation, Mapping, Routes | `context/`, `MAP.md` |
| **Scribe** | Eirwyn Rúnblóm | Preservation, Memory, Records | `persistence/`, `DEVLOG.md` |

---

## 3. Island Integration Strategy (Additive Only)
The repository currently contains five disconnected "islands." This roadmap provides the **Seam-Bridging Protocol** to integrate them into the active CLI without breaking existing functionality.

### Island A: Mythic Vibe CLI (The Root)
*   **Status:** [LIVE]
*   **Additive Path:** Expand the current 6-file structure into the **Target Package Architecture** (see Section 4).

### Island B: Norse Saga Engine (NSE)
*   **Status:** [DORMANT]
*   **Integration Seam (S-1):** Resolve the `yggdrasil_core` ghost import by mapping it to the existing `yggdrasil/core/` package.
*   **Full Code Path:** Implement the `yggdrasil.router` as a provider adapter in `ai/providers/local.py`.

### Island C: MindSpark ThoughtForge
*   **Status:** [DORMANT]
*   **Integration Seam (S-2):** Install the MindSpark package in the CLI environment.
*   **Full Code Path:** Bridge `MindSpark.cognition` to the `workflow/engine.py` to provide advanced thought-form generation during the `plan` phase.

### Island D: WYRD Protocol
*   **Status:** [DORMANT]
*   **Integration Seam (S-3):** Create an in-process binding for the `WYRD passive_oracle`.
*   **Full Code Path:** Use WYRD as a real-time data provider for the `context/scanner.py`, allowing the CLI to ingest live world-model data.

### Island E: Upstream Vendors (Ollama/Whisper/Chatterbox)
*   **Status:** [DORMANT]
*   **Integration Seam (S-4/S-5):** Implement Python client adapters in `ai/providers/`.
*   **Full Code Path:** Enable `ollama` as the default local LLM provider for all 6 agents, ensuring 100% local-first sovereignty.

---

## 4. Target Package Architecture
We will migrate the current flat structure to this domain-shaped architecture. This is an **additive migration**: existing files are moved and expanded, never deleted.

```text
mythic_vibe_cli/
├── cli/            # UI, Commands, Output, Errors
├── core/           # Phases, Method Law, Project Model, State
├── workflow/       # 6-Agent Engine, Transitions, Rituals
├── docs/           # Templates, Drift Detection, Governance
├── context/        # Scanner, Indexer, Packet Builder (Cartographer)
├── ai/             # 6-Agent Roles, Providers (Ollama/OpenAI)
├── verify/         # Invariant Checker, Test Runner (Auditor)
├── persistence/    # JSON/SQLite Store, Migrations (Scribe)
├── plugins/        # Registry, Loader, API Hooks
└── plunder/        # GitHub Import, License Tracking
```

---

## 5. The 10-Phase Expansion Roadmap

### Phase 1: Architectural Unification (Months 1-2)
*   **Goal:** Hardening the foundation and resolving "ghost" imports.
*   **Deliverables:**
    *   Implement `mythic_vibe_cli/core/state.py` to replace `status.json`.
    *   Resolve `yggdrasil_core` import errors in Island B.
    *   Establish the `verify/` domain with the first **Auditor** invariant checks.

### Phase 2: The 6-Agent Engine (Months 3-4)
*   **Goal:** Moving from generic prompts to role-based orchestration.
*   **Deliverables:**
    *   Implement `ai/prompts/roles.py` containing the full system prompts for all 6 agents.
    *   Create the `workflow/engine.py` to manage agent handoffs (e.g., **Skald** names the feature -> **Architect** defines boundaries -> **Forge Worker** builds).

### Phase 3: TUI & UX Revolution (Months 5-6)
*   **Goal:** Providing a professional terminal interface.
*   **Deliverables:**
    *   Integrate `Textual` for a rich TUI.
    *   Implement real-time progress bars for long-running agent tasks.

### Phase 4: Local-First Sovereignty (Months 7-8)
*   **Goal:** Full integration of Island E (Ollama).
*   **Deliverables:**
    *   `ai/providers/local.py` adapter for Ollama.
    *   `whisper/` integration for voice-to-intent "Vibe" commands.

### Phase 5: Knowledge Graph & Context (Months 9-10)
*   **Goal:** Implementing the **Cartographer's** vision.
*   **Deliverables:**
    *   `context/indexer.py` to build a local map of all code/doc relationships.
    *   Integration of Island D (WYRD) for live context injection.

### Phase 6: MindSpark Integration (Months 11-12)
*   **Goal:** Advanced cognition via Island C.
*   **Deliverables:**
    *   Full bridge between `workflow/engine.py` and `MindSpark_ThoughtForge`.
    *   "Deep Think" mode for complex architectural refactors.

### Phase 7: Plugin & Ritual Ecosystem (Months 13-15)
*   **Goal:** Extensibility.
*   **Deliverables:**
    *   `plugins/registry.py` for community-contributed agent roles and rituals.
    *   `ritual.py` command to execute custom Mythic Engineering ceremonies.

### Phase 8: Plunder & Provenance (Months 16-18)
*   **Goal:** Safe external code ingestion.
*   **Deliverables:**
    *   `plunder/github.py` for disciplined importing of external libraries.
    *   Automated license and provenance tracking in `docs/`.

### Phase 9: Drift Detection & Self-Healing (Months 19-20)
*   **Goal:** Maintaining the "Living System."
*   **Deliverables:**
    *   `verify/doc_checker.py` to alert when code and `.md` docs diverge.
    *   `heal` command to automatically align implementation with documented intent.

### Phase 10: Distribution & Community (Months 21-24)
*   **Goal:** Releasing the Sovereign OS.
*   **Deliverables:**
    *   PyPI and Homebrew distribution.
    *   Comprehensive `grimoire` of community-tested Mythic Engineering patterns.

---

## 6. Quality Gates (The Auditor's Law)
Every release must pass these strictly additive gates:
1.  **Architecture Gate:** No boundary violations between the 10 domains.
2.  **Continuity Gate:** Every command must append to the `DEVLOG.md`.
3.  **Reality Gate:** 100% pass rate on the `verify/` suite.
4.  **Sovereignty Gate:** All core functions must work 100% offline via Ollama.

---

## 7. Conclusion: The Living Road
This roadmap is not a static document; it is a **Living Road**. As the system grows, the **Scribe** will record our progress, the **Cartographer** will update our maps, and the **Skald** will ensure our vision remains luminous. 

**We do not build software; we shape living systems.**
