---
title: "Mythic Vibe CLI — Best-in-Class Production Roadmap"
repo: "hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding"
method_source: "hrabanazviking/Mythic-Engineering"
created: "2026-04-24"
status: "planning"
format: "Markdown data file"
purpose: "Turn Mythic Vibe CLI into a real, working, best-in-class vibe coding CLI using Mythic Engineering as the operating method."
---

# Mythic Vibe CLI — Best-in-Class Production Roadmap

## 0. Executive Intent

**Mythic Vibe CLI should become the command-line operating system for disciplined AI-assisted software creation.**

Its job is not merely to generate prompts, scaffold documents, or wrap AI tools. Its deeper job is to make **Mythic Engineering executable**:

```text
intent -> constraints -> architecture -> plan -> build -> verify -> reflect
```

The CLI should guide a user from vague creative impulse into:

- explicit system intent,
- documented constraints,
- architecture-aware planning,
- safe build packets,
- AI-ready context packs,
- verification gates,
- recoverable session memory,
- durable handoffs,
- and long-term project continuity.

The product should feel like a **calm engineering companion**: structured enough to prevent drift, flexible enough to preserve creative momentum, and serious enough for long-lived codebases.

---

# 1. Source-Reality Assessment

## 1.1 Current repository posture

The current repo is not a clean single-purpose runtime repository. It is a **large mythic engineering monorepo** containing:

- active CLI product code,
- active docs,
- tests,
- historical/runtime fragments,
- research islands,
- vendor/reference mirrors,
- plundering guides,
- architectural notes,
- and mythology-heavy system design material.

The existing repo docs already define the critical rule:

```text
Active runtime path:
- mythic_vibe_cli/

Active support paths:
- tests/
- docs/
- selected root governance records

Reference / dormant / vendor islands:
- ai/
- core/
- systems/
- sessions/
- yggdrasil/
- WYRD-Protocol-...
- mindspark_thoughtform/
- whisper/
- chatterbox/
- ollama/
```

## 1.2 Active runtime files inspected

Current active Python runtime is small and concentrated:

```text
mythic_vibe_cli/
  __init__.py
  cli.py
  codex_bridge.py
  config.py
  mythic_data.py
  workflow.py
```

Current test surface:

```text
tests/
  __init__.py
  test_cli.py
  test_config_and_bridge.py
  test_workflow.py
```

Current docs surface includes:

```text
docs/
  ARCHITECTURE.md
  DATA_FLOW.md
  DOCUMENTATION_STANDARDS.md
  DOMAIN_MAP.md
  INDEX.md
  PHILOSOPHY.md
  SESSION_HANDOFF_TEMPLATE.md
  SYSTEM_VISION.md
  api.md
  hardware_profiles.md
  quickstart.md
  research/
  specs/
```

## 1.3 Current implemented capabilities

The CLI already has the seed of a real product:

```text
init / start / imbue
checkin
status
import-md
codex-pack / evoke
codex-log
sync
method
doctor / scry
weave
prune
heal
oath
grimoire add|list
config
config set
db migrate
plunder
```

## 1.4 Current architectural strengths

The project already has several strong bones:

- It knows the core Mythic Engineering loop.
- It creates durable artifacts under `docs/`, `tasks/`, and `mythic/`.
- It has a prompt bridge for ChatGPT/Codex.
- It tracks status in `mythic/status.json`.
- It has a diagnostic command.
- It has config layering.
- It has a method sync/import path for pulling Mythic Engineering material.
- It has ritual aliases that give the tool a memorable identity.
- It has explicit docs that separate active runtime from dormant islands.

## 1.5 Current architectural weaknesses

The current product is still an early skeleton. To become best-in-class, it needs:

- a stronger internal domain model,
- a stable artifact schema,
- reliable migrations,
- better state handling,
- richer diagnostics,
- real project scanning,
- real command contracts,
- plugin loading that actually loads plugins,
- provider adapters instead of copy/paste-only bridge logic,
- safer GitHub import/plunder workflows,
- structured task packets,
- review/audit modes,
- strong verification gates,
- better test coverage,
- packaging/release hardening,
- and a stronger separation between core domain logic and CLI output.

---

# 2. Product North Star

## 2.1 One-sentence definition

**Mythic Vibe CLI is a method-first AI coding command line that turns creative intent into architecture-aware, verified, recoverable software work.**

## 2.2 Product promises

The finished CLI must deliver these promises:

| Promise | Meaning |
|---|---|
| Architecture before patching | The tool should ask where behavior belongs before helping change code. |
| Continuity before speed | Every major action leaves durable traces. |
| AI as force multiplier | AI assists, but the user remains sovereign and responsible. |
| Reality over theory | Tests, diffs, runtime behavior, and files are ground truth. |
| Recoverable memory | A future session can understand what happened and why. |
| Beginner-safe, expert-capable | Simple path for new users; deep controls for serious builders. |
| Method fidelity | Mythic Engineering is not decoration; it is the workflow engine. |
| Local-first | User data stays on disk unless explicit external integration is invoked. |
| Pluggable | Providers, rituals, templates, and scanners can be extended. |
| Auditable | Decisions, prompts, changes, and verification results can be reviewed. |

---

# 3. Core Design Laws

These laws should govern every implementation decision.

## Law 1 — The method is executable

The CLI must not merely describe Mythic Engineering. It must enforce, guide, record, and verify the method.

## Law 2 — No hidden memory

Anything important must be written to disk in a predictable place.

## Law 3 — Project state is a first-class object

`status.json` should evolve into a real project state model with schema versioning, migrations, phase history, open tasks, risks, decisions, and verification records.

## Law 4 — AI output is never automatically trusted

The CLI may generate prompts, call providers, or ingest responses, but it must separate:

```text
proposal -> user review -> applied change -> verification -> reflection
```

## Law 5 — Documents are not decoration

Docs are part of the runtime method. Drift between docs and code is a diagnostic failure.

## Law 6 — Every subsystem has an owner

If a feature cannot be assigned to a domain, it is not ready to be implemented.

## Law 7 — The CLI should be useful without cloud AI

The offline/local path should still scaffold, scan, plan, diagnose, and preserve continuity.

