# Quarterly Architecture Review

**Cadence:** Once per calendar quarter (Jan, Apr, Jul, Oct).
**Owner:** The maintainer roster listed in `pyproject.toml`.
**Trigger command:** `mythic-vibe review architecture`.

---

## Why this exists

Mythic Engineering treats architecture as a **living artefact**,
not a one-time deliverable. Boundaries drift, ADRs go stale,
new dormant islands accrue, drift findings pile up. A
quarterly review keeps that drift visible and resolved before
it becomes a v2.0-sized rewrite.

---

## What runs each quarter

1. **Generate the checklist:** `mythic-vibe review architecture` produces a markdown checklist with:
   - Governance-doc presence audit (`docs/ARCHITECTURE.md`, `docs/DOMAIN_MAP.md`, `docs/DATA_FLOW.md`, `docs/ACTIVE_PRODUCT_BOUNDARY.md`, `docs/PHILOSOPHY.md`).
   - ADR count.
   - Drift summary (uses the existing PH-13 `drift.scan_for_drift`).
   - Open questions (auto-derived from missing artefacts + drift severity).
   - Reviewer checklist (5 manual items).

2. **Walk every ADR.** Mark `Superseded` ones explicitly. If an ADR's *Decision* no longer matches the code, either update the ADR or open a new one that supersedes it.

3. **Triage drift.** Every `warning`/`error` from `mythic-vibe drift dashboard` is either:
   - Actioned this quarter, OR
   - Documented as accepted (with a note in the relevant ADR or in the review log).

4. **Compare CHANGELOG `[Unreleased]` against the period's commits.** Use `python scripts/check_changelog.py --classify` (PH-20.F) to spot mis-categorised entries.

5. **Capture the review.** Save the rendered markdown (or a hand-edited subset) under `mythic/governance/review-<YYYY-MM-DD>.md`. The `mythic/governance/` directory is operator-curated content (per the PH-20.2 hard-rule, `doctor --fix` will never touch it).

---

## What does NOT belong in this review

- **Hot-fixes.** Architecture review is a forward-looking exercise. Acute bugs go through normal triage, not the quarterly window.
- **Feature scoping.** That's a separate planning ritual; the review answers *"is the foundation still sound?"*, not *"what should we build next?"*.
- **Personnel discussion.** Operator/team capacity is out of scope for the architectural pass.

---

## Cadence enforcement

There is no hard CI gate that enforces "the review ran this quarter" — that would be process bloat. Instead:

- The `mythic/governance/review-*.md` filename pattern lets operators audit by-eye whether a quarter was skipped.
- Maintainers can add a custom `git log --grep "review-architecture"` shell helper if they want a one-line "last review" report.
- Future v1.x slices may add an opt-in stale-review warning to `doctor` (similar to the PH-19.8 stale-catalog watchdog).

---

## Authors

This cadence document was written as part of Phase 20.H (audit remediation cycle 2026-05-03), the v1.0 launch polish.
