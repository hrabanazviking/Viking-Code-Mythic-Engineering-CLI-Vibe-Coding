# Documentation Standards and Continuity Charter

This charter defines how documentation is written, reviewed, evolved, and archived in the Mythic Vibe CLI repository.

Its purpose is simple: **our records should remain useful after context fades**.

---

## 1) Documentation principles

### 1.1 Durable over fashionable

Write for maintainers who arrive months later, not only for today’s active contributors.

### 1.2 Explain intent, not only mechanics

A command list without rationale causes future drift. Each major file should preserve:

- what exists,
- why it exists,
- what assumptions it depends on,
- what would invalidate it.

### 1.3 One canonical home per topic

If two docs describe the same contract, one is canonical and the other links to it. Duplicate authority invites divergence.

### 1.4 Operational clarity over ornamental language

Poetic framing is welcome, ambiguity is not. Every section should answer a practical question.

### 1.5 Explicit dates and explicit status

Use absolute dates (`YYYY-MM-DD`) in changelog/devlog records and note whether statements are:

- current behavior,
- planned behavior,
- historical behavior.

---

## 2) The active documentation spine

These files form the project's continuity backbone and should be reviewed together when major behavior changes.

- `README.md` — project identity, scope, install, command orientation.
- `docs/INDEX.md` — canonical navigation and ownership map.
- `docs/quickstart.md` — first-loop execution guide.
- `docs/INSTALL.md` — install matrix (PyPI / Homebrew / Scoop / wheelhouse / contributor / pre-release).
- `docs/ARCHITECTURE.md` — component model and dependency boundaries.
- `docs/api.md` — public CLI contracts and compatibility expectations.
- `docs/COMMAND_CONTRACTS.md` — durable contract surface for every command.
- `docs/DOMAIN_MAP.md` — ownership and boundary registry.
- `docs/DATA_FLOW.md` — state and artifact movement through the active CLI.
- `docs/ACTIVE_PRODUCT_BOUNDARY.md` — exact product paths and runtime contract.
- `docs/SYSTEM_VISION.md` — long-horizon purpose and non-goals.
- `docs/PHILOSOPHY.md` — values and engineering stance.
- `docs/runtime.md` — operator guide for the ten runtime primitives.
- `docs/plugins.md` — plugin authoring + dispatcher contract.
- `docs/compatibility_policy.md` (v1.0) — **binding contract** for SemVer, Python + OS support, deprecation cadence.
- `docs/security/threat_model.md` (v1.0) — assets / attackers / mitigations matrix.
- `docs/governance/quarterly_review.md` (v1.0) — architecture-review cadence + agenda.
- `docs/RELEASE_CHECKLIST.md` — pre-tag manual gates + tag-driven distribution flow.
- `DEVLOG.md` — narrative continuity for contributors.
- `CHANGELOG.md` — release/user-facing delta log (v1.0: `python scripts/check_changelog.py --classify` buckets entries by conventional-commit prefix).
- `CONTRIBUTING.md` — contributor onboarding (incl. compatibility-policy assessment guidance).

When one file changes and the others become stale, drift has begun.

---

## 3) Writing conventions

### 3.1 Required section pattern for major docs

For architecture/API/vision/policy documents, prefer this section order:

1. **Purpose**
2. **Scope (in and out)**
3. **Current state**
4. **Contracts/invariants**
5. **Failure modes and risks**
6. **Operational checklist**
7. **References / related docs**

### 3.2 Language conventions

- Prefer active voice.
- Expand acronyms on first use.
- Avoid vague terms like “soon,” “later,” or “obvious.”
- Use consistent product naming: **Mythic Vibe CLI**.

### 3.3 Code and command blocks

Every command example should be copy-paste safe and indicate context when needed:

- shell required,
- working directory assumptions,
- expected artifact output.

### 3.4 Compatibility statements

Where behavior can change, include a “Compatibility” subsection clarifying:

- what is stable,
- what is experimental,
- deprecation path expectations.

---

## 4) Review and update rhythm

### 4.1 Trigger events that require doc updates

A documentation update is required when any of the following occurs:

- new command or option added,
- command semantics changed,
- file layout or scaffold output changed,
- compatibility/deprecation policy changed,
- build/test workflow changed,
- major strategic direction changed.

### 4.2 Minimum update set by change type