## Law 8 — The user owns the work

The CLI should not lock the user into one AI vendor, one editor, one platform, or one worldview of software work.

---

# 4. Target Architecture

## 4.1 Proposed package structure

Replace the current flat runtime package with a domain-shaped architecture:

```text
mythic_vibe_cli/
  __init__.py
  __main__.py

  cli/
    __init__.py
    app.py
    commands/
      init.py
      status.py
      checkin.py
      doctor.py
      plan.py
      codex.py
      ai.py
      scan.py
      verify.py
      reflect.py
      config.py
      db.py
      plugin.py
      plunder.py
      ritual.py
    output.py
    errors.py

  core/
    __init__.py
    phases.py
    method.py
    project.py
    state.py
    artifacts.py
    events.py
    errors.py

  workflow/
    __init__.py
    engine.py
    transitions.py
    checkins.py
    handoff.py
    reflection.py
    rituals.py

  docs/
    __init__.py
    templates.py
    renderer.py
    drift.py
    governance.py

  context/
    __init__.py
    scanner.py
    indexer.py
    summarizer.py
    packet_builder.py
    budgets.py
    file_filters.py

  ai/
    __init__.py
    providers/
      base.py
      openai.py
      anthropic.py
      gemini.py
      openrouter.py
      local.py
      copy_paste.py
    prompts/
      roles.py
      packets.py
      schemas.py
    response_ingest.py

  verify/
    __init__.py
    commands.py
    test_runner.py
    git_diff.py
    invariant_checker.py
    doc_checker.py
    security.py

  persistence/
    __init__.py
    json_store.py
    sqlite_store.py
    migrations.py
    locks.py
    backups.py

  plugins/
    __init__.py
    registry.py
    loader.py
    api.py
    hooks.py

  plunder/
    __init__.py
    github.py
    license.py
    provenance.py
    import_plan.py

  resources/
    templates/
      project/
      docs/
      tasks/
      mythic/
    schemas/
      project_state.schema.json
      checkin.schema.json
      packet.schema.json
      decision.schema.json
      verification.schema.json
```

## 4.2 Domain ownership map

| Domain | Owns | Must not own |
|---|---|---|
| `cli/` | Argument parsing, command dispatch, terminal output | Method logic, persistence rules, provider-specific internals |
| `core/` | Method concepts, phases, project model, state types | Filesystem side effects, network calls |
| `workflow/` | Phase transitions, check-ins, handoffs, ritual workflows | Raw CLI parsing, provider HTTP calls |
| `docs/` | Templates, docs drift checks, governance | AI provider calls, project scanning internals |
| `context/` | Project scanning, indexing, packet construction | Applying code changes |
| `ai/` | Provider adapters, prompt rendering, response ingest | Project state ownership |
| `verify/` | Tests, diffs, invariant checks, diagnostics | Planning decisions |
| `persistence/` | JSON/SQLite stores, migrations, locks, backups | User-facing command semantics |
| `plugins/` | Plugin discovery, hooks, isolation | Core method law |
| `plunder/` | GitHub import, license/provenance tracking | Silent code mutation |

---

# 5. Canonical Artifact System

## 5.1 Project artifact tree

A mature initialized project should contain:

```text
.
├── MYTHIC_ENGINEERING.md
├── SYSTEM_VISION.md
├── .mythic-vibe.json
├── docs/
│   ├── INDEX.md
│   ├── PHILOSOPHY.md
│   ├── ARCHITECTURE.md
│   ├── DOMAIN_MAP.md
│   ├── DATA_FLOW.md
│   ├── DECISIONS/
│   │   └── ADR-0001-initial-architecture.md
│   ├── INTERFACES/
│   │   └── README.md
│   ├── INVARIANTS.md
│   ├── VERIFICATION.md
│   ├── RISK_REGISTER.md
│   ├── SESSION_HANDOFF.md
│   └── DEVLOG.md
├── tasks/
│   ├── current_GOALS.md
│   ├── backlog.md
│   ├── active/
│   │   └── TASK-0001.md
│   └── completed/
├── mythic/
│   ├── status.json
│   ├── state.sqlite
│   ├── loop.md
│   ├── plan.md
│   ├── codex_prompt.md
│   ├── packets/
│   ├── responses/
│   ├── checkins/
│   ├── verification/
│   ├── reflections/
│   ├── imports/
│   └── plugins.json
```

## 5.2 State schema v1

```json
{
  "schema_version": 1,
  "project_id": "uuid",
  "goal": "string",
  "created_at": "iso_datetime",
  "updated_at": "iso_datetime",
  "current_phase": "intent",
  "completed_phases": [],
  "active_task_id": null,
  "open_risks": [],
  "open_decisions": [],
  "last_packet_id": null,
  "last_verification_id": null,
  "history": []
}
```

## 5.3 Check-in schema

```json
{
  "schema_version": 1,
  "checkin_id": "CHK-000001",
  "timestamp": "iso_datetime",
  "phase": "plan",
  "task_id": "TASK-0001",
  "summary": "string",
  "files_changed": [],
  "decisions": [],
  "risks": [],
  "next_phase": "build"
}
```

## 5.4 Decision schema

```json
{
  "schema_version": 1,
  "decision_id": "ADR-0001",
  "title": "string",
  "status": "proposed|accepted|superseded|rejected",
  "context": "string",
  "decision": "string",
  "consequences": [],
  "links": []
}
```

## 5.5 Verification schema

```json
{
  "schema_version": 1,
  "verification_id": "VER-000001",
  "timestamp": "iso_datetime",
  "task_id": "TASK-0001",
  "commands": [
    {
      "command": "pytest -q",
      "exit_code": 0,
      "summary": "passed"
    }
  ],
  "diff_reviewed": true,
  "docs_updated": true,
  "invariants_checked": [],
  "result": "pass|fail|blocked"
}
```

---

# 6. Multi-Stage Production Plan

## Stage 0 — Repo Boundary Stabilization

```yaml
stage_id: STAGE-00
name: Repo Boundary Stabilization
mythic_phase_bias: architecture
goal: Make the active product boundary undeniable.
priority: critical
```

### Intent

