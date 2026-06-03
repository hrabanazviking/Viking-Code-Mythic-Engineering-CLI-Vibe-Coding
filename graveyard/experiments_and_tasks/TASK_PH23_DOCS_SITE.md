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

### 2026-05-05 — Slice 23.1 closed (mkdocs-material documentation site)
**Shipped:**
- `mkdocs.yml` at repo root — comprehensive site config:
  - mkdocs-material theme with deep-purple primary + amber
    accent + light/dark palette toggle.
  - 13 navigation features enabled (tabs, sticky tabs, sections,
    expand, path, top, search highlight/suggest/share, code copy,
    code annotations, action edit, toc follow).
  - Inter + JetBrains Mono fonts.
  - 9 markdown extensions (admonition, attr_list, def_list,
    footnotes, md_in_html, tables, toc with permalinks, all
    pymdownx.* the project uses including details, highlight,
    inlinehilite, snippets, superfences, tabbed).
  - search plugin enabled.
  - Navigation tree: Home → Getting Started (Quickstart, Install)
    → Operator Guides (Hermes, Chat Bridge, SSH, Plugins,
    Plugin Authoring) → Reference (Command Contracts, API,
    Runtime, Compatibility, Hardware Profiles) → Architecture
    (7 docs) → Security (3 docs) → Governance (4 docs incl.
    Contributor Index) → Decision Records (10 ADRs explicitly
    listed).
  - Social links + generator footer suppressed.
- `docs/INDEX.md` — repurposed as the operator-facing site
  landing. New content: project one-liner, 4-quickstart-command
  recipe, 4-card "Where to start" grid (Quickstart / Install /
  Hermes / Verifying Artifacts), project shape paragraph
  pointing at Philosophy/Architecture/SystemVision, reference
  list, 8-channel distribution table, project values
  (stdlib-only, no telemetry, cryptographic provenance,
  cross-platform CI). The original contributor-orientation
  content was preserved at `docs/contributor_index.md` per the
  additive rule.
- `docs/contributor_index.md` — verbatim copy of the original
  INDEX.md contributor hub plus a PH-23.1 dated note explaining
  the move; extended sections to reference the new PH-21 + PH-22
  surfaces (Sigstore signing, tag signing, AUR / OCI / launcher
  / Android / WASI packaging directories).
- `.github/workflows/docs.yml` — new build + deploy workflow.
  Runs on every PR + push to development + push to main. Builds
  with `mkdocs build --strict` so broken nav links + missing
  files fail the PR. On main pushes only, also configures
  GitHub Pages, uploads the site artifact, and deploys. One-
  concurrent-deployment lock prevents stale-over-fresh races.
- `pyproject.toml` — `[docs]` extra extended with
  `mkdocs-material>=9.5` + `pymdown-extensions>=10.0`. `[dev]`
  superset extended with both packages too so contributors
  running `pip install -e ".[dev]"` can build the site without
  an extra install step.
- `tests/test_docs_site.py` — 18 tests across 5 classes:
    MkdocsConfigTests (5) — material theme, site metadata,
        search plugin, code-copy feature, palette toggle.
    NavEntryFilesExistTests (3) — extracts every `.md` path
        from the nav block and asserts the file exists under
        docs/ (catches strict-build failures at PR time).
    SiteLandingPageTests (2) — INDEX.md has the operator-
        facing landing content (pipx install command, Where
        to start, Distribution channels); contributor_index.md
        preserves the legacy contributor hub.
    DocsWorkflowTests (6) — runs on PR + main + development,
        strict build gate, .[docs] extra install, deploy-to-
        Pages gating on main+push only, deploy-pages action
        usage, pages concurrency lock.
    PyprojectDocsExtraTests (3) — [docs] pins mkdocs-material
        + pymdown-extensions; [dev] block (parsed via regex
        scoped to the dev block) includes both.

**Gates green:** 2499 passed / 1 skipped / 109 subtests (+18
from this slice); ruff clean; mypy clean (156 source files).

**Compatibility surface:** new operator-facing documentation
surface; existing markdown documents are unmodified except for
INDEX.md (repurposed for the site landing; legacy content
preserved at contributor_index.md). The old INDEX.md content
is reachable via the new "Governance → Contributor Index"
nav entry, so any contributor bookmark to "the doc index"
still resolves to the equivalent content.

**Operator step required to activate the site:** GitHub Pages
must be enabled on the repo settings (Settings → Pages →
Source: GitHub Actions). One-time click; the workflow handles
everything else from there.

PH-23.1 status: closed. Whether to open additional PH-23
slices (e.g. mkdocs versioning via mike, custom domain, search
analytics) is operator-driven — no PH-23.x is currently
scoped.
