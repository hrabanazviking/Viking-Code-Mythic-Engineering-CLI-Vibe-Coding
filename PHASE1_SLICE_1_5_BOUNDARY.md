---
title: "Phase 1 — Slice 1.5 Boundary Re-audit"
phase: PH-01
slice: 1.5
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 5ed5980
status: complete
result: clean
adrs_filed: 0
errors: 0
warnings: 0
---

# Phase 1 Slice 1.5 — Boundary Re-audit

## Purpose

Run `mythic-vibe doctor --repo-boundary` on the live development
branch, capture the diagnostics, and review every avenue by which
active runtime code could reach into a dormant island. File ADRs for
any missing-but-justified imports, or document why none are needed.

## Live `doctor --repo-boundary` result

```json
{
  "errors": [],
  "ok": true,
  "path": "<repo root>",
  "repo_boundary": true,
  "sections": {
    "boundary": [
      "REPO_BOUNDARY.md",
      "docs/ACTIVE_PRODUCT_BOUNDARY.md",
      "docs/DORMANT_ISLANDS.md",
      "docs/ADRS/ADR-0001-active-runtime-boundary.md",
      "docs/ADRS/ADR-0002-no-direct-vendor-imports.md"
    ],
    "docs": [],
    "required_artifacts": [],
    "state": []
  },
  "warnings": []
}
```

**Result: clean.** All five required boundary documents exist; no
forbidden absolute imports detected anywhere under `mythic_vibe_cli/`;
zero errors, zero warnings.

## Manual deeper audit beyond the automated check

The `doctor --repo-boundary` automation walks AST imports in
`mythic_vibe_cli/*.py` and flags any absolute import whose root name
is in `FORBIDDEN_RUNTIME_IMPORT_ROOTS`. To make sure no subtle bypass
pattern is in play, this slice also inspects:

### 1. Relative-vs-absolute import handling

`MythicWorkflow._absolute_imports` (workflow.py:342) correctly skips
`ImportFrom` nodes with non-zero `level` (i.e. relative `from .x` /
`from ..x` imports). Every `mythic_vibe_cli.ai.*` reference inside
the active runtime is a relative `from .ai...` (verified by grep).
The internal `mythic_vibe_cli/ai/` package is not the same thing as
the dormant top-level `ai/` island, and the AST walker does not
conflate them.

### 2. Dynamic / runtime imports

Two dynamic-import sites exist:

| Location | Purpose | Status |
|---|---|---|
| `plugins/dispatcher.py:164` | Loads a registered plugin module by name | Intentional plugin extension point. Plugins are user-supplied, opt-in via `grimoire add` / registry, and isolated by the dispatcher (plugin failures are caught and logged, never crash the CLI). |
| `plugins/loader.py:41` | Resolves a plugin's `entrypoint` string | Intentional. Same trust model as dispatcher. |

Neither dynamic-import site has any code path that targets a dormant
island root. Plugin entrypoints are arbitrary user-installable
packages; if a future user installed a plugin whose entrypoint lived
under a dormant island, that would be an audit surface for the
plugin (PH-10), not the boundary itself. **No remediation needed.**

### 3. `sys.path` manipulation

`grep -rn "sys.path" mythic_vibe_cli/` returns no matches. Active
runtime never inserts any path manipulation that could pull in a
dormant island.

### 4. Forbidden-roots set vs. documented boundary

`FORBIDDEN_RUNTIME_IMPORT_ROOTS` (workflow.py:14):

```python
{"ai", "core", "systems", "sessions", "yggdrasil", "imports",
 "mindspark_thoughtform", "ollama", "whisper", "chatterbox"}
```

The documented dormant-island list in `REPO_BOUNDARY.md` includes
the same roots plus `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/`,
`research_data/`, `docs/research/`, and `docs/specs/`.

| Item | Why it isn't in `FORBIDDEN_RUNTIME_IMPORT_ROOTS` | Risk |
|---|---|---|
| `WYRD-Protocol-...` | Directory name contains hyphens — Python cannot import it as a module under any circumstances. Naturally protected. | none |
| `research_data/` | Markdown only; no Python files. | none |
| `docs/research/` | Markdown only; no Python files. | none |
| `docs/specs/` | Markdown only; no Python files. | none |
| `imports/` (whole tree) | Doctor blocks the whole `imports` root, while `REPO_BOUNDARY.md` only flags `imports/norsesaga/` as dormant. The automated check is *stricter* than the documented boundary. | this is defense-in-depth and is the preferred direction of asymmetry. |

The automated check is conservatively stricter than the documented
boundary in one place (`imports/`); nowhere is it laxer. **No
remediation needed.**

### 5. `context/file_filters.py` — scan-time exclusions

The repository scanner excludes the same dormant islands from
project indexing (`mindspark_thoughtform/`, `WYRD-Protocol-*/`, etc.
listed in `file_filters.py:35-51`). This is a separate concern from
import-time enforcement (this slice's focus) but the lists are
consistent.

### 6. Tests

`tests/` is intentionally outside the boundary check scope. Tests
can import anything for fixture purposes. The test suite does not
currently import from any dormant island either, but that is not
enforced — and shouldn't be, because a future test of an island
adapter may legitimately need to. **No change needed.**

## ADRs filed

**Zero.** Every dynamic-import site, every conservative-stricter
forbidden-root, and every relative-import path is already covered by
the existing ADR-0001 (active runtime boundary) and ADR-0002 (no
direct vendor imports). No new architectural decision is being made
in this slice — it is hygiene confirmation only.

## Findings

**Zero new findings.** The boundary is in healthy shape. The slice
1.4 audit surfaced two real bugs (F-021 reflect-gate on `weave`,
F-022 doctor crash on bare projects). Neither was a boundary issue.
F-022 is now fixed (commit `5ed5980`); F-021 remains parked at PH-13.

## Slice 1.5 close

Slice 1.5 is complete. Live `doctor --repo-boundary` is clean; the
manual deeper audit found no bypass patterns; no ADRs needed. The
existing ADR-0001 / ADR-0002 fully cover the architectural claim.

The slice produces this memo as its only deliverable — no code
changes, no test changes.

## Phase 1 — fully closed

With slice 1.5 done, Phase 1 (Foundation Audit & Quality Sweep) is
**fully closed**:

| Slice | Result | Deliverable |
|---|---|---|
| 1.1 audit | 20 findings catalogued | `PHASE1_RUNTIME_AUDIT.md` |
| 1.2 issue triage | 21 issues mapped, 5 duplicate clusters | `PHASE1_ISSUE_TRIAGE.md` |
| 1.3 quick-fix sweep | 7 info-severity additive fixes | `PHASE1_SLICE_1_3_CLOSEOUT.md` |
| 1.4 coverage hygiene | +32 tests, 74→76% coverage, 2 new bugs | `PHASE1_SLICE_1_4_CLOSEOUT.md` |
| F-022 hot-fix | 1-line return-tuple fix + regression test | commit `5ed5980` |
| 1.5 boundary re-audit | clean — 0 errors, 0 warnings, 0 ADRs filed | this memo |

Slice 1.6 (Phase 1 close-out memo summarising the whole phase)
remains optional — the per-slice memos already capture the full
record. The next high-value move is **Phase 2: Slash Command Surface
Expansion**.