Stop the repo from feeling like everything is active. The CLI cannot become best-in-class while active runtime, dormant experiments, vendor mirrors, and research islands feel equally authoritative.

### Constraints

- Do not delete historical material yet.
- Do not import dormant runtime code into active product.
- Treat dormant folders as source material until formal adapters exist.
- Keep Apache-2.0 notices and provenance intact.

### Build tasks

- [ ] Create `docs/ACTIVE_PRODUCT_BOUNDARY.md`.
- [ ] Create `docs/DORMANT_ISLANDS.md`.
- [ ] Add root `REPO_BOUNDARY.md`.
- [ ] Add warning banners to dormant island READMEs if missing.
- [ ] Create `docs/ADRS/ADR-0001-active-runtime-boundary.md`.
- [ ] Create `docs/ADRS/ADR-0002-no-direct-vendor-imports.md`.
- [ ] Update `docs/INDEX.md`.
- [ ] Update root README with "Active Runtime Path" above the fold.
- [ ] Add `mythic-vibe doctor --repo-boundary` check.

### Verification

```bash
python -m mythic_vibe_cli.cli doctor --path .
pytest -q
```

### Done when

- A new contributor knows exactly where real CLI code lives.
- `mythic_vibe_cli/`, `tests/`, and `docs/` are visibly privileged.
- Dormant folders cannot accidentally become dependencies without ADR.

---

## Stage 1 — CLI Kernel Hardening

```yaml
stage_id: STAGE-01
name: CLI Kernel Hardening
mythic_phase_bias: build
goal: Make the current CLI reliable, typed, testable, and maintainable.
priority: critical
```

### Intent

Turn `cli.py` from a broad command file into a maintainable command surface.

### Constraints

- Keep existing commands working.
- Preserve ritual aliases.
- Avoid breaking current README examples.
- Add tests before large command refactors.

### Build tasks

- [x] Add `__main__.py` so `python -m mythic_vibe_cli` works.
- [x] Split command handlers out of `cli.py`.
- [x] Add `mythic_vibe_cli/output.py` with consistent terminal rendering.
- [x] Add `mythic_vibe_cli/errors.py` with structured error formatting.
- [x] Add command registry pattern.
- [x] Replace direct `print()` calls in command logic with output functions.
- [x] Add return-code policy:
  - `0` success,
  - `1` operational failure,
  - `2` user input/config error,
  - `3` verification failure,
  - `4` unsafe operation blocked.
- [x] Add `--json` output mode to machine-readable commands.
- [x] Add `--quiet` and `--verbose`.
- [x] Add `--dry-run` to commands that write files.
- [ ] Add shell completion later as Stage 13.

### Target command kernel

```text
mythic-vibe
  init
  status
  checkin
  doctor
  plan
  build
  verify
  reflect
  packet
  ai
  config
  db
  plugin
  plunder
```

### Compatibility aliases

```text
imbue  -> init
scry   -> doctor
evoke  -> packet create
weave  -> reflect sync
heal   -> verify repair
oath   -> policy oath
```

### Verification

```bash
python -m mythic_vibe_cli --help
python -m mythic_vibe_cli.cli --help
pytest -q
```

### Done when

- `cli.py` is a thin router.
- Commands are isolated and individually testable.
- JSON mode exists for automation.
- Existing examples still pass.

---

## Stage 2 — Mythic Project State Engine

```yaml
stage_id: STAGE-02
name: Mythic Project State Engine
mythic_phase_bias: architecture
goal: Replace loose status tracking with schema-versioned project state.
priority: critical
```

### Intent

`mythic/status.json` should become a durable state contract, not just a simple progress file.

### Constraints

- Must migrate existing simple `status.json`.
- Must not destroy user data.
- Must support JSON first, SQLite second.
- Must support offline use.

### Build tasks

- [ ] Create `core/state.py`.
- [ ] Create `persistence/json_store.py`.
- [ ] Create `persistence/migrations.py`.
- [ ] Define `ProjectState`.
- [ ] Define `CheckinRecord`.
- [ ] Define `DecisionRecord`.
- [ ] Define `VerificationRecord`.
- [ ] Add schema files under `resources/schemas/`.
- [ ] Add `mythic-vibe db migrate`.
- [ ] Add `mythic-vibe state show`.
- [ ] Add `mythic-vibe state validate`.
- [ ] Add automatic backup before migration:
  - `mythic/backups/status.json.YYYYMMDDHHMMSS.bak`
- [ ] Add file locks for concurrent writes.
- [ ] Add tests for corrupt JSON recovery.

### Data rules

```yaml
state_rules:
  - state changes must be append-recorded
  - migration must preserve old history
  - invalid phase names must fail validation
  - write operations must be atomic
  - backups must exist before destructive rewrite
```

### Verification

```bash
pytest tests/test_state.py -q
mythic-vibe state validate --path .
mythic-vibe db migrate --path .
```

### Done when

- Existing projects migrate safely.
- State is validated before and after command writes.
- Commands can report state as human text or JSON.

---

## Stage 3 — Mythic Artifact Template System

```yaml
stage_id: STAGE-03
name: Mythic Artifact Template System
mythic_phase_bias: plan
goal: Make project scaffolding rich, explicit, and extensible.
priority: high
```

### Intent

The current scaffold is useful but too thin for a best-in-class workflow. It should generate actionable artifacts that match Mythic Engineering.

### Constraints

- Beginner mode must stay readable.
- Advanced mode must be deep enough for real systems.
- Templates must be versioned.
- User edits must not be overwritten silently.

### Build tasks

- [ ] Move templates out of Python string literals.
- [ ] Create `resources/templates/project/`.
- [ ] Add template version headers.
- [ ] Add `mythic-vibe init --profile beginner|standard|advanced|solo|team|library|app|cli`.
- [ ] Add `mythic-vibe init --force` with backups.
- [ ] Add `mythic-vibe init --preview`.
- [ ] Add `mythic-vibe scaffold add docs|adr|task|interface|invariant|risk`.
- [ ] Add `docs/INTERFACES/`.
- [ ] Add `docs/INVARIANTS.md`.
- [ ] Add `docs/RISK_REGISTER.md`.
- [ ] Add `docs/VERIFICATION.md`.
- [ ] Add `tasks/backlog.md`.
- [ ] Add first ADR automatically.
- [ ] Add session handoff file automatically.

