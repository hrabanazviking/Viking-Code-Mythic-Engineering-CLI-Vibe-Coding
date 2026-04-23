# Domain Map

**Last updated:** 2026-04-23  
**Owner:** Architecture / Docs  
**Scope:** Entire repository

This map is the routing law for where code and docs belong.

---

## 1) Why this exists

In a multi-project monorepo, contributors can unintentionally modify dormant or vendor areas while trying to ship active product behavior. This document prevents that drift by defining ownership and forbidden dependencies.

---

## 2) Domain inventory

| Domain | Primary paths | Status | Owns | Must not own |
|---|---|---|---|---|
| Product CLI | `mythic_vibe_cli/`, `tests/`, packaging files | **Active** | Command contracts, workflow lifecycle, config, prompt packet generation, method sync | Vendor mirrors, research corpus, dormant runtime islands |
| Governance Docs | `docs/`, root architecture/governance docs | **Active** | Architecture records, operating rules, contributor orientation | Runtime implementation logic |
| Skills & Agent Modes | `skills/`, `.claude/`, `.roo/` | **Active** | Reusable workflows/personas and execution guidance | Product runtime code |
| Legacy Runtime Cluster | `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, `imports/norsesaga/` | Dormant/fragmented | Historical experiments and partial runtime systems | New product-critical features without explicit architecture decision |
| Thoughtform Island | `mindspark_thoughtform/` | Dormant/self-contained | Research implementation experiments | CLI production dependencies |
| WYRD Protocol Island | `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | Dormant/self-contained | Protocol/world-model exploration | CLI production dependencies |
| Vendor Mirrors | `ollama/`, `whisper/`, `chatterbox/` | Snapshot/reference | Upstream code mirrors | Direct import targets in active CLI |
| Research Corpus | `research_data/`, `docs/research/`, `docs/specs/` | Informational | Theory/spec references | Authoritative runtime behavior |

---

## 3) Hard dependency law

### Product CLI (`mythic_vibe_cli/*`)

Allowed:
- Python stdlib and declared package dependencies.
- Internal imports within `mythic_vibe_cli/`.
- File IO for project scaffolds and operational artifacts.
- Explicit network access in sync/import paths.

Forbidden:
- Imports from dormant runtime clusters.
- Imports from Thoughtform/WYRD islands.
- Imports from vendor mirrors.

### Docs and skills domains

Allowed:
- References to stable repository-relative paths.

Forbidden:
- Secrets, machine-specific absolute paths, undocumented production assumptions.

---

## 4) Ownership map for active CLI

| Subdomain | Canonical owner |
|---|---|
| Command surface and args | `mythic_vibe_cli/cli.py` |
| Workflow lifecycle and phase transitions | `mythic_vibe_cli/workflow.py` |
| Config precedence and coercion | `mythic_vibe_cli/config.py` |
| Prompt packet synthesis and compaction | `mythic_vibe_cli/codex_bridge.py` |
| Method sync/import/caching | `mythic_vibe_cli/mythic_data.py` |

---

## 5) Routing rules for new work

- New command or alias -> `mythic_vibe_cli/cli.py`
- New workflow phase/state behavior -> `mythic_vibe_cli/workflow.py`
- New configuration setting -> `mythic_vibe_cli/config.py`
- New packet section/formatting -> `mythic_vibe_cli/codex_bridge.py`
- New sync provider/parser -> `mythic_vibe_cli/mythic_data.py`
- New governance documentation -> `docs/` + corresponding root records
- New agent workflow/skill -> `skills/<skill-name>/`

---

## 6) Boundary compliance checklist

A change is compliant only if all are true:

1. It stays inside the proper owning domain.
2. It introduces no forbidden cross-domain import.
3. It updates governance docs when ownership/boundaries shift.
4. It includes verification commands relevant to changed domains.

If any check fails, treat the change as architectural drift and fix before merge.
