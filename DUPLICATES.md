# DUPLICATES.md — Definitive Register of Duplicated Files and Directories

**Last updated:** 2026-04-23
**Author:** Védis Eikleið (Cartographer)
**Scope:** Every duplicate pair or set I could verify in `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding` on branch `development`.
**Companion scrolls:** `MAP.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`, `YGGDRASIL_COMPARISON.md`, `IMPACT_integration.md`.

## Symbol legend (recommendation labels)

- `[IDENTICAL]` — byte-for-byte same content (md5 matched).
- `[DRIFT]` — similar but diverged (checksum differs; size close).
- `[SHELL]` — one side is a stub / empty placeholder.
- `[PARTIAL]` — one side is a strict (or near-strict) subset of the other.
- `[NAME-ONLY]` — same name, unrelated content (no real duplication).

**I recommend no action here.** This scroll is the ledger — Eirwyn's `RECOMMENDATIONS.md` will advise keep/merge/drop.

---

## 1. Top-level doctrinal markdown — four-way copies

These files appear at repo root AND inside each subproject, identical.

| File | Copies | Sizes (lines/bytes) | Label |
|---|---|---|---|
| `PHILOSOPHY.md` | root, `mindspark_thoughtform/`, `mindspark_thoughtform/MindSpark_ThoughtForge/`, `WYRD-Protocol-.../` | md5 `67078d2d...` across all 4 | `[IDENTICAL]` |
| `RULES.AI.md` | root, `mindspark_thoughtform/`, `mindspark_thoughtform/MindSpark_ThoughtForge/`, `WYRD-Protocol-.../` | md5 `fec75d83...` across all 4 | `[IDENTICAL]` |
| `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md` | root, `mindspark_thoughtform/`, `WYRD-Protocol-.../` | md5 `0a56e825...` across all 3 | `[IDENTICAL]` |
| `WORLD_MODELING_SKILL.md` | root, `mindspark_thoughtform/`, `WYRD-Protocol-.../` | md5 `505e2afd...` across all 3 | `[IDENTICAL]` |

---

## 2. `research_data/` — three-way full copy

Three complete copies of the 41-doc research series (00–40 plus supporting specs, `pyproject.toml`, `src/`, `tests/`, `wyrd_runtime/`):

| Path | Status |
|---|---|
| `research_data/` | canonical (has `pyproject.toml`, `src/`, `tests/`, `config/`, `examples/`, `scripts/`) |
| `mindspark_thoughtform/research_data/` | full copy of the `.md` corpus (no `src/`, no `tests/`) |
| `WYRD-Protocol-World-.../research_data/` | full copy of the `.md` corpus (no `src/`, no `tests/`) |

Sample md5 checks:

| File | All three copies | Label |
|---|---|---|
| `00_INDEX.md` | md5 `7fabffaa...` across all 3 | `[IDENTICAL]` |
| `01_architecture_overview.md` | md5 `0e365a29...` across all 3 | `[IDENTICAL]` |

Recommendation label for the corpus as a whole: **`[IDENTICAL]`** for the MDs, **`[PARTIAL]`** for the tree as a whole (only root has `src/`, `tests/`, `pyproject.toml`, `config/`, `examples/`, `scripts/`).

---

## 3. The three `wyrdforge` trees

Two Python package trees plus a reference-only folder.

| Path | Completeness | Has `__init__.py`? | `pyproject.toml` `name`? | Label |
|---|---|---|---|---|
| `WYRD-Protocol-.../src/wyrdforge/` | Full — `bridges/`, `ecs/`, `evals/`, `hardening/`, `llm/`, `loaders/`, `models/`, `oracle/`, `persistence/`, `runtime/`, `schemas/`, `security/`, `services/` (14 sub-packages) | yes | `wyrdforge` v1.0.0 | canonical |
| `research_data/src/wyrdforge/` | Strict subset — only `models/`, `runtime/`, `schemas/`, `security/`, `services/` (5 sub-packages) | **no** (no `__init__.py` anywhere in the tree) | `wyrdforge` v0.1.0 | `[PARTIAL]` |
| `mindspark_thoughtform/research_data/src/` | (not checked as full tree — appears similar to research_data/src/) | — | — | `[PARTIAL]` (inherits research_data layout) |

### 3.1 File-level comparison — WYRD canonical vs research_data/src/wyrdforge

Spot-checked md5:

| File | WYRD | research_data | WYRD lines | RD lines | Label |
|---|---|---|---|---|---|
| `models/bond.py` | `1c9769d8...` | `1c9769d8...` | — | — | `[IDENTICAL]` |
| `models/memory.py` | `c3b17e10...` | `c3b17e10...` | — | — | `[IDENTICAL]` |
| `security/permission_guard.py` | `6b56c39f...` | `6b56c39f...` | — | — | `[IDENTICAL]` |
| `services/bond_graph_service.py` | `ba0b64bd...` | `744693b1...` | 61 | 60 | `[DRIFT]` (1-line delta) |
| `services/memory_store.py` | `20d3538e...` | `8fe6f3ff...` | 69 | 68 | `[DRIFT]` (1-line delta) |
| `runtime/demo_seed.py` | `869580920c...` | `6d4e14bd...` | 33 | 32 | `[DRIFT]` (1-line delta) |

### 3.2 Sub-packages missing entirely on the research_data side

Present in WYRD, absent in `research_data/src/wyrdforge/`:

- `bridges/` (9 files)
- `ecs/` (entire ECS core)
- `evals/`
- `hardening/`
- `llm/`
- `loaders/`
- `oracle/`
- `persistence/`

Present in both:

- `models/` — full `bond.py`, `common.py`, `evals.py`, `memory.py`, `micro_rag.py`, `persona.py`
- `runtime/` — RD has only `demo_seed.py`; WYRD adds `character_context.py`, `turn_loop.py`
- `schemas/` — all 14 `.schema.json` files identical
- `security/` — 2 files identical
- `services/` — RD has 5 of 11 (`bond_graph_service.py`, `memory_store.py`, `micro_rag_pipeline.py`, `persona_compiler.py`, `truth_calibrator.py`); WYRD adds `contradiction_detector.py`, `memory_promoter.py`, `memory_to_rag.py`, `runic_engine.py`, `writeback_engine.py`, `__init__.py`

### 3.3 Crucial namespace note

Both `WYRD-Protocol-.../pyproject.toml` AND `research_data/pyproject.toml` declare `name = "wyrdforge"`. If both were installed, they would collide on package name (pip/setuptools would refuse, or the second install overwrites the first). Absent `__init__.py` in `research_data/src/wyrdforge/`, it is not currently importable as a package anyway.

Recommendation label for the full comparison: **`[PARTIAL]` + `[DRIFT]`** — `research_data/` is a partial, slightly-older snapshot; WYRD is canonical.

---

## 4. NSE systems — root copy vs `imports/norsesaga/` copy

| File | `systems/` (root) | `imports/norsesaga/systems/` | Size (lines) | Label |
|---|---|---|---|---|
| `event_dispatcher.py` | present, md5 `8fd2f248...` | present, md5 `8fd2f248...` | 145 / 145 | `[IDENTICAL]` |
| `world_dreams.py` | **absent** | present, 140 lines | — | **unique to imports/** |
| `world_will.py` | **absent** | present, 182 lines | — | **unique to imports/** |

`imports/norsesaga/systems/` is **not** a duplicate subset — it is a tiny companion directory adding two files (`world_dreams.py`, `world_will.py`) that the root `systems/` does not carry, plus one that is identical.

Recommendation label: `event_dispatcher.py` = `[IDENTICAL]`; the two `world_*.py` files = neither duplicate nor shell — they are **additions**.

First-pass note H-4 (in `MAP.md`) framed this as "two copies of NSE systems, each incomplete"; the more precise reading is: the root `systems/` has 28 modules (the full engine), and `imports/norsesaga/systems/` has 3 modules where 1 is identical and 2 are additive.

---

## 5. NSE engine name duplication — `wyrd_system.py`

Two unrelated files share this name:

| Path | Purpose | Label |
|---|---|---|
| `systems/wyrd_system.py` | NSE "Three Wells / Norns" fate system (~33 KB per `INVENTORY.md`) | — |
| `yggdrasil/core/wyrd_system.py` | Yggdrasil's own wyrd subsystem | — |

These are `[NAME-ONLY]` — different implementations, different packages, not duplicates in the byte sense. Flag only because reader confusion is guaranteed.

---

## 6. Yggdrasil name duplication — already mapped

See `YGGDRASIL_COMPARISON.md` for full side-by-side.

| Path | Kind | Label |
|---|---|---|
| `yggdrasil/` (top-level package) | NSE cognitive router | `[NAME-ONLY]` (vs WYRD) |
| `WYRD-Protocol-.../src/wyrdforge/ecs/yggdrasil.py` | WYRD spatial hierarchy service | `[NAME-ONLY]` (vs NSE) |

---

## 7. MindSpark internal shell

| Path | Contents | Label |
|---|---|---|
| `mindspark_thoughtform/` (outer) | Full project (src/thoughtforge/, tests/, configs/, data/, research_data/, etc.) | canonical |
| `mindspark_thoughtform/MindSpark_ThoughtForge/` (inner) | Only `PHILOSOPHY.md`, `README.md`, `RULES.AI.md` | `[SHELL]` |

The inner folder has **no Python**, no tests, no config — only three doctrinal MDs that are themselves identical to the ones at the root (see section 1). Visible artifact of a renaming or nested-clone operation.

---

## 8. `docs/specs/` — root vs `mindspark_thoughtform/docs/specs/`

All 27 spec files in `docs/specs/` are byte-identical copies of those in `mindspark_thoughtform/docs/specs/`. Sample md5 checks:

| File | root | mindspark | Label |
|---|---|---|---|
| `Algorithms_and_Pseudocode_Spec.md` | `9364a488...` | `9364a488...` | `[IDENTICAL]` |
| `ThoughtForge_Complete_Implementation_Guide.md` | `afc5d1f4...` | `afc5d1f4...` | `[IDENTICAL]` |
| `GALDRABOK_PREFACE.md` | `21df822f...` | `21df822f...` | `[IDENTICAL]` |

Recommendation label for the full set: **`[IDENTICAL]`** — either the root has been "lifted" from MindSpark, or MindSpark and root share a sync.

---

## 9. Emotional Engine Integration Plan — space-vs-underscore drift

| File | md5 | Lines | Label |
|---|---|---|---|
| `Emotional Engine Integration Plan for Norse Saga Engine.md` | `2611fc29...` | 299 | older/shorter |
| `Emotional_Engine_Integration_Plan_for_Norse_Saga_Engine.md` | `e5e8f776...` | 397 | newer/longer |

Same title, different filenames (space vs underscore). **Not** identical — the underscored version is ~33% longer. Label: `[DRIFT]`.

---

## 10. Mythic Engineering CLI doctrine — filename family

These live at repo root and share concept but not bytes (unchecked for md5 here; filenames alone show drift):

- `Mystic_Engineering_Protocals1.0.md` (170 KB, note: typo *Mystic*/*Protocals*)
- `Mythic_Engineers_Codex.md` (88 KB)
- `Mythic_Engineering_CLI_Design_Ideas_7373y4yj.md` (47 KB)
- `MYTHIC_ENGINEERING.md` (generated by `cli.cmd_init`)
- `practical_mythic_engineering_step_by_step.md`
- `Quick_Guide_to_Mythic_Engineering_Vibe_Coding.md`
- `Ada_Lovelace_Explains_Mythic_Engineering.md`