### Artifact profiles

| Profile | User type | Generated depth |
|---|---|---|
| beginner | new coder / vibe coder | simple forms, explanations, examples |
| standard | normal project | core docs + tasks + checks |
| advanced | complex codebase | ADRs, invariants, interfaces, risk register |
| solo | single builder | lightweight handoff, devlog focus |
| team | multi-person | ownership map, PR checklist, review gates |
| cli | CLI product | command contracts, help output tests |
| library | Python package | API contracts, semantic versioning notes |
| app | app project | data flow, user journeys, deployment docs |

### Verification

```bash
mythic-vibe init --goal "Test project" --profile advanced --preview
mythic-vibe init --goal "Test project" --profile advanced --path /tmp/mv-test
mythic-vibe doctor --path /tmp/mv-test
pytest -q
```

### Done when

- Templates live outside runtime logic.
- Scaffolds are rich enough to guide real development.
- User edits are protected.

---

## Stage 4 — Phase Workflow Engine

```yaml
stage_id: STAGE-04
name: Phase Workflow Engine
mythic_phase_bias: build
goal: Make the Mythic Engineering loop operational, not merely documented.
priority: critical
```

### Intent

The CLI should guide the user through each phase with commands, prompts, validation, and artifacts.

### Constraints

- Users can move flexibly, but the tool should warn about skipped reasoning.
- Must support noob-friendly explanations.
- Must support advanced direct mode.

### Build tasks

- [ ] Add `mythic-vibe phase current`.
- [ ] Add `mythic-vibe phase next`.
- [ ] Add `mythic-vibe phase set`.
- [ ] Add `mythic-vibe phase complete`.
- [ ] Add `mythic-vibe intent capture`.
- [ ] Add `mythic-vibe constraints capture`.
- [ ] Add `mythic-vibe architecture map`.
- [ ] Add `mythic-vibe plan create`.
- [ ] Add `mythic-vibe build packet`.
- [ ] Add `mythic-vibe verify run`.
- [ ] Add `mythic-vibe reflect`.
- [ ] Add phase-specific question sets.
- [ ] Add phase-specific required fields.
- [ ] Add warnings for missing prior phases.

### Phase data file pattern

```text
mythic/checkins/
  2026-04-24T18-00-00Z-intent.md
  2026-04-24T18-15-00Z-constraints.md
  2026-04-24T18-30-00Z-architecture.md
```

### Phase record template

```markdown
# Mythic Phase Record

- Phase:
- Task:
- Timestamp:
- Operator:
- Confidence:
- Risk:

## Intent

## Constraints

## Architecture Impact

## Action Taken

## Verification

## Reflection

## Next Step
```

### Done when

- The loop is navigable as a real CLI state machine.
- Each phase writes durable artifacts.
- `status` can explain where the user is and what to do next.

---

## Stage 5 — Context Scanner and Project Index

```yaml
stage_id: STAGE-05
name: Context Scanner and Project Index
mythic_phase_bias: architecture
goal: Let the CLI understand the local project enough to build useful packets.
priority: critical
```

### Intent

A best-in-class AI coding CLI must know what files exist, what changed, which docs matter, and which files should not be touched.

### Constraints

- Must respect `.gitignore`.
- Must support include/exclude patterns.
- Must avoid reading huge/vendor files by default.
- Must never upload anything without explicit user action.
- Must be fast on large repos.

### Build tasks

- [ ] Create `context/scanner.py`.
- [ ] Create `context/indexer.py`.
- [ ] Create `context/file_filters.py`.
- [ ] Add `mythic-vibe scan`.
- [ ] Add `mythic-vibe scan --json`.
- [ ] Add `mythic-vibe scan --changed`.
- [ ] Add `mythic-vibe scan --docs`.
- [ ] Add `.mythicignore`.
- [ ] Honor `.gitignore`.
- [ ] Detect language stats.
- [ ] Detect package files:
  - `pyproject.toml`
  - `package.json`
  - `Cargo.toml`
  - `go.mod`
  - etc.
- [ ] Detect test commands.
- [ ] Detect docs drift candidates.
- [ ] Detect large files and binary files.
- [ ] Detect vendor/reference islands.
- [ ] Create `mythic/project_index.json`.

### Project index schema

```json
{
  "schema_version": 1,
  "generated_at": "iso_datetime",
  "root": "path",
  "git": {
    "branch": "string",
    "dirty": true,
    "changed_files": []
  },
  "languages": {},
  "important_files": [],
  "docs": [],
  "tests": [],
  "ignored": [],
  "risks": [],
  "recommended_context": []
}
```

### Done when

- The CLI can create an accurate local project map.
- Prompt packets are grounded in actual files.
- Large/dormant/vendor areas are excluded by default unless requested.

---

## Stage 6 — Best-in-Class Prompt Packet Engine

```yaml
stage_id: STAGE-06
name: Best-in-Class Prompt Packet Engine
mythic_phase_bias: build
goal: Make AI packets precise, bounded, role-aware, and repeatable.
priority: critical
```

### Intent

The current `codex-pack` is the right seed. It should become a general packet engine for multiple AI workflows.

### Constraints

- Keep copy/paste mode.
- Do not require API keys.
- Preserve ChatGPT Plus/Codex bridge.
- Support model/provider-specific packet formats later.

### Build tasks

- [ ] Rename internal concept from `CodexBridge` to `PacketBuilder`.
- [ ] Keep `codex-pack` as compatibility command.
- [ ] Add `packet create`.
- [ ] Add `packet show`.
- [ ] Add `packet list`.
- [ ] Add `packet ingest`.
- [ ] Add `packet diff`.
- [ ] Add packet IDs.
- [ ] Add packet metadata.
- [ ] Add token/character budget strategy.
- [ ] Add role selection:
  - Architect
  - Forge Worker
  - Auditor
  - Cartographer
  - Scribe
  - Debugger
  - Refactorer
- [ ] Add output formats:
  - ChatGPT/Codex copy-paste
  - Claude Code task
  - Gemini CLI task
  - Aider prompt
  - Roo prompt
  - Goose prompt
  - generic Markdown
  - strict JSON
