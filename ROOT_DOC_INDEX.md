# Root Doc Index — Navigating the 200+ .md files at the repo root

**Last updated:** 2026-05-03 (v1.0.0)

This repository's root directory contains **200+ Markdown files**. Most are *not* part of the active Mythic Vibe CLI v1.0.0 product surface. This index sorts them into tiers so a new contributor knows what's load-bearing, what's historical, and what's auxiliary research.

> **Quick rule of thumb.** If you're trying to understand the active product, start with `README.md` and follow the stones from `docs/INDEX.md`. Everything else here is reference material.

---

## Tier 1 — Active product governance (load-bearing)

These are the canonical operator + contributor surfaces for v1.0.0:

| File | Role |
|---|---|
| `README.md` | Front door — install, command overview, philosophy |
| `CHANGELOG.md` | Release-facing change history (v1.0.0 entry binding) |
| `DEVLOG.md` | Narrative continuity for contributors |
| `CONTRIBUTING.md` | Contributor onboarding (incl. compatibility-policy guidance) |
| `LICENSE` | Apache-2.0 license text |
| `NOTICE` | Apache attribution |
| `LEGAL-NOTICE.md` | Distribution position + no-personal-info-gatekeeping statement |
| `THIRD_PARTY_NOTICES.md` | Plundered-material attribution + originals callout |
| `REPO_BOUNDARY.md` | Active runtime boundary law + v1.0 enforcement gates |
| `MYTHIC_ENGINEERING.md` | Method headline (the "what is this method?" doc) |
| `RELEASE_v1_0_0_2026-05-03.md` | v1.0.0 launch closeout memo |
| `pyproject.toml` (not .md, but co-located) | Package metadata, entry points, build config |

For every other operator-facing doc, see [`docs/INDEX.md`](docs/INDEX.md).

---

## Tier 2 — Active monorepo survey docs

These are still useful for understanding the **whole repository** (including dormant islands), but the **active-product-only** record now lives under `docs/`:

| Root file | Active-product-only counterpart |
|---|---|
| `ARCHITECTURE.md` | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| `DATA_FLOW.md` | [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md) |
| `DOMAIN_MAP.md` | [`docs/DOMAIN_MAP.md`](docs/DOMAIN_MAP.md) |
| `DEPENDENCIES.md` | (no direct counterpart — see `docs/DOMAIN_MAP.md` §4 for the v1.0 internal-edge ownership map) |

When the two diverge in scope, the `docs/` version is authoritative for the v1.0.0 product surface; the root version is authoritative for the broader monorepo posture.

---

## Tier 3 — Historical audit logs (immutable)

These are the audit-cycle records from the 2026-05-02 fake-code / pseudo-code / bug-sweep cycle. Treated like ADRs: **immutable historical records**. Don't edit; supersede only by writing a new audit if the underlying behavior changes.

- `AUDIT_FAKE_TEMP_CODE_2026-05-02.md`
- `AUDIT_PSEUDOCODE_DEEP_2026-05-02.md`
- `AUDIT_BUG_SWEEP_2026-05-02.md`
- `AUDIT_REMEDIATION_CLOSEOUT_2026-05-02.md`
- `AUDIT_REMEDIATION_VERIFICATION_2026-05-02.md`
- (Companion in `docs/ADRS/`: `ADR_SANITY_SWEEP_2026-05-03.md`)

---

## Tier 4 — Historical task plans

Per-session task files written during PH-01 through PH-22 implementation. Many are now historical; a few (e.g. `TASK_PH19_DISTRIBUTION.md`) are still updated additively as their phases close.

Pattern: `TASK_<topic>.md` or `TASK_phase<N>_<topic>.md`. Examples include:

- `TASK_PH19_DISTRIBUTION.md` — PH-19 + PH-20 live plan tracker (still updated additively).
- `TASK_master_roadmap_and_phase1.md`, `TASK_phase2*.md`, ..., `TASK_phase18_robustness.md` — historical phase plans.
- `TASK_pi_plunder_*.md` — historical per-primitive plunder task plans.
- `TASK_textual_tui.md`, `TASK_tui_*.md` — historical TUI slice plans.
- `TASK_wire_*.md` — historical wiring task plans.

