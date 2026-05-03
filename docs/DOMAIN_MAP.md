# Domain Map

**Last updated:** 2026-05-03 (v1.0.0)
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
| Product CLI | `mythic_vibe_cli/`, `tests/`, packaging files | **Active** | Command contracts, workflow lifecycle, project state, config, prompt packets, method sync | Vendor mirrors, dormant islands, unrelated research runtimes |
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
| Command surface and aliases | `mythic_vibe_cli/__main__.py`, `mythic_vibe_cli/cli.py`, `mythic_vibe_cli/app.py`, `mythic_vibe_cli/commands.py`, `mythic_vibe_cli/exit_codes.py` |
| Terminal output and CLI error formatting | `mythic_vibe_cli/output.py`, `mythic_vibe_cli/errors.py` |
| Project state contract and validation | `mythic_vibe_cli/core/state.py`, `mythic_vibe_cli/resources/schemas/` |
| JSON persistence, backups, and migrations | `mythic_vibe_cli/persistence/json_store.py`, `mythic_vibe_cli/persistence/migrations.py` |
| Workflow lifecycle and phase transitions | `mythic_vibe_cli/workflow.py` |
| Role orchestration planning | `mythic_vibe_cli/workflow_engine.py`, `mythic_vibe_cli/ai/prompts/roles.py` |
| Configuration precedence and coercion | `mythic_vibe_cli/config.py` |
| Prompt packet synthesis and budget logic | `mythic_vibe_cli/codex_bridge.py` (v1.0: `ROLE_BUDGET_MULTIPLIERS` per-role compaction) |
| Method sync/import/cache | `mythic_vibe_cli/mythic_data.py` |
| **Runtime primitives** (v1.0: 10 modules) | `mythic_vibe_cli/runtime/{file_mutation_queue, output_guard, event_bus, timings, slash_commands, source_info, exec, event_log, cross_process_lock, atomic_write}.py` |
| **Six-role forge** (PH-03) | `mythic_vibe_cli/{workflow_agents, forge_ledger, forge, forge_verifier, forge_reflection}.py` |
| **Plugin layer** (incl. v1.0 capabilities + breaker) | `mythic_vibe_cli/plugins/{api, registry, loader, sandbox, capabilities, circuit_breaker, dispatcher, extension_points, entry_points}.py` |
| **Verification gates** | `mythic_vibe_cli/verify/{__init__, test_runner, git_diff, doc_checker, invariant_checker}.py` |
| **AI provider adapters** | `mythic_vibe_cli/ai/providers/{base, copy_paste, local, openai, anthropic, gemini, openrouter, ollama, yggdrasil, mindspark}.py`; catalog at `mythic_vibe_cli/ai/providers/model_catalog.py`; recommendation DSL at `mythic_vibe_cli/ai/recommend.py` (v1.0); routing at `mythic_vibe_cli/ai/{router, routing_runtime, registry, cost_guard, ollama_health}.py` |
| **Plunder + provenance** | `mythic_vibe_cli/plunder/{github, license, provenance, verify, attestation}.py` |
| **Init wizard** (v1.0 / PH-20.0) | `mythic_vibe_cli/init_wizard.py` |
| **Packet lint** (v1.0 / PH-20.1) | `mythic_vibe_cli/packet_lint.py` |
| **Doctor auto-fix** (v1.0 / PH-20.2) | `mythic_vibe_cli/doctor_fix.py` |
| **Persona presets** (v1.0 / PH-20.A) | `mythic_vibe_cli/personas.py` |
| **Architecture review** (v1.0 / PH-20.H) | `mythic_vibe_cli/architecture_review.py` |
| **Workflow lineage viewer** (v1.0 / PH-20.C) | `mythic_vibe_cli/workflow_lineage.py` |
| **TUI panel data builders** (v1.0 / PH-20.I) | `mythic_vibe_cli/tui_panels.py` |
| **Drift detection** (PH-13 + v1.0 dashboard) | `mythic_vibe_cli/drift.py` |
| **Hardware profiles** | `mythic_vibe_cli/hardware.py` |
| **Voice surfaces** | `mythic_vibe_cli/voice/{transcribe, tts}.py` |
| **Alternate access surfaces** | `mythic_vibe_cli/surfaces/{chat_bridge, chat_bridge_loop, web_terminal, ssh_doctor, narrow_layout}.py` |
| **Security policy** | `mythic_vibe_cli/security/{approval, dangerous_patterns, exec_policy, privacy, redaction, secret_scanner}.py` |
| **Knowledge graph + scanning** | `mythic_vibe_cli/context/{scanner, indexer, file_filters, autopopulate, packet_context}.py`; `mythic_vibe_cli/memory/` |
| **Robustness layer** | `mythic_vibe_cli/robustness/` |
| **Protocol surfaces** | `mythic_vibe_cli/protocols/` (PH-16 MCP / ACP / OTel) |
| **Policy engine** | `mythic_vibe_cli/policy/` (PH-14) |
| **CI/CD wrappers** | `mythic_vibe_cli/cicd/` (PH-12) |
| **Out-of-package tooling** | `tools/contract_audit.py` (docs↔code drift); `scripts/regenerate_sbom.py`, `scripts/check_changelog.py` (`--classify` PH-20.F) |