- [ ] Add packet safety sections:
  - Files allowed
  - Files forbidden
  - Invariants
  - Verification commands
  - Expected output format
  - Check-in summary format
- [ ] Add context source manifest.

### Packet data model

```json
{
  "packet_id": "PKT-000001",
  "created_at": "iso_datetime",
  "phase": "build",
  "role": "Forge Worker",
  "task": "string",
  "context_files": [],
  "forbidden_files": [],
  "invariants": [],
  "verification": [],
  "prompt": "string",
  "budget": {
    "limit": 12000,
    "used": 10422,
    "truncated": true
  }
}
```

### Golden prompt format

```markdown
# Mythic Engineering Task Packet

## 1. Role

## 2. Intent

## 3. Constraints

## 4. Architecture Context

## 5. Files In Scope

## 6. Files Out of Scope

## 7. Current State

## 8. Requested Change

## 9. Verification Commands

## 10. Required Output Format

## 11. Check-in Summary
```

### Done when

- Packets are reusable artifacts, not temporary text.
- The same input creates reproducible packet output.
- Packets can be pasted into multiple tools without losing method fidelity.

---

## Stage 7 — AI Provider Adapter Layer

```yaml
stage_id: STAGE-07
name: AI Provider Adapter Layer
mythic_phase_bias: architecture
goal: Add optional direct AI integrations without breaking local-first/copy-paste use.
priority: high
```

### Intent

The CLI should work in three modes:

```text
1. Offline/local artifact mode
2. Copy/paste bridge mode
3. Direct provider mode
```

### Constraints

- No provider required by default.
- API keys must be explicit.
- Sensitive files must not be sent accidentally.
- Provider adapters must be isolated.
- Every provider call must be logged as metadata, not hidden behavior.

### Build tasks

- [ ] Create `ai/providers/base.py`.
- [ ] Create `ai/providers/copy_paste.py`.
- [ ] Create `ai/providers/openai.py`.
- [ ] Create `ai/providers/anthropic.py`.
- [ ] Create `ai/providers/gemini.py`.
- [ ] Create `ai/providers/openrouter.py`.
- [ ] Create `ai/providers/local.py`.
- [ ] Add `mythic-vibe ai providers`.
- [ ] Add `mythic-vibe ai test`.
- [ ] Add `mythic-vibe ai run --packet PKT-0001`.
- [ ] Add `--dry-run` for provider calls.
- [ ] Add redaction engine.
- [ ] Add provider request/response logging.
- [ ] Add cost/token estimate field.
- [ ] Add `mythic-vibe ai ingest-response`.
- [ ] Add "never apply automatically" default.

### Provider interface

```python
class AIProvider:
    name: str

    def validate_config(self) -> ProviderStatus:
        ...

    def estimate(self, packet: Packet) -> Estimate:
        ...

    def run(self, packet: Packet) -> ProviderResponse:
        ...
```

### Security rules

```yaml
ai_safety_rules:
  - no network call unless command explicitly invokes provider mode
  - no hidden provider fallback
  - no automatic code application from model output
  - log provider, model, timestamp, packet id, and files included
  - redact configured secrets
  - warn if packet includes env files, keys, tokens, credentials, private notes
```

### Done when

- Copy/paste remains first-class.
- Direct AI mode is optional, explicit, logged, and safe.
- The provider system can grow without contaminating core workflow logic.

---

## Stage 8 — Verification and Reality Gates

```yaml
stage_id: STAGE-08
name: Verification and Reality Gates
mythic_phase_bias: verify
goal: Make reality checks central to the CLI.
priority: critical
```

### Intent

The CLI must enforce Mythic Engineering's principle that reality outranks theory.

### Constraints

- Verification commands differ by project.
- Tool must work even when no tests exist.
- It should recommend, not fake certainty.

### Build tasks

- [ ] Create `verify/test_runner.py`.
- [ ] Create `verify/git_diff.py`.
- [ ] Create `verify/invariant_checker.py`.
- [ ] Create `verify/doc_checker.py`.
- [ ] Add `mythic-vibe verify`.
- [ ] Add `mythic-vibe verify --commands`.
- [ ] Add `mythic-vibe verify --changed-files`.
- [ ] Add `mythic-vibe verify --docs`.
- [ ] Add `mythic-vibe verify --invariants`.
- [ ] Add `mythic-vibe verify --record`.
- [ ] Add verification result artifacts.
- [ ] Add verification gate in `reflect`.
- [ ] Add "blocked" state if verification fails.
- [ ] Add `heal` workflow for failing tests.

### Verification levels

| Level | Meaning |
|---|---|
| `none` | No checks configured. Tool warns. |
| `smoke` | CLI/help/import tests pass. |
| `unit` | Project unit tests pass. |
| `integration` | Cross-command workflows pass. |
| `release` | Full test/lint/type/package checks pass. |

### Done when

- The CLI never treats unverified changes as complete.
- Verification results become durable records.
- Failing tests trigger a structured healing workflow.

---

## Stage 9 — Doctor/Scry Deep Diagnostics

```yaml
stage_id: STAGE-09
name: Doctor/Scry Deep Diagnostics
mythic_phase_bias: verify
goal: Turn doctor into a serious project health scanner.
priority: high
```

### Intent

`doctor` should become one of the CLI's killer features.

### Build tasks

- [ ] Check required artifacts.
- [ ] Check state schema.
- [ ] Check phase coherence.
- [ ] Check stale docs.
- [ ] Check missing ADRs for major changes.
- [ ] Check docs/code drift.
- [ ] Check invalid config.
- [ ] Check packet budget issues.
- [ ] Check missing verification commands.
- [ ] Check dirty Git state.
- [ ] Check dormant island imports.
- [ ] Check vendor folder modifications.
- [ ] Check duplicate docs.
- [ ] Check missing session handoff.
- [ ] Add severity:
  - info
  - warning
  - error
  - blocked
- [ ] Add remediation hints.
- [ ] Add `--fix` only for safe fixes.
- [ ] Add `--json`.

### Diagnostic item schema