These are kept for continuity — a future contributor can read them to understand why a slice landed the way it did. They are not meant to be edited as living docs.

---

## Tier 5 — Auxiliary research / persona / reference material

The bulk of root-level .md files are auxiliary content from the broader Mythic Engineering workspace:

- **Persona / role specs** — `CHARACTER_RULES.md`, `CARTOGRAPHER_*.md` (4 files), `Various_Astrid_*.md`, persona prompt material.
- **Companion-project research** — files referencing NorseSagaEngine, MindSpark, WYRD, Yggdrasil, ThoughtForge: `Building the Yggdrasil Cognitive Architecture in Python_*.md`, `Emotional Engine Integration Plan*.md`, `Fate-Weaver_Protocol_*.md`, `WORLD_MODELING_SKILL.md`, `YGGDRASIL_*.md`, etc.
- **AI-tool plundering guides** — `Aider_Plundering_Guide.md`, `Gemini_CLI_Plundering_Guide.md`, `Goose_Plundering_Guide.md`, etc. (one per upstream agent surveyed).
- **Diagnostic templates** — `diagnostics_*.md` (10 files): canonical templates for debugging / dependencies / examples / interface / metrics / patterns / prompts / tasks / tests.
- **Generated docs templates** — `generate_docs_*.md`.
- **Essays + manifestos** — `Ada_Lovelace_Explains_Mythic_Engineering.md`, `Heathen_Third_Path_and_Cyber-Viking_Ethos.md`, `HJARTAFORGUN_-_The Heart-Forging.md`, `VIBRANT_VOYAGER_*.md`, `Völuspá_CLI_-_The_Seeresss_Prophecy_of_Code.md`, `Viking_Code_The_Fusion_*.md`.
- **Architecture studies + planning artifacts** — `ARCHITECTURE_STUDY_March-8-2026.md`, `ARCHITECT_REFACTOR_BLUEPRINT.md`, `CODE_REQUIREMENTS_MATRIX.md`, `Vibe_Coding_CLI_Tools_-_Aggregate_Feature_and_Interface_Report.md`, `Viking_Code_Mythic_Engineering_CLI_-_Ultra-Advanced_Design_Plan.md`.
- **Operator policy** — `INSTRUCTIONS_FOR_AI.md`, `JULS_INSTRUCTIONS.md`, `FILE_AI_IS_NOT_TO_CHANGE.md`.
- **External corpus references** — `Good_AI_Models_March-2026.md`, `arxiv_AI_theories_integration_report_*.md`, `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md`.

These are reference material, not active product docs. They were not part of the v1.0.0 doc-audit cycle (which focused on operator-facing + governance + method tier docs in `docs/`).

---

## Tier 6 — Per-phase closeout memos

Phase-finale and slice-finale memos written during implementation:

- `FOLLOWUP_SUBSLICES_CLOSEOUT.md`, `PHASE15_FINALE_CLOSEOUT.md`, etc. (when present)
- `RELEASE_v1_0_0_2026-05-03.md` (v1.0 launch — see Tier 1)

These follow the same immutability convention as ADRs and audit logs.

---

## Practical guidance

- **New contributor reaching this repo for the first time:** read `README.md` → `docs/INDEX.md` → `docs/quickstart.md`. Ignore everything else until you have a question.
- **Trying to understand a specific area:** check `docs/` first; fall back to root only if `docs/` doesn't cover it.
- **Trying to understand history:** start with `DEVLOG.md` and `CHANGELOG.md`, then read the audit + task files relevant to the period.
- **Trying to add a new doc:** prefer `docs/` over root. Add an entry to `docs/INDEX.md` and to `ROOT_DOC_INDEX.md` (this file) tier table when you do.

---

## Audit cadence

This index was created during the v1.0.0 documentation audit (2026-05-03). The active-product doc surface in Tier 1 + Tier 2 is reviewed each release per `docs/RELEASE_CHECKLIST.md`. Tier 3-6 are reviewed only when their topic comes back into active scope (e.g. via an ADR drawing dormant material into the product path).

The next scheduled architecture review (per `docs/governance/quarterly_review.md`) is the appropriate moment to revisit whether any Tier 5 / Tier 6 file should be promoted, archived, or removed.
