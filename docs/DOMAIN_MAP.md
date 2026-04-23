# DOMAIN_MAP

**Last updated:** 2026-04-23  
**Owner:** Architecture / Docs  
**Scope:** Mythic Vibe CLI repository

---

## 1) Purpose

This map defines where capabilities belong, which domains are active vs archival, and which dependencies are forbidden. Use it as the routing law before adding new code.

---

## 2) Domain inventory

| Domain | Primary paths | Status | Owns | Must not own |
|---|---|---|---|---|
| Product CLI | `mythic_vibe_cli/`, `tests/`, `pyproject.toml` | **Active** | CLI commands, workflow loop, config resolution, codex packet generation, method sync | Research corpus, vendor forks, experimental runtimes |
| Governance Docs | `docs/`, `ARCHITECTURE.md`, `DOMAIN_MAP.md`, `DATA_FLOW.md`, `DEPENDENCIES.md`, `INVENTORY.md` | **Active** | Architecture records, operational rules, contributor orientation | Runtime implementation code |
| Skills & Agent Modes | `skills/`, `.claude/`, `.roo/` | **Active** | Reusable agent workflows, persona definitions, structured execution patterns | Product runtime logic |
| Legacy Runtime Cluster | `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, `imports/norsesaga/` | Dormant / fragmented | Historical and experimental runtime components | New product-critical features without ADR |
| Thoughtform Island | `mindspark_thoughtform/` | Dormant / self-contained | Cognitive pipeline experiments | CLI production dependencies |
| WYRD Protocol Island | `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | Dormant / self-contained | Protocol/world-model research and SDKs | CLI production dependencies |
| Vendor Mirrors | `ollama/`, `whisper/`, `chatterbox/` | Vendor snapshots | Upstream reference code | Direct import targets for product CLI |
| Research Corpus | `research_data/`, `docs/research/`, `docs/specs/` | Informational | Theory, studies, exploratory design artifacts | Authoritative runtime behavior |

---

## 3) Hard dependency law

### Product CLI (`mythic_vibe_cli/*`)

Allowed:
- Python stdlib + declared package dependencies.
- Internal imports within `mythic_vibe_cli/`.
- File-system interaction with scaffold targets (`docs/`, `tasks/`, `mythic/`).
- Explicit network access isolated to sync/import flows.

Forbidden:
- Imports from `ai/`, `core/`, `systems/`, `yggdrasil/`, `imports/norsesaga/`.
- Imports from `mindspark_thoughtform/` or `WYRD-Protocol-.../`.
- Imports from vendor mirrors (`ollama/`, `whisper/`, `chatterbox/`).

### Docs/skills domains

Allowed:
- Referencing stable repository paths and contract files.

Forbidden:
- Embedding secrets, local absolute machine paths, or hidden production assumptions.

---

## 4) Active product ownership map

| Subdomain | File owner |
|---|---|
| Command surface and argument contracts | `mythic_vibe_cli/cli.py` |
| Workflow lifecycle, scaffold generation, and status transitions | `mythic_vibe_cli/workflow.py` |
| Config layering, coercion, and env/file precedence | `mythic_vibe_cli/config.py` |
| Codex/ChatGPT packet synthesis and compaction | `mythic_vibe_cli/codex_bridge.py` |
| Mythic method syncing/import behavior | `mythic_vibe_cli/mythic_data.py` |

---

## 5) Routing rules for new work

- New CLI commands or aliases → `mythic_vibe_cli/cli.py`
- New phase/state behavior → `mythic_vibe_cli/workflow.py`
- New config knobs or precedence rules → `mythic_vibe_cli/config.py`
- New packet sections/format logic → `mythic_vibe_cli/codex_bridge.py`
- New method sync providers/parsers → `mythic_vibe_cli/mythic_data.py`
- New architecture governance text → `docs/` + root architecture pack
- New persona/workflow skill → `skills/<skill-name>/`

---

## 6) Boundary-compliant change checklist

A change is compliant only if all are true:

1. It stays inside domain-owned paths.
2. It introduces no forbidden cross-domain import.
3. It updates this map (and related architecture docs) when ownership shifts.
4. It includes verification commands for touched domains.

If any condition fails, treat the change as architectural drift and correct it before merge.