```json
{
  "severity": "warning",
  "code": "DOCS_DRIFT_001",
  "message": "docs/ARCHITECTURE.md is older than changed runtime files.",
  "evidence": [],
  "recommended_fix": "Run mythic-vibe reflect --docs"
}
```

### Done when

- `doctor` gives actionable engineering guidance.
- `scry` remains the mythic alias.
- Diagnostics are machine-readable.

---

## Stage 10 — Reflection, Handoff, and Continuity Memory

```yaml
stage_id: STAGE-10
name: Reflection, Handoff, and Continuity Memory
mythic_phase_bias: reflect
goal: Make session endings valuable and recoverable.
priority: high
```

### Intent

The CLI should end every work cycle with a high-quality future-self handoff.

### Build tasks

- [ ] Add `mythic-vibe reflect`.
- [ ] Add `mythic-vibe handoff create`.
- [ ] Add `mythic-vibe handoff show`.
- [ ] Add `mythic-vibe handoff latest`.
- [ ] Add `mythic-vibe resume`.
- [ ] Summarize:
  - intent,
  - constraints,
  - decisions,
  - files changed,
  - tests run,
  - failures,
  - next steps.
- [ ] Generate `docs/SESSION_HANDOFF.md`.
- [ ] Generate timestamped handoff files.
- [ ] Link handoff from `status`.

### Handoff template

```markdown
# Session Handoff

## Where the work stands

## What changed

## Decisions made

## Files touched

## Verification run

## Known risks

## Next recommended action

## Prompt packet suggestion
```

### Done when

- A future session can resume without rediscovering context.
- `resume` tells the user what to do next.
- Reflection is short enough to use but rich enough to matter.

---

## Stage 11 — Plunder System v2

```yaml
stage_id: STAGE-11
name: Lawful Plunder System v2
mythic_phase_bias: constraints
goal: Turn plundering into safe, licensed, provenance-tracked reuse.
priority: medium
```

### Intent

The repo already includes several plundering guides and a `plunder` command. This should become a safe code-reuse workflow, not a raw file copy helper.

### Constraints

- Respect licenses.
- One file per import can remain as safe default.
- Track source, commit, license, and modification notes.
- Never overwrite silently.

### Build tasks

- [ ] Create `plunder/github.py`.
- [ ] Create `plunder/license.py`.
- [ ] Create `plunder/provenance.py`.
- [ ] Add `plunder inspect`.
- [ ] Add `plunder plan`.
- [ ] Add `plunder fetch`.
- [ ] Add `plunder apply`.
- [ ] Add `plunder record`.
- [ ] Add source manifest:
  - source repo,
  - source file,
  - source ref/SHA,
  - license,
  - destination,
  - modifications.
- [ ] Add Apache/MIT/BSD compatibility notes.
- [ ] Add "do not plunder" warning for incompatible/unknown licenses.
- [ ] Add NOTICE update helper.
- [ ] Add tests with mocked GitHub responses.

### Provenance file

```text
mythic/imports/plunder_manifest.json
```

### Done when

- Reuse is documented and lawful.
- Plundered files are traceable.
- License posture is clearer.

---

## Stage 12 — Plugin/Grimoire System

```yaml
stage_id: STAGE-12
name: Plugin/Grimoire System
mythic_phase_bias: architecture
goal: Make extensions real without destabilizing the core.
priority: medium
```

### Intent

`grimoire add|list` currently stores plugin strings. It should become a real plugin system with hooks.

### Constraints

- Plugins must not silently override core behavior.
- Plugin failures must not corrupt project state.
- Hooks must be documented and versioned.

### Build tasks

- [ ] Create `plugins/api.py`.
- [ ] Create `plugins/registry.py`.
- [ ] Create `plugins/loader.py`.
- [ ] Add plugin manifest schema.
- [ ] Add plugin health checks.
- [ ] Add hooks:
  - `before_scan`
  - `after_scan`
  - `before_packet`
  - `after_packet`
  - `before_verify`
  - `after_verify`
  - `before_reflect`
  - `after_reflect`
- [ ] Add `mythic-vibe plugin list`.
- [ ] Add `mythic-vibe plugin inspect`.
- [ ] Add `mythic-vibe plugin disable`.
- [ ] Add sandbox warning.

### Done when

- Plugins are discoverable.
- Plugin behavior is visible.
- Core method law remains protected.

---

## Stage 13 — Packaging, Release, and Install Quality

```yaml
stage_id: STAGE-13
name: Packaging, Release, and Install Quality
mythic_phase_bias: verify
goal: Make the CLI easy to install, test, and release.
priority: high
```

### Build tasks

- [ ] Ensure `pyproject.toml` is complete.
- [ ] Define console scripts:
  - `mythic-vibe`
  - `mythic`
- [ ] Add package metadata.
- [ ] Add Python version classifiers.
- [ ] Add optional dependency groups:
  - `dev`
  - `ai`
  - `docs`
  - `test`
- [ ] Add GitHub Actions:
  - tests,
  - lint,
  - package build,
  - release check.
- [ ] Add `ruff`.
- [ ] Add `mypy` or `pyright` optional type check.
- [ ] Add `pytest-cov`.
- [ ] Add release checklist.
- [ ] Add changelog automation.
- [ ] Add install docs for:
  - Windows PowerShell,
  - Linux,
  - macOS,
  - venv,
  - uv,
  - pipx.

### Done when

- Fresh users can install and run quickly.
- CI proves core commands.
- Release artifacts are reproducible.

---

## Stage 14 — UX Polish and Command Ergonomics

```yaml
stage_id: STAGE-14
name: UX Polish and Command Ergonomics
mythic_phase_bias: reflect
goal: Make the CLI feel calm, powerful, and clear.
priority: medium
```

### Build tasks

- [ ] Add rich terminal output if dependency allowed.
- [ ] Add plain output fallback.
- [ ] Add command examples in every help section.
- [ ] Add `mythic-vibe examples`.
- [ ] Add `mythic-vibe guide`.
- [ ] Add `mythic-vibe next`.
- [ ] Add `mythic-vibe explain phase`.
- [ ] Add `mythic-vibe explain artifact`.
- [ ] Add `mythic-vibe tutorial`.
- [ ] Add shell completions.
- [ ] Add Windows-friendly docs.
- [ ] Add "noob mode" expanded guidance.

