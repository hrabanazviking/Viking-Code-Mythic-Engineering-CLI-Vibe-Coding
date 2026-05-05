# TASK — PH-23 Documentation Site (kickoff)

**Opened:** 2026-05-05 (autonomous run, immediately after PH-22)
**Branch:** `development`
**HEAD at kickoff:** `dad841b` (PH-22 final slice closed)
**Operator:** Volmarr Wyrd
**Author:** Runa Gridweaver Freyjasdottir, executing on Volmarr's behalf
**Status:** `OPEN — AUTONOMOUS RUN — slice 23.1`

---

## Why PH-23 exists

The master roadmap stopped at PH-22. Volmarr's autonomous-mode
authorization explicitly covered "all other best order slices and
phases after that." Opening PH-23 here, with the highest-value
clean greenfield slice as the first piece. Future PH-23+ slices
are operator-driven.

PH-23 scope: **cross-cutting polish + operator UX** that doesn't
fit any earlier phase but raises the project's overall floor.
Each slice is independently scoped — picking PH-23.1 to ship
without binding a future PH-23.x to anything.

---

## Operating rules (carry-over)

Same discipline that ran PH-19 → PH-22:
1. **Additive only — never subtractive.**
2. TASK file → commit + push → implement → ruff/mypy/pytest green
   → per-slice closeout addendum → memory update → push.
3. ruff + mypy + pytest gate every Python commit.
4. Stdlib-first; cross-platform; open-source-only.
5. One cohesive slice per commit; no batching.

---

## Slice 23.1 — mkdocs-material documentation site

**Why:** the project has accumulated ~20 markdown documents
across `docs/`, `packaging/`, and the repo root. Cross-references
work but search doesn't, and operators landing on
`README.md` have to know which markdown file to grep for the
answer to their question. A real documentation site
consolidates everything into a navigable, searchable surface.

**Why now:** clean greenfield work; no risk of breaking existing
surfaces. The existing `mkdocs` extra in `pyproject.toml` already
exists from PH-15 — this slice activates it with real content.

**Deliverables:**
- `mkdocs.yml` — site configuration with mkdocs-material theme,
  navigation tree pulling in every existing document under
  logical sections, search plugin, palette + features tuned
  for technical docs.
- `docs/index.md` — landing page consolidating the project's
  one-liner, install quick-reference, and pointers to the
  core documents.
- New `.github/workflows/docs.yml` — build + deploy workflow
  that runs `mkdocs build --strict` on every PR (link rot
  detection) and deploys to GitHub Pages on `main` push.
- `pyproject.toml` — `[docs]` extra updated to pin
  `mkdocs-material` alongside the existing `mkdocs` dep.
- `tests/test_docs_site.py` — Python-side tests asserting
  `mkdocs.yml` structure, every document referenced in the
  nav exists, the workflow shape, and the strict-build gate.

**Out of scope (deferred):**
- Custom domain (docs.mythic-vibe.dev) — Volmarr-side DNS work.
- mkdocs-material insiders features — paid tier; the public
  theme covers this slice's needs.
- Versioned docs (mike plugin) — useful for v2.0 but the v1.x
  release wave doesn't have enough divergence to need it yet.

---

## Status updates per slice (additive log)

### 2026-05-05 — Slice 23.1 in flight
TASK file written, plan locked. Starting work in this commit.