- **CLI behavior change**: `README.md`, `docs/api.md`, `docs/COMMAND_CONTRACTS.md`, `CHANGELOG.md`.
- **Scaffold/template change**: `docs/quickstart.md`, `docs/ARCHITECTURE.md`, `CHANGELOG.md`.
- **Governance/direction change**: `docs/SYSTEM_VISION.md`, `DEVLOG.md`, `CHANGELOG.md`.
- **Boundary/ownership change**: `docs/DOMAIN_MAP.md`, `docs/ACTIVE_PRODUCT_BOUNDARY.md`, `docs/INDEX.md`, `DEVLOG.md`.
- **New attack surface / security-relevant change** (v1.0): `docs/security/threat_model.md` (per its §8 update procedure).
- **Public-surface stability change** (v1.0): `docs/compatibility_policy.md` (per its §9 additive-revision rule), `CHANGELOG.md` with a `Deprecated:` line, `CONTRIBUTING.md` if the contributor process changes.
- **New runtime primitive**: `docs/runtime.md` (new section), re-export from `mythic_vibe_cli/runtime/__init__.py`, focused test under `tests/`.
- **New plugin extension point or capability**: `docs/plugins.md` (new section), `mythic_vibe_cli/plugins/capabilities.py` `KNOWN_CAPABILITIES` AND the JSON schema enum (coordinated).
- **New AI provider**: `docs/api.md`, `mythic_vibe_cli/ai/registry.py`, static catalog rows in `mythic_vibe_cli/ai/providers/model_catalog.py`. The conformance suite (`tests/test_provider_contract_conformance.py`) auto-extends coverage.
- **Distribution / release flow change**: `docs/RELEASE_CHECKLIST.md`, `packaging/README.md`, `.github/workflows/release.yml`.

### 4.3 Session closure checklist

Before ending a meaningful session, confirm:

- decision rationale is written,
- command contract changes are documented,
- open questions are captured as explicit threads,
- index links still resolve,
- changelog/devlog entries are synchronized.

---

## 5) Drift detection and repair

### 5.1 Common drift signals

- docs promise commands that no longer exist,
- defaults in docs do not match runtime behavior,
- two files disagree on project scope,
- troubleshooting sections reference removed paths,
- (v1.0) the docs↔code contract auditor (`tools/contract_audit.py`) reports new undocumented handlers,
- (v1.0) the live contract-audit baseline (`tests/test_contract_audit.py:_BASELINE_ALLOW_UNDOCUMENTED`) names a handler that no longer exists in `COMMAND_HANDLERS`.

### 5.2 Drift response protocol

1. Identify canonical source for the contested topic.
2. Align non-canonical docs to canonical wording.
3. Add an entry in `DEVLOG.md` summarizing what drift was repaired.
4. Add a user-facing note in `CHANGELOG.md` if behavior understanding changed.
5. (v1.0) Re-run `python tools/contract_audit.py --strict` to confirm the docs↔code drift is closed.

### 5.3 Mechanical drift gates (v1.0)

These gates run in CI on every PR and catch a class of drift that prose review misses:

- `tools/contract_audit.py --strict` — every argparse handler must appear in at least one markdown doc reference (or the baseline allowlist).
- `tests/test_cli_kernel.py:test_command_registry_preserves_current_commands_and_aliases` — full command-handler set is locked.
- `tests/test_slash_commands.py:SlashCommandsCatalogTests` — every argparse handler must have a `BUILTIN_SLASH_COMMANDS` entry (with documented exclusions).
- `tests/test_sbom_committed.py` — committed SBOM at `docs/security/sbom.json` must be well-formed CycloneDX.
- `tests/test_architecture_review.py:CadenceDocPresenceTest` — `docs/governance/quarterly_review.md` must exist with the right header.

---

## 6) Session memory and archival discipline

### 6.1 DEVLOG expectations

Each devlog entry should preserve:

- date,
- session intention,
- what changed,
- why it matters,
- unresolved threads.

### 6.2 CHANGELOG expectations

Changelog entries should be concise, externally useful, and grouped by semantic categories (`Added`, `Changed`, `Fixed`, `Removed`, etc.).

### 6.3 Archival notes

When superseding a document:

- avoid silent deletion,
- leave a forwarding note or replacement link,
- preserve historical context in the devlog.

---

## 7) Documentation quality rubric

A mature document should score “yes” to all checks below:

- **Findable** — appears in `docs/INDEX.md`.
- **Scoped** — explicitly states what it covers and excludes.
- **Actionable** — gives clear next actions.
- **Consistent** — terminology and contracts match peer docs.
- **Dated** — when temporal claims are made, dates are explicit.
- **Maintainable** — includes enough structure for easy future edits.

---

## 8) Practical ownership model

Ownership is functional, not personal:

- whoever changes behavior is responsible for initiating doc updates,
- reviewers are responsible for drift checks,
- maintainers are responsible for continuity and archival coherence.

If ownership is unclear, default to updating docs rather than deferring.

---

## 9) Closing commitment

This repository may evolve quickly, but its memory should remain deliberate.

If code is the blade, documentation is the sheath: it preserves shape, protects intent, and keeps craft from rusting between sessions.