Label: **`[NAME-ONLY]`** — different docs on a shared theme; treat as one corpus, not as duplicates.

---

## 11. arXiv data dumps

| File | Size | md5 | Consumed by? | Label |
|---|---|---|---|---|
| `arxiv_results.json` | 44 KB | — | `scripts/parse_arxiv_and_generate.py` (live) | canonical |
| `arxiv_all_papers.json` | 77 KB | — | nothing | redundant |
| `arxiv_papers.json` | 9 KB | — | nothing | redundant |
| `relevant_papers.json` | 67 KB | — | nothing | redundant |

Four separate dumps, only one live consumer. I have not md5-compared for drift (they differ in size, so they are not identical). Label: `[NAME-ONLY]` — same corpus family, different snapshots / subsets.

---

## 12. Ephemeral runtime artifacts (noted for completeness — not duplicates)

| Path | Kind | Note |
|---|---|---|
| `diagnostics/turn_trace.jsonl` | 46 MB JSONL | Only one copy; a captured NSE run log. Not a duplicate. Included here only because its size (46 MB) is unusual for a source repo. |

---

## 13. Summary table

| Duplication class | Count | Worst case | Lowest-risk action |
|---|---|---|---|
| Identical doctrinal MDs across 3–4 roots | 4 files × 3–4 locations | — | Decide on a single canonical root; keep others as symlinks or generate-on-install. |
| Identical docs/specs across root + mindspark | 27 files × 2 locations | — | One of these should be the source. |
| Identical research_data corpus across 3 locations | ~41 MDs × 3 | — | Root `research_data/` should be canonical; inner copies can be pruned. |
| wyrdforge partial duplicate (root vs WYRD) | ~16 files present in both, 3 drift | partial + drift | See `IMPACT_integration.md` section on WYRD. |
| NSE `systems` vs `imports/norsesaga/systems` | 1 identical + 2 unique | — | Identify whether `world_dreams.py` / `world_will.py` are needed; absorb or drop. |
| MindSpark internal `[SHELL]` | 1 dir | — | Remove or document. |
| Emotional Engine plan drift | 2 files, different sizes | — | Pick the longer (newer) as canonical; archive the shorter. |
| Name-only collisions | Yggdrasil (2), wyrd_system (2) | — | Document the disambiguation in the future integration README. |

**Nothing here is broken by the duplication itself** — Python would not crash, the CLI runs regardless. These are maintenance and clarity costs, not runtime costs, with one exception: the `research_data/pyproject.toml` declaring `name = "wyrdforge"` is a latent install-time collision with the real WYRD package. That one is a ticking watch, not a present fire.
