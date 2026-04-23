# DOMAIN_MAP.md — Canonical Ownership & Boundaries

**Last updated:** 2026-04-23  
**Primary owner:** Architect (Rúnhild Svartdóttir)  
**Repository:** `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`

---

## 1. Purpose

This document defines **hard domain ownership boundaries** for the repository so contributors can answer three questions with zero ambiguity:

1. **Where does a capability belong?**
2. **What is allowed to depend on what?**
3. **Which code is product-critical vs archival/vendor context?**

---

## 2. Domain index (bounded contexts)

| Domain | Paths | Status | Owner | Responsibility |
|---|---|---|---|---|
| Product CLI Core | `mythic_vibe_cli/`, `tests/`, `pyproject.toml` | **Active** | CLI Team | User-facing command surface, workflow orchestration, config, packet generation, method sync. |
| Project Docs Authority | `ARCHITECTURE.md`, `MAP.md`, `DEPENDENCIES.md`, `DATA_FLOW.md`, this file | **Active** | Architecture/Docs | Canonical maps, structural constraints, change planning artifacts. |
| Skill Runtime Pack | `skills/` | **Active** | Agent Ops | Reusable agent skills and associated references. |
| Agent Configuration (Cross-tool) | `.claude/agents/`, `.roo/`, `.roomodes` | **Active** | Agent Ops | Cross-repo callable persona/mode definitions. |
| NSE Runtime Legacy Island | `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, `imports/norsesaga/` | Dormant / partial | Runtime R&D | Experimental runtime components; currently fragmented and import-incomplete. |
| WYRD Protocol Island | `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | Dormant / self-contained | Protocol R&D | ECS/world model + bridges + SDK and protocol experiments. |
| MindSpark Thoughtform Island | `mindspark_thoughtform/` | Dormant / self-contained | Thoughtform R&D | Cognitive pipeline, inference connectors, internal app/test tooling. |
| Vendor Mirrors | `ollama/`, `whisper/`, `chatterbox/` | Dormant / vendor | Vendor Sync | Upstream snapshots/reference code, not direct product dependencies. |
| Research Corpus | `research_data/`, `docs/research/`, root research markdown/json artifacts | Active (informational) | Research | Theory inputs and analysis references. |

---

## 3. Domain law (allowed dependencies)

### 3.1 Product CLI law (strict)

`mythic_vibe_cli/*` MAY depend on:
- Python stdlib
- Internal files in `mythic_vibe_cli/`
- Local project docs and scaffold targets (`docs/`, `tasks/`, `mythic/`)
- Network APIs explicitly used by `mythic_data.py`

`mythic_vibe_cli/*` MUST NOT depend on:
- `ai/`, `core/`, `systems/`, `yggdrasil/`
- `WYRD-Protocol-.../` implementation modules
- `mindspark_thoughtform/` implementation modules
- Vendor mirrors under `ollama/`, `whisper/`, `chatterbox/`

### 3.2 Skill/Agent law

`skills/*`, `.claude/agents/*`, `.roo/*` MAY reference architecture docs and stable repo paths.

They MUST NOT encode:
- Absolute machine-specific paths
- Secrets/tokens
- Runtime assumptions that couple to one AI vendor only

### 3.3 Dormant island law

Dormant islands are **quarantined for product stability**.

- They are allowed to evolve internally.
- They are not allowed to become implicit product dependencies without an ADR and a boundary contract.

---

## 4. Ownership contracts by active product subdomain

### 4.1 CLI Interface Domain
- **Files:** `mythic_vibe_cli/cli.py`
- **Owns:** commands, parser definitions, command dispatch, terminal UX text.
- **Does not own:** persistence schema logic, deep workflow rules, external API details.

### 4.2 Workflow Orchestration Domain
- **Files:** `mythic_vibe_cli/workflow.py`
- **Owns:** lifecycle phases, scaffold templates, status transitions, check-in records.
- **Contract:** surface stable interfaces used by CLI commands.

### 4.3 Config Resolution Domain
- **Files:** `mythic_vibe_cli/config.py`
- **Owns:** layered config merge, env override semantics, coercion and bounds.
- **Contract:** return typed config object; hide source path precedence internals.

### 4.4 Codex Packet Domain
- **Files:** `mythic_vibe_cli/codex_bridge.py`
- **Owns:** prompt packet rendering, compaction policy, context selection logic.
- **Contract:** deterministic packet output based on request + local state.

### 4.5 Method Sync Domain
- **Files:** `mythic_vibe_cli/mythic_data.py`
- **Owns:** remote markdown sync, cache persistence, fallback behavior.
- **Contract:** isolate network calls; no CLI presentation logic inside this domain.

---

## 5. Structural drift currently observed

1. **Multi-product super-repo drift:** repo contains multiple mature/dormant projects with no manifest-level ownership registry.
2. **Root-level documentation gravity:** architecture docs describe many islands, but no canonical boundary law previously prevented accidental cross-import.
3. **Legacy runtime fragmentation:** root runtime references absent modules (e.g., `yggdrasil_core` references noted in existing architecture docs), indicating extraction drift.
4. **Product surface ambiguity:** high documentation volume can obscure that `mythic_vibe_cli` is the active package shipped via `pyproject.toml`.

---

## 6. Required enforcement mechanisms

1. Add a `DOMAIN_POLICY.md` linter-oriented file (future) containing machine-checkable rules.
2. Add CI checks:
   - import boundary guard for `mythic_vibe_cli`
   - markdown freshness check for key architecture docs
3. Add ADR requirement for any dependency from active product into dormant islands.
4. Add ownership table to PR template (future) requiring “domain touched” + “boundary risk.”

---

## 7. Fast routing rules (where new code goes)

- New CLI command parsing logic → `mythic_vibe_cli/cli.py`
- New phase/state behavior → `mythic_vibe_cli/workflow.py`
- New config knob/schema behavior → `mythic_vibe_cli/config.py`
- New codex packet sections/format rules → `mythic_vibe_cli/codex_bridge.py`
- New upstream sync providers/parsers → `mythic_vibe_cli/mythic_data.py`
- New architectural governance docs → root `*.md` architecture pack
- New reusable agent persona/workflow → `skills/<skill-name>/` (+ optional `.claude/agents/` and `.roo/` entries)

---

## 8. Definition of boundary-compliant change

A change is boundary-compliant when:

1. It modifies only owner-approved domains.
2. It introduces no forbidden cross-domain dependency.
3. It updates architecture docs when boundaries or ownership changes.
4. It includes verification commands aligned to touched domains.

When these four are true, the architecture remains load-bearing under growth.