### UX law

Every command should answer:

```text
What happened?
Where was it written?
What should I do next?
How do I verify it?
```

---

## Stage 15 — Mythic Engineering Method Integration

```yaml
stage_id: STAGE-15
name: Mythic Engineering Method Integration
mythic_phase_bias: architecture
goal: Make the CLI track the canonical Mythic Engineering method deeply.
priority: high
```

### Intent

The method source should not be a loose README sync. The CLI should treat Mythic Engineering as a versioned method corpus.

### Build tasks

- [ ] Import markdown corpus with manifest.
- [ ] Add method version detection.
- [ ] Add method source config.
- [ ] Add `method sync`.
- [ ] Add `method status`.
- [ ] Add `method diff`.
- [ ] Add `method pin`.
- [ ] Add local cache.
- [ ] Add fallback method profile.
- [ ] Add method excerpt selector for packet building.
- [ ] Add method sections:
  - principles,
  - workflow,
  - AI roles,
  - required docs,
  - refactor method,
  - debugging method,
  - verification method,
  - failure modes.
- [ ] Add method freshness warning.

### Done when

- The CLI can tell what method version/profile it is using.
- Packets include relevant method sections, not random bulk docs.
- Users can pin method content for reproducibility.

---

# 7. Best-in-Class Command Surface

## 7.1 Final command taxonomy

```text
mythic-vibe init
mythic-vibe status
mythic-vibe next
mythic-vibe scan
mythic-vibe phase
mythic-vibe intent
mythic-vibe constraints
mythic-vibe architecture
mythic-vibe plan
mythic-vibe build
mythic-vibe verify
mythic-vibe reflect
mythic-vibe handoff
mythic-vibe packet
mythic-vibe ai
mythic-vibe method
mythic-vibe doctor
mythic-vibe config
mythic-vibe plugin
mythic-vibe plunder
mythic-vibe db
mythic-vibe policy
```

## 7.2 Ritual aliases

```text
imbue   -> init
scry    -> doctor
evoke   -> packet create
weave   -> reflect
heal    -> verify repair
oath    -> policy oath
grimoire -> plugin
```

## 7.3 Example golden workflow

```bash
mythic-vibe init --goal "Build a real Mythic Engineering CLI" --profile advanced

mythic-vibe scan --write-index

mythic-vibe intent capture \
  --task "Refactor CLI command router"

mythic-vibe constraints capture \
  --must-preserve "Existing README commands" \
  --must-not-touch "dormant islands"

mythic-vibe architecture map \
  --domain cli \
  --decision "Move command handlers into cli/commands"

mythic-vibe plan create \
  --task "Split cli.py into command modules"

mythic-vibe packet create \
  --role "Forge Worker" \
  --phase build \
  --task "Implement the command-module split safely" \
  --out mythic/packets/PKT-0001.md

mythic-vibe ai run --provider copy-paste --packet PKT-0001

mythic-vibe response ingest \
  --from-file mythic/responses/RESP-0001.md

mythic-vibe verify run \
  --command "pytest -q" \
  --command "python -m mythic_vibe_cli --help"

mythic-vibe reflect \
  --summary "CLI command router split into modular handlers"

mythic-vibe handoff create
```

---

# 8. Data Files to Add

## 8.1 Core schemas

```text
mythic_vibe_cli/resources/schemas/
  project_state.schema.json
  checkin.schema.json
  decision.schema.json
  verification.schema.json
  packet.schema.json
  plugin_manifest.schema.json
  plunder_manifest.schema.json
```

## 8.2 Template files

```text
mythic_vibe_cli/resources/templates/
  project/beginner/
  project/standard/
  project/advanced/
  docs/ARCHITECTURE.md.j2
  docs/DOMAIN_MAP.md.j2
  docs/DATA_FLOW.md.j2
  docs/INVARIANTS.md.j2
  docs/RISK_REGISTER.md.j2
  docs/VERIFICATION.md.j2
  docs/SESSION_HANDOFF.md.j2
  tasks/TASK.md.j2
  mythic/loop.md.j2
  mythic/plan.md.j2
  packets/generic.md.j2
  packets/codex.md.j2
  packets/claude.md.j2
  packets/gemini.md.j2
  packets/aider.md.j2
```

## 8.3 Governance files

```text
docs/
  ACTIVE_PRODUCT_BOUNDARY.md
  DORMANT_ISLANDS.md
  COMMAND_CONTRACTS.md
  PROVIDER_SECURITY.md
  PLUGIN_API.md
  PACKET_FORMATS.md
  STATE_SCHEMA.md
  MIGRATIONS.md
  RELEASE_PROCESS.md
```

---

# 9. Testing Strategy

## 9.1 Test categories

| Category | Purpose |
|---|---|
| Unit tests | Validate pure logic and data models. |
| CLI tests | Validate command parsing and outputs. |
| Golden file tests | Validate generated templates/packets. |
| Migration tests | Validate state upgrades. |
| Filesystem tests | Validate safe writes/backups. |
| Provider tests | Mock provider calls. |
| Plunder tests | Mock GitHub imports and license data. |
| Integration tests | Run full Mythic loop in temp project. |

## 9.2 Minimum release checks

```bash
ruff check .
pytest -q
python -m mythic_vibe_cli --help
python -m mythic_vibe_cli.cli --help
mythic-vibe init --goal "Smoke test" --path /tmp/mythic-smoke --profile standard
mythic-vibe doctor --path /tmp/mythic-smoke
mythic-vibe packet create --path /tmp/mythic-smoke --phase plan --task "Smoke packet"
```

## 9.3 Golden workflow test

A full integration test should:

1. create temp project,
2. initialize advanced scaffold,
3. scan project,
4. capture intent,
5. create plan,
6. create packet,
7. ingest mock response,
8. run fake verification command,
9. reflect,
10. create handoff,
11. assert all artifacts exist and state is coherent.

---

# 10. Release Milestones

## Milestone 0.2.0 — Stable Skeleton

```yaml
release: 0.2.0
theme: "Make the current CLI reliable."
must_ship:
  - __main__.py
  - split command handlers
  - better doctor
  - state migration v1
  - template files moved out of Python literals
  - tests for all current commands
```

