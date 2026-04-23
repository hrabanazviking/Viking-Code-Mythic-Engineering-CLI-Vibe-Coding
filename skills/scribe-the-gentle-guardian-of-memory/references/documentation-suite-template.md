# Scribe Documentation Suite Template

Use this checklist when creating large documentation batches across any repository.

## 1) Continuity Core

Create or refresh:

- `DEVLOG.md`
  - Date-stamped session entries
  - Decisions made
  - Tradeoffs accepted
  - Follow-up tasks
- `CHANGELOG.md`
  - Added / Changed / Fixed / Removed sections
  - Version or milestone labels
- `docs/INDEX.md`
  - Canonical table of contents for all docs

## 2) Module Documentation Pack (`docs/modules/`)

Create one file per planned module, named:

- `docs/modules/<module_name>.md`

Each module doc should include:

1. Purpose
2. Ownership / boundaries
3. Inputs and outputs
4. Data model and contracts
5. Dependencies and integration points
6. Failure modes and mitigations
7. Test strategy
8. Milestones / implementation phases
9. Open questions

## 3) Protocol Documentation Pack (`docs/protocols/`)

Minimum protocol files:

- `docs/protocols/testing-protocol.md`
- `docs/protocols/security-protocol.md`
- `docs/protocols/reliability-protocol.md`
- `docs/protocols/operations-protocol.md`
- `docs/protocols/documentation-protocol.md`

## 4) Planning and Decision Records (`docs/plans/`)

Create:

- `docs/plans/implementation-roadmap.md`
- `docs/plans/decision-ledger.md`
- `docs/plans/risk-register.md`

## 5) Drift Repair Pass

- Cross-check names, statuses, and terminology across all docs.
- Ensure every planned module appears in index + roadmap + module docs.
- Ensure unresolved questions appear in both decision ledger and risk register.

## 6) Completion Gate

Before finishing:

- Verify all links resolve.
- Confirm no duplicate “source of truth” files conflict.
- Add a final continuity summary entry in `DEVLOG.md`.
