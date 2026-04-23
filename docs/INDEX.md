# Mythic Vibe CLI Documentation Index

**Status:** Canonical documentation navigation map  
**Last updated:** 2026-04-23  
**Audience:** Users, contributors, maintainers, and future selves returning after context loss.

This index is the front door to the active documentation suite.

---

## 1) Start paths by role

### New user path (10–20 minutes)

1. `quickstart.md`
2. `SYSTEM_VISION.md`
3. `api.md` (CLI entrypoints section)

### Contributor path (20–40 minutes)

1. `ARCHITECTURE.md`
2. `DOMAIN_MAP.md`
3. `api.md`
4. Root `DEVLOG.md` and `CHANGELOG.md`

### Maintainer / release path

1. Root `CHANGELOG.md`
2. Root `DEVLOG.md`
3. `ARCHITECTURE.md`
4. `DOMAIN_MAP.md`

---

## 2) Core active docs

- `quickstart.md` — setup, first execution loop, troubleshooting.
- `SYSTEM_VISION.md` — product purpose, promises, anti-goals.
- `ARCHITECTURE.md` — active runtime architecture and dependency law.
- `DOMAIN_MAP.md` — ownership boundaries and routing rules.
- `api.md` — CLI/module contracts and filesystem interface.
- Root `README.md` — project-level overview and command orientation.
- Root `DEVLOG.md` — continuity record of major sessions.
- Root `CHANGELOG.md` — user-facing change history.

---

## 3) Source-of-truth boundaries

In case of disagreement between records:

1. Runtime behavior in `mythic_vibe_cli/` is ground truth for executable behavior.
2. `docs/ARCHITECTURE.md` defines active architecture intent.
3. `docs/DOMAIN_MAP.md` defines ownership and allowed boundaries.
4. `docs/api.md` defines user/integration-facing contracts.
5. Root `DEVLOG.md` preserves chronology and rationale.
6. Root `CHANGELOG.md` summarizes release-facing deltas.

If this order causes confusion, treat that as a docs bug and repair it in the same PR.

---

## 4) Documentation upkeep protocol

When you change behavior, update documentation in the same pull request:

- Command or output change -> `api.md` + `quickstart.md`
- Workflow/lifecycle change -> `ARCHITECTURE.md` + `api.md`
- Boundary ownership change -> `DOMAIN_MAP.md` + `ARCHITECTURE.md`
- Product positioning change -> `SYSTEM_VISION.md` + `README.md`
- Meaningful user-facing change -> `CHANGELOG.md`
- Session-level rationale/decision history -> `DEVLOG.md`

---

## 5) Drift signals (act immediately)

Treat these as warnings that documentation drift is occurring:

- CLI help text differs from examples in docs.
- New files/commands exist without any mention in docs.
- Runtime imports cross forbidden domain boundaries.
- `README.md` promises behavior that tests or command help do not show.
- `DEVLOG.md` lacks entries for significant architecture decisions.

---

## 6) Naming and style rules

- Prefer explicit, searchable headings over poetic ambiguity.
- Use absolute dates (`YYYY-MM-DD`) for durable chronology.
- Prefer stable paths in examples and avoid machine-specific absolute paths.
- Keep each doc answerable to a clear owner/scope.
- Avoid duplicating long content across multiple docs; link to source-of-truth files.

---

## 7) Companion hubs

- `docs/index.md` — reader-friendly documentation hub for quick orientation.
- Root `ARCHITECTURE.md` and `DATA_FLOW.md` — deeper repository-level records.
- `docs/research/` and `docs/specs/` — reference material, not active CLI runtime contracts.

---

## 8) Archival note

Documentation is treated as part of the product surface. If code changes are merged without matching documentation updates, continuity debt accumulates and should be corrected with priority.
