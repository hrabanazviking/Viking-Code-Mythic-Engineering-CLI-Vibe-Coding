# Domain Map

**Last updated:** 2026-04-23  
**Owner:** Architecture + Documentation maintainers  
**Scope:** Entire repository

This domain map defines ownership, routing, and boundary rules so contributors can place work correctly in a large monorepo.

---

## 1) Why this exists

Without explicit routing, large repositories accumulate accidental edits in dormant or vendor areas. The result is hidden coupling, fragile releases, and confusing ownership.

This file prevents that by documenting:

- where active product behavior belongs,
- what each domain owns,
- what each domain must not own,
- which dependencies are disallowed.

---

## 2) Domain inventory

| Domain | Primary paths | Status | Owns | Must not own |
|---|---|---|---|---|
| Product CLI | `mythic_vibe_cli/`, `tests/`, packaging files | **Active** | Command contracts, workflow lifecycle, config, prompt packets, method sync | Vendor mirrors, dormant islands, unrelated research runtimes |
| Governance Docs | `docs/`, root architecture/governance docs | **Active** | Architecture records, onboarding, standards, release notes | Runtime implementation logic |
| Skills & Agent Modes | `skills/`, `.claude/`, `.roo/` | **Active** | Reusable execution/persona workflows | Product runtime behavior |
| Legacy Runtime Cluster | `ai/`, `core/`, `systems/`, `sessions/`, `yggdrasil/`, `imports/norsesaga/` | Dormant/fragmented | Historical experiments and archived runtime ideas | New product-critical behavior without architecture decision |
| Thoughtform Island | `mindspark_thoughtform/` | Dormant/self-contained | Experimental cognition systems | Direct CLI runtime dependencies |
| WYRD Protocol Island | `WYRD-Protocol-.../` | Dormant/self-contained | World-model/protocol experiments | Direct CLI runtime dependencies |
| Vendor Mirrors | `ollama/`, `whisper/`, `chatterbox/` | Snapshot/reference | Upstream source mirrors | Direct active CLI imports |
| Research Corpus | `research_data/`, `docs/research/`, `docs/specs/` | Informational | Theory/spec references | Authoritative runtime behavior |

---

## 3) Hard dependency law

### Product CLI (`mythic_vibe_cli/*`)

Allowed:

- Python stdlib + declared package dependencies.
- Internal imports within `mythic_vibe_cli/`.
- Artifact IO for project scaffolding/state.
- Explicit network calls only in sync/import paths.

Forbidden:

- Imports from dormant runtime clusters.
- Imports from Thoughtform/WYRD islands.
- Imports from vendor mirrors (`ollama`, `whisper`, `chatterbox`).

### Documentation and skills domains

Allowed:

- Stable repository-relative references.

Forbidden:

- Secrets or machine-specific absolute paths.
- Operational instructions that contradict active architecture.

---

## 4) Active CLI ownership map

| Subdomain | Canonical owner |
|---|---|
| Command surface and aliases | `mythic_vibe_cli/__main__.py`, `mythic_vibe_cli/cli.py`, `mythic_vibe_cli/app.py`, `mythic_vibe_cli/exit_codes.py` |
| Workflow lifecycle and phase transitions | `mythic_vibe_cli/workflow.py` |
| Configuration precedence and coercion | `mythic_vibe_cli/config.py` |
| Prompt packet synthesis and budget logic | `mythic_vibe_cli/codex_bridge.py` |
| Method sync/import/cache | `mythic_vibe_cli/mythic_data.py` |

---

## 5) Routing rules for new work

- New CLI command/alias -> `mythic_vibe_cli/app.py` with compatibility preserved through `mythic_vibe_cli/cli.py`
- New CLI entrypoint or exit-code policy -> `mythic_vibe_cli/__main__.py`, `mythic_vibe_cli/exit_codes.py`, and `docs/COMMAND_CONTRACTS.md`
- New phase/state logic -> `mythic_vibe_cli/workflow.py`
- New config option or precedence behavior -> `mythic_vibe_cli/config.py`
- New prompt packet section/format -> `mythic_vibe_cli/codex_bridge.py`
- New sync provider/parser/cache path -> `mythic_vibe_cli/mythic_data.py`
- New governance document -> `docs/` + linked root records
- New repeatable agent workflow -> `skills/<skill-name>/`

---

## 6) Boundary compliance checklist

A change is compliant only if all are true:

1. It remains in the proper owning domain.
2. It introduces no forbidden imports.
3. Governance docs are updated when behavior/ownership changes.
4. Tests/checks relevant to affected domains were executed.
5. Release/session continuity records were updated for meaningful deltas.

---

## 7) Escalation path for boundary exceptions

If a change truly needs cross-domain wiring:

1. Document intent and reason in architecture docs.
2. Define explicit adapter boundaries.
3. Add tests proving boundary contract behavior.
4. Record rationale in `DEVLOG.md` and summarize in `CHANGELOG.md`.

No silent exceptions.

---

## 8) Drift indicators

Investigate immediately if you see:

- Active CLI imports from dormant islands.
- New docs describing behavior not present in runtime.
- Contributors editing vendor mirrors for product fixes.
- Duplicate logic appearing in both active and dormant paths.

---

## 9) Related docs

- `docs/ARCHITECTURE.md`
- `docs/api.md`
- `docs/INDEX.md`
- root `ARCHITECTURE.md`
- root `DEVLOG.md`