---

## 5) Routing rules for new work

- New CLI command/alias -> parser wiring in `mythic_vibe_cli/app.py`, implementation and registry wiring in `mythic_vibe_cli/commands.py`, with compatibility preserved through `mythic_vibe_cli/cli.py`. **Also update:** `BUILTIN_SLASH_COMMANDS` in `mythic_vibe_cli/runtime/slash_commands.py`, `tests/test_cli_kernel.py:test_command_registry_preserves_current_commands_and_aliases`, and the contract-audit baseline in BOTH `tests/test_contract_audit.py` AND `tools/contract_audit.py:main`.
- New CLI entrypoint or exit-code policy -> `mythic_vibe_cli/__main__.py`, `mythic_vibe_cli/exit_codes.py`, and `docs/COMMAND_CONTRACTS.md`
- New terminal rendering or command error format -> `mythic_vibe_cli/output.py`, `mythic_vibe_cli/errors.py`, and command tests where behavior is user-visible
- New phase lifecycle logic -> `mythic_vibe_cli/workflow.py`
- New role orchestration logic -> `mythic_vibe_cli/workflow_engine.py` plus role definitions in `mythic_vibe_cli/ai/prompts/roles.py`
- New project state fields/schema/validation -> `mythic_vibe_cli/core/state.py`, `mythic_vibe_cli/resources/schemas/`, and migration tests
- New state read/write/migration behavior -> `mythic_vibe_cli/persistence/` — and **add a property test** under `tests/property/` per the PH-19.4 invariant pattern
- New config option or precedence behavior -> `mythic_vibe_cli/config.py`
- New prompt packet section/format -> `mythic_vibe_cli/codex_bridge.py` (consider per-role budget impact in `ROLE_BUDGET_MULTIPLIERS`)
- New sync provider/parser/cache path -> `mythic_vibe_cli/mythic_data.py`
- New runtime primitive -> `mythic_vibe_cli/runtime/`, with a focused test under `tests/test_<name>.py`, re-export from `mythic_vibe_cli/runtime/__init__.py`, AND a section in `docs/runtime.md`
- New plugin extension point or capability -> `mythic_vibe_cli/plugins/` plus updates to BOTH `KNOWN_CAPABILITIES` in `capabilities.py` AND the JSON schema enum in `mythic_vibe_cli/resources/schemas/plugin_manifest.schema.json` (capability vocabulary is coordinated)
- New AI provider -> `mythic_vibe_cli/ai/providers/<name>.py`, register in `mythic_vibe_cli/ai/registry.py`, add static catalog rows in `mythic_vibe_cli/ai/providers/model_catalog.py`, and the conformance suite (`tests/test_provider_contract_conformance.py`) auto-extends coverage
- New top-level surface (provenance, persona, review, etc.) -> follow the v1.0 pattern: top-level dispatcher in `commands.py`, parser in `app.py`, entry in `BUILTIN_SLASH_COMMANDS`, `COMMAND_HANDLERS` registration, contract-audit baseline updates in BOTH locations, doc page or section in `docs/api.md` + `docs/COMMAND_CONTRACTS.md`
- New governance document -> `docs/` + linked root records; if it concerns architecture cadence, also reference from `docs/governance/quarterly_review.md`
- New release workflow / packaging template -> `.github/workflows/`, `packaging/`, and `docs/RELEASE_CHECKLIST.md`
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