## Milestone 0.3.0 — Real Mythic Workflow

```yaml
release: 0.3.0
theme: "Make the full loop operational."
must_ship:
  - phase commands
  - richer check-ins
  - task records
  - phase records
  - handoff create/resume
  - verification records
```

## Milestone 0.4.0 — Context and Packets

```yaml
release: 0.4.0
theme: "Make AI context packets serious."
must_ship:
  - project scanner
  - project index
  - packet IDs
  - role-aware packets
  - multiple packet formats
  - packet history
```

## Milestone 0.5.0 — Provider and Plugin Foundations

```yaml
release: 0.5.0
theme: "Make integration extensible."
must_ship:
  - provider adapter base
  - copy-paste provider
  - optional OpenAI/OpenRouter adapter
  - plugin registry
  - plugin hooks
```

## Milestone 0.6.0 — Plunder and Provenance

```yaml
release: 0.6.0
theme: "Make lawful code reuse disciplined."
must_ship:
  - plunder inspect/plan/fetch/apply
  - provenance manifest
  - license checks
  - NOTICE helper
```

## Milestone 0.7.0 — Deep Doctor

```yaml
release: 0.7.0
theme: "Make project health visible."
must_ship:
  - diagnostic codes
  - severity
  - JSON output
  - docs drift checks
  - boundary checks
  - remediation hints
```

## Milestone 1.0.0 — Best-in-Class Local-First Mythic Vibe CLI

```yaml
release: 1.0.0
theme: "A complete local-first Mythic Engineering CLI."
must_ship:
  - stable command contracts
  - documented schemas
  - migration support
  - full loop workflow
  - scanner
  - packet engine
  - verification gates
  - handoff/resume
  - release docs
  - CI
  - package install quality
```

---

# 11. Codex/Claude/Roo Implementation Packet Plan

Use this sequence to build the project safely with AI assistants.

## Packet 1 — Boundary Audit

```yaml
role: Architect
task: "Create ACTIVE_PRODUCT_BOUNDARY.md and ADR-0001."
files_allowed:
  - docs/
  - README.md
  - ARCHITECTURE.md
  - DOMAIN_MAP.md
files_forbidden:
  - dormant runtime folders
  - vendor mirrors
verification:
  - "pytest -q"
```

## Packet 2 — CLI Router Split

```yaml
role: Forge Worker
task: "Split cli.py into command modules without changing behavior."
files_allowed:
  - mythic_vibe_cli/cli.py
  - mythic_vibe_cli/cli/
  - tests/
verification:
  - "pytest -q"
  - "python -m mythic_vibe_cli.cli --help"
```

## Packet 3 — State Schema v1

```yaml
role: Architect + Forge Worker
task: "Implement schema-versioned ProjectState and migration from current status.json."
files_allowed:
  - mythic_vibe_cli/core/
  - mythic_vibe_cli/persistence/
  - mythic_vibe_cli/resources/schemas/
  - tests/
verification:
  - "pytest tests/test_state.py -q"
```

## Packet 4 — Template Extraction

```yaml
role: Scribe + Forge Worker
task: "Move scaffold templates out of Python string literals into resources/templates."
files_allowed:
  - mythic_vibe_cli/resources/templates/
  - mythic_vibe_cli/docs/
  - mythic_vibe_cli/workflow.py
  - tests/
verification:
  - "pytest -q"
```

## Packet 5 — Project Scanner

```yaml
role: Cartographer
task: "Implement project scanner and project_index.json."
files_allowed:
  - mythic_vibe_cli/context/
  - tests/
verification:
  - "pytest tests/test_scanner.py -q"
```

## Packet 6 — Packet Engine v2

```yaml
role: Forge Worker
task: "Replace Codex-only bridge internals with general packet builder while preserving codex-pack."
files_allowed:
  - mythic_vibe_cli/context/
  - mythic_vibe_cli/ai/prompts/
  - mythic_vibe_cli/codex_bridge.py
  - tests/
verification:
  - "pytest tests/test_packet_builder.py -q"
  - "mythic-vibe codex-pack --phase plan --task 'test'"
```

## Packet 7 — Verification Records

```yaml
role: Auditor
task: "Implement verify run and persistent verification records."
files_allowed:
  - mythic_vibe_cli/verify/
  - mythic_vibe_cli/workflow/
  - tests/
verification:
  - "pytest tests/test_verify.py -q"
```

## Packet 8 — Handoff/Resume

```yaml
role: Scribe
task: "Implement handoff create/latest and resume summary."
files_allowed:
  - mythic_vibe_cli/workflow/
  - mythic_vibe_cli/docs/
  - tests/
verification:
  - "pytest tests/test_handoff.py -q"
```

---

# 12. Non-Negotiable Quality Bar

Before calling this project "real working best there is," the CLI must satisfy:

```yaml
quality_bar:
  install:
    - installs in clean venv
    - runs on Windows PowerShell
    - runs on Linux shell
  commands:
    - every command has help
    - every writing command supports dry-run or clear preview where practical
    - every command returns meaningful exit codes
  state:
    - schema-versioned
    - migration-safe
    - backup-before-destructive-change
  docs:
    - docs updated with behavior changes
    - active product boundary clear
    - API contracts current
  ai:
    - copy-paste mode works without keys
    - provider mode explicit and logged
    - no hidden uploads
  verification:
    - test runner integrated
    - verification records persisted
    - doctor catches missing artifacts
  safety:
    - plunder tracks license/provenance
    - plugin system cannot silently corrupt core
    - dormant/vendor folders protected by diagnostics
```

---

# 13. Final Mythic Definition

When complete, Mythic Vibe CLI should be describable like this:

> **Mythic Vibe CLI is a local-first, architecture-aware AI coding command line that operationalizes Mythic Engineering. It turns creative intent into explicit constraints, domain-aware plans, AI-ready packets, verified changes, and durable continuity records. It preserves the speed of vibe coding while preventing drift, hidden coupling, lost reasoning, and context collapse.**

That is the standard.

Not a prompt wrapper.

Not a scaffold toy.

Not random AI automation.

A real Mythic Engineering workbench.
