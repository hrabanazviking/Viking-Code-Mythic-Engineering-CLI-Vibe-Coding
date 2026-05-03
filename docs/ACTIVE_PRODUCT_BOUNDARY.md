# Active Product Boundary

**Last updated:** 2026-05-03 (v1.0.0)

The active product is **Mythic Vibe CLI**: a method-first command-line tool that turns creative intent into architecture-aware, verified, recoverable software work.

## Active Product Paths

| Path | Status | Responsibility |
|---|---|---|
| `mythic_vibe_cli/` | Active runtime | Installable CLI package, command dispatch, workflow state, config, packets, method sync, plugins, AI providers, runtime primitives, six-role forge, governance commands |
| `tests/` | Active verification | Unit, integration, property (`tests/property/`), snapshot (`tests/snapshots/`), and provider-conformance tests |
| `tools/` | Active tooling | Out-of-package developer tools (`contract_audit.py` docs↔code drift detector) |
| `scripts/` | Active operator scripts | `regenerate_sbom.py`, `check_changelog.py` (with `--classify`) |
| `packaging/` | Active distribution templates | Homebrew formula + Scoop manifest templates + wheelhouse operator guide |
| `pyproject.toml` | Active packaging | Package metadata, entrypoints, build configuration, optional-extras matrix |
| `docs/` | Active governance | Architecture records, boundary rules, onboarding, API and workflow docs, security docs (`docs/security/`), governance cadence (`docs/governance/`) |
| `.github/workflows/` | Active CI/CD | `ci.yml` (3 OS × 3 Python + Linux aarch64) + `release.yml` (tag-driven distribution) |
| root governance docs | Active continuity | `README.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `DEVLOG.md`, `DATA_FLOW.md`, `CONTRIBUTING.md`, `RELEASE_v1_0_0_2026-05-03.md`, `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES.md` |

## Product Runtime Contract

The active CLI must remain independently executable without importing dormant runtime islands, research corpora, or vendor mirrors. It may read and write project artifacts such as `docs/`, `tasks/`, and `mythic/` in user projects, but its implementation dependencies stay inside `mythic_vibe_cli/` unless an ADR grants a specific adapter exception.

**v1.0.0 binding additions:**

- The compatibility-policy contract in [`docs/compatibility_policy.md`](compatibility_policy.md) is binding from this release. Public-surface stability tiers (§3 of that doc) govern what may change without a major version bump.
- Runtime base has **zero non-stdlib dependencies** — every external package is opt-in via `pyproject.toml [project.optional-dependencies]`. AI provider adapters, the Textual TUI, OpenTelemetry, and the three island adapters all sit behind try-import + `MissingExtraError` with operator-friendly install hints.
- Cross-process write paths use `runtime/cross_process_lock.py` + `runtime/atomic_write.py` (PH-19). Hand-rolled `.write_text()` on shared files is no longer recommended for new code.

## Current Runtime Modules

| Module | Owns |
|---|---|
| `mythic_vibe_cli/__main__.py` | Package-module execution for `python -m mythic_vibe_cli` |
| `mythic_vibe_cli/cli.py` | Public compatibility entrypoint for `mythic_vibe_cli.cli:main` |
| `mythic_vibe_cli/app.py` | Argument parsing and top-level command dispatch |
| `mythic_vibe_cli/commands.py` | Command implementations, command registry, and compatibility aliases |
| `mythic_vibe_cli/output.py` | Shared terminal output helpers |
| `mythic_vibe_cli/errors.py` | Structured CLI error payloads and formatting |
| `mythic_vibe_cli/exit_codes.py` | Shared CLI return-code policy (`SUCCESS=0`, `OPERATIONAL_FAILURE=1`, `USER_INPUT_ERROR=2`, `VERIFICATION_FAILURE=3`, `UNSAFE_OPERATION_BLOCKED=4`) |
| `mythic_vibe_cli/core/state.py` | Schema-versioned project state, records, phase constants, validation |
| `mythic_vibe_cli/persistence/` | `JsonStateStore` + `FileLock` (with v1.0 opt-in `cross_process=True`); `migrate_project_state` (PH-19.4 hypothesis-tested) |
| `mythic_vibe_cli/resources/schemas/` | Packaged JSON schemas (state, checkin, decision, verification, plugin manifest with v1.0 `capabilities` enum) |
| `mythic_vibe_cli/runtime/` | **Ten** primitives — file mutation queue, output guard, event bus, timings, slash-commands catalog, source-info, exec, event log, plus v1.0 cross-process lock + atomic write |
| `mythic_vibe_cli/workflow.py` | Mythic phases, scaffolding, status, check-ins, diagnostics |
| `mythic_vibe_cli/workflow_engine.py` | Six-role workflow orchestration planner |
| `mythic_vibe_cli/workflow_agents.py` | Agent contract spec (PH-03 slice 3.1) — frozen `AgentInput`/`AgentOutput`/`AgentContract` dataclasses |
| `mythic_vibe_cli/forge.py`, `forge_ledger.py`, `forge_verifier.py`, `forge_reflection.py` | Six-role forge — plan/run/resume + ledger + verifier gates + reflection capture (PH-03) |
| `mythic_vibe_cli/workflow_lineage.py` | v1.0 / PH-20.C — Mermaid + JSON workflow graph viewer |
| `mythic_vibe_cli/codex_bridge.py` | AI prompt packet rendering, context compaction, v1.0 `ROLE_BUDGET_MULTIPLIERS` per-role budget logic |
| `mythic_vibe_cli/packet_lint.py` | v1.0 / PH-20.1 — 7-rule heuristic packet linter |
| `mythic_vibe_cli/config.py` | Layered config resolution and env overrides |
| `mythic_vibe_cli/mythic_data.py` | Method source sync, markdown import, local cache |
| `mythic_vibe_cli/init_wizard.py` | v1.0 / PH-20.0 — opt-in `init --interactive` Q&A wizard |
| `mythic_vibe_cli/doctor_fix.py` | v1.0 / PH-20.2 — tightly-scoped auto-remediation (mythic/ subdirs + CHANGELOG `[Unreleased]`); hard-rule: never touches user-authored content |
| `mythic_vibe_cli/personas.py` | v1.0 / PH-20.A — opt-in operator presets (`solo`/`team-lead`/`auditor`) |
| `mythic_vibe_cli/architecture_review.py` | v1.0 / PH-20.H — quarterly review checklist generator |
| `mythic_vibe_cli/tui_panels.py` | v1.0 / PH-20.I — opt-in TUI heatmap + plugin risk panel data builders |
| `mythic_vibe_cli/drift.py` | PH-13 drift detection + v1.0 dashboard rollup |
| `mythic_vibe_cli/handoff.py` | Session-bridge handoff record creation + listing |
| `mythic_vibe_cli/hardware.py` | Hardware profile detection (Pi tiers documented in `docs/hardware_profiles.md`) |
| `mythic_vibe_cli/plugins/` | Plugin layer — `api`, `registry`, `loader`, `sandbox`, `dispatcher`, `extension_points`, `entry_points` plus v1.0 additions `capabilities.py` + `circuit_breaker.py` |
| `mythic_vibe_cli/verify/` | Verification gates — `test_runner`, `git_diff`, `doc_checker`, `invariant_checker` |
| `mythic_vibe_cli/ai/` | AI provider adapters (9 providers), routing, telemetry, model catalog, v1.0 `recommend.py` policy DSL |
| `mythic_vibe_cli/plunder/` | Lawful single-file reuse — `github`, `license`, `provenance` plus v1.0 additions `verify.py` (SHA-256) + `attestation.py` (per-line) |
| `mythic_vibe_cli/security/` | `approval`, `dangerous_patterns`, `exec_policy`, `privacy`, `redaction`, `secret_scanner` |
| `mythic_vibe_cli/surfaces/` | Alternate access — `chat_bridge`, `chat_bridge_loop`, `web_terminal`, `ssh_doctor`, `narrow_layout` |
| `mythic_vibe_cli/voice/` | Local-first speech — `transcribe`, `tts` |
| `mythic_vibe_cli/protocols/` | PH-16 MCP / ACP / OpenTelemetry surfaces (gated) |
| `mythic_vibe_cli/policy/` | PH-14 policy engine |
| `mythic_vibe_cli/cicd/` | PH-12 CI/CD wrappers |
| `mythic_vibe_cli/context/` | Project scanning + indexing + knowledge graph autopopulation |
| `mythic_vibe_cli/memory/` | PH-05 knowledge graph (SQLite) |
| `mythic_vibe_cli/robustness/` | PH-18 robustness sweeps |
| `mythic_vibe_cli/tui/` | Textual TUI surfaces (gated by `[tui]` extra) |

## Change Rule

If a change modifies active runtime behavior, update at least one of these records when relevant:

- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MAP.md`
- `docs/DATA_FLOW.md`
- `docs/api.md`
- `docs/COMMAND_CONTRACTS.md`
- `docs/compatibility_policy.md` (when public-surface tiers change)
- `docs/security/threat_model.md` (when a new attack surface is added)
- `CHANGELOG.md`
- `DEVLOG.md`

Use these before merging boundary-sensitive work:

```bash
mythic-vibe doctor --repo-boundary --path .
python tools/contract_audit.py --strict
pytest -q
ruff check mythic_vibe_cli tests scripts tools
mypy mythic_vibe_cli
```
