# RECOMMENDATIONS — The Integration-Readiness Register

**Last updated:** 2026-04-23
**Branch:** development
**Scribe:** Eirwyn Rúnblóm
**Scope:** Every major directory and notable root-level file in `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`, weighed against the declared product (the Mythic Vibe CLI) and given a keep/merge/drop/defer judgement.
**Purpose:** A register Volmarr can read in a single sitting and turn into decisions. Each row stands on its own evidence. Where a call is genuinely his to make, it is marked honestly as `DEFER — NEEDS VOLMARR`, with the trade-off laid out plainly.

---

## Prelude

This is the second pass. The first pass (`INVENTORY.md`, `ORIGINS.md`, Védis's `MAP.md` / `ARCHITECTURE.md` / `DEPENDENCIES.md` / `DATA_FLOW.md`) established what lives here and where it came from. This register asks a different question: **given that the product is the Mythic Vibe CLI — a small, deliberately-scoped vibe-coding harness built around a copy-paste bridge to ChatGPT Plus / Codex — what should become of everything else in this hall?**

Three shaping truths govern every row below:

1. **The CLI is an island.** `mythic_vibe_cli/` imports nothing outside its own package and stdlib. Everything else in the repo is optional cargo. A keep/merge decision therefore costs nothing in the CLI's own runtime; it is a question of **maintenance surface**, **distribution weight**, and **narrative coherence**.
2. **The CLI's only external dependency at runtime is GitHub.** `mythic_data.py` fetches markdown from `hrabanazviking/Mythic-Engineering`. The CLI is therefore *well-positioned* to pull methodology corpus from other repos on demand rather than vendor it.
3. **`pyproject.toml` declares only `mythic_vibe_cli` as the package.** When this project is installed with `pip install -e .`, none of the imported subtrees ship. They live in the repo but not in the wheel. That is a structural clue about the author's intent: these are reference corpora and future-integration candidates, not part of the shipped product.

---

## Label legend

| Label | Meaning |
|---|---|
| `KEEP AS-IS` | Present, wanted, already correctly scoped — leave alone. |
| `MERGE INTO CLI` | The logic belongs inside `mythic_vibe_cli/` proper and should be unified with the product package. |
| `WRAP AS SUBCOMMAND` | The functionality is valuable but separate; expose it through a new `mythic-vibe <verb>` subcommand while the source stays where it is or is modestly relocated. |
| `EXTRACT SELECTED PIECES` | A small, load-bearing subset is worth keeping; the rest is noise. Pull the subset into the CLI or a clean sibling module; discard the remainder. |
| `DROP — DUPLICATE` | A copy of content that exists canonically elsewhere in the repo; removing it loses nothing. |
| `DROP — UNUSED` | Present but unreferenced by CLI, and not a candidate for future integration under the CLI's declared scope. |
| `DEFER — NEEDS VOLMARR` | A genuine design choice only Volmarr can make; the register lays out the trade-off and waits. |
| `VENDOR-FREEZE — UPSTREAM` | Third-party code that must not drift. If kept, pin a commit SHA and document the pinning rule; if dropped, depend on the upstream installation externally. |

---

## Register — directories

| Path | Origin | Current state | Recommendation | Reasoning |
|---|---|---|---|---|
| `mythic_vibe_cli/` | MythicVibeCLI (NEW) | Live product — 6 Python files, complete command set, tested by `tests/` | `KEEP AS-IS` | This is the declared deliverable. Tight scope, cohesive, already tested. |
| `tests/` | MythicVibeCLI (NEW) | Three test modules covering CLI, config/bridge, workflow | `KEEP AS-IS` | The only tests that cover shipped code. Alignment is already correct. |
| `ai/` | NSE | Two files: `openrouter.py` (35 KB async client), `local_providers.py` (23 KB hardened Ollama/LM-Studio/OAI-compat client) | `DEFER — NEEDS VOLMARR` | These are genuinely useful building blocks for a future provider layer, but the CLI currently has *no provider layer* — the Codex bridge is copy-paste. Two viable futures: **(a)** extract `local_providers.py` as the basis for a `mythic-vibe run` local-model subcommand (would pair naturally with the `ollama/` vendor); **(b)** drop both and keep the CLI provider-free, leaving `mythic_vibe_cli` as a pure orchestration tool. Volmarr's choice between "the CLI grows teeth" vs "the CLI stays a scaffolder" decides this. |
| `core/` | NSE | Six small NSE modules; at least two (`emotional.py`, `dream_system.py`) import the non-existent `yggdrasil_core` package | `EXTRACT SELECTED PIECES` or `DROP — UNUSED` | In broken-import state as imported. `yggdrasil.py` (rune-tagging of VAD vectors) is a cohesive 2.6 KB self-contained module that *could* be the seed of a `mythic-vibe rune` subcommand if rune-aligned metaphor is desired in the CLI; `message_queue.py` is a stub. The rest is NSE-runtime internals with no place in the CLI's scope. Favour dropping unless `rune` commands are wanted, in which case extract `core/yggdrasil.py` alone. |
| `systems/` | NSE | 28 modules, ~500 KB — NSE's full engine room (personality, emotional engine, RAG, memory, stress, romance, dice, religion, runic, voice bridge, wyrd system) | `DEFER — NEEDS VOLMARR` | This is NSE's heart, living complete in the attic of the CLI repo. The CLI does not and should not run any of it. Three viable futures: **(a)** **excise entirely** from this repo — NSE owns this code in its own repo, and there is no design reason for the CLI to carry the engine room; **(b)** keep as **reference material** but move to `reference/nse_systems/` so it is not confused with the product; **(c)** keep a single load-bearing study piece (e.g. `personality_engine.py` as a reference for the CLI's future persona-aware prompt packets). My judgement leans toward (a), but this is Volmarr's decision — it is *his* engine, imported here for reasons the repo does not record. |
| `sessions/` | NSE | One file: `memory_manager.py` (16 KB) | `DROP — UNUSED` | Isolated, NSE-flavoured, unreferenced by CLI. If kept at all, should follow `systems/` into a reference folder. |
| `yggdrasil/` | NSE (earlier era) | Extensive OpenRouter-centric cognitive router with Nine-Worlds modules, Huginn/Muninn ravens, 11–12 paired AI-sidecar markdown files per Python module | `DEFER — NEEDS VOLMARR` | Two futures are both defensible: **(a)** this is an abandoned NSE design superseded by the WYRD Protocol's ECS Yggdrasil — drop it; **(b)** this is a distinct, still-valued cognitive-routing architecture that Volmarr wants in the CLI orbit, in which case it should move to its own sibling repo (e.g. `yggdrasil-cognitive`) because **it is the largest single maintenance surface in this tree** (paired sidecar docs multiply file count roughly twelve-fold). Keeping it inside this repo without a plan dilutes the CLI's scope. See also the **Yggdrasil comparison** note below. |
| `diagnostics/` | NSE (probable) | One file: `turn_trace.jsonl` (46 MB) | `DROP — UNUSED` | Forty-six megabytes of undocumented NSE session log, checked into a CLI repo it does not serve. If archival value is real, move to a data-archive location outside this repo; do not ship it inside the CLI's repository. |
| `imports/norsesaga/systems/` | NSE | Three files (`event_dispatcher.py`, `world_dreams.py`, `world_will.py`) | `DROP — DUPLICATE` | Stripped subset overlapping with the fuller `systems/` and `core/` trees. If `systems/` is kept at all, this is strictly redundant; if `systems/` is dropped, this scrap should go with it. |
| `mindspark_thoughtform/` | MindSpark | Near-full snapshot of the MindSpark ThoughtForge project — own `pyproject.toml`, `Dockerfile`, 620-test suite, phase task files, full `src/thoughtforge/` | `DEFER — NEEDS VOLMARR` | MindSpark is its own shipped project (per memory, v1.2.0 live with 620 tests in its own repo). Carrying a full copy here means **this repo must re-synchronise whenever MindSpark advances**, or else silently fall behind. Three options: **(a)** drop the snapshot; if CLI ever needs MindSpark, pin it as a real pip dependency of a future subcommand; **(b)** keep as reference but explicitly freeze it — annotate with the exact MindSpark commit SHA it was copied from and mark as a read-only reference; **(c)** absorb MindSpark into this repo as a sibling package and deprecate the other repo. (c) is the heaviest and would require Volmarr's deliberate choice. |
| `mindspark_thoughtform/MindSpark_ThoughtForge/` | MindSpark | Empty shell — only `PHILOSOPHY.md`, `README.md`, `RULES.AI.md`; no code | `DROP — DUPLICATE` | Half-finished nested clone artefact. Those three files already exist at the MindSpark root. No content is lost by deletion. |
| `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | WYRD | Near-full snapshot of the shipped WYRD v1.0.0 — 1700+ Python tests, all twenty engine integrations, full `src/wyrdforge/`, TASK_PHASE*.md files 0–19 | `DEFER — NEEDS VOLMARR` | Same structural problem as MindSpark, at larger scale. WYRD is a shipped v1.0.0 product with a tag and its own repo. Options: **(a)** drop the snapshot entirely — the CLI has no edge into WYRD; **(b)** keep as frozen reference with pinned commit SHA in a `reference/` folder; **(c)** turn the CLI into the WYRD Protocol's vibe-coding harness, in which case the integration story needs to be designed, not implicit. Until Volmarr writes an integration design, option (a) honours the CLI's declared scope most cleanly. |
| `research_data/` (repo root) | Cross-project research corpus | Numbered research docs 00–25 plus specs, `wyrd_runtime/`, partial `src/wyrdforge/` | `DROP — DUPLICATE` (if kept in MindSpark/WYRD copies) **or** `KEEP AS-IS` (if the CLI becomes the single canonical home of this corpus) | Appears in triplicate — repo root, MindSpark, WYRD. The corpus is valuable; three copies are not. Decision pairs with the MindSpark and WYRD rows: whichever of those two is dropped, its `research_data/` copy goes with it. If all three snapshots are dropped, the repo-root copy becomes canonical. `DEFER — NEEDS VOLMARR` on **which home is canonical**, but the *duplication itself* must resolve. |
| `research_data/src/wyrdforge/` | WYRD (partial) | Subset of WYRD's `wyrdforge` — models, runtime, schemas, security, services | `DROP — DUPLICATE` | A partial shadow of the full `WYRD-Protocol-*/src/wyrdforge/`. Divergence risk. No CLI edge. Delete. |
| `ollama/` | Upstream OSS | Full Ollama Go project, unmodified — source of the 681 Go / 185 C++ / 158 CUDA files in the file census | `VENDOR-FREEZE — UPSTREAM` or `DROP — UNUSED` | A vendored Go compiler-heavy project inside a Python CLI repo is a significant burden — it inflates the repository by a large factor, and the CLI calls none of it. **Recommended: drop entirely.** If local-model runtime is wanted later, Ollama is better invoked as an already-installed daemon via `ai/local_providers.py` over HTTP (port 11434) — no vendoring needed. If Volmarr wants to keep the source tree for offline/air-gapped study, it must be pinned to an exact upstream SHA and marked read-only in a vendor manifest. |
| `whisper/` | Upstream OSS | Full OpenAI Whisper package, unmodified | `VENDOR-FREEZE — UPSTREAM` or `DROP — UNUSED` | Same structural argument as Ollama. No CLI edge. `openai-whisper` is pip-installable; if a future `mythic-vibe transcribe` subcommand is wanted, depend on it via `pyproject.toml` rather than vendoring the source. **Recommended: drop.** |
| `chatterbox/` | Upstream OSS | Full Chatterbox TTS package, unmodified | `VENDOR-FREEZE — UPSTREAM` or `DROP — UNUSED` | Same. `DROP — UNUSED` unless a voice-out subcommand is designed. |
| `docs/` | Mixed — mostly MindSpark | `api.md`, `quickstart.md`, `hardware_profiles.md`, `index.md` — mirrors MindSpark's `docs/` tree; `specs/` is dominated by ThoughtForge/Sovereign RAG/TurboQuant documents; `research/data_project_development_resources/` | `EXTRACT SELECTED PIECES` | The CLI needs *its own* `docs/` — the one currently at root is MindSpark's. Proposal: move the MindSpark-specific content into MindSpark's own repo (or into a `reference/mindspark_specs/` folder if kept), and re-populate `docs/` with CLI-only material (`docs/api.md` describing the CLI's commands, `docs/quickstart.md` narrating the ChatGPT Plus workflow, `docs/mythic_source/` as the target of `mythic-vibe import-md`). |
| `scripts/` | Cross-project utility | `build_poetic_edda_masterworks.py`, `compile_edda.py`, `fix_absolute_paths.py`, `parse_arxiv_and_generate.py`, `quality_gate.py` | `EXTRACT SELECTED PIECES` | `parse_arxiv_and_generate.py` is the one active cross-island bridge in the repo (it puts the root on `sys.path` and calls `ai/openrouter.py`) — useful for methodology research, but NSE-flavoured; it could become a `mythic-vibe scholar` subcommand or be moved to a research-scripts sibling repo. `quality_gate.py` and `fix_absolute_paths.py` are generic utilities that may stay as repo-local helpers. The two Edda-builders are NSE content generators; they belong with NSE. |

---

## Register — root-level files

| Path | Origin | Current state | Recommendation | Reasoning |
|---|---|---|---|---|
| `README.md` | MythicVibeCLI (NEW) | Canonical user-facing narrative of the CLI | `KEEP AS-IS` | The product's front door. |
| `LICENSE`, `NOTICE`, `LEGAL-NOTICE.md` | MythicVibeCLI (NEW) | Apache-2.0 license and published privacy stance | `KEEP AS-IS` | Required and authoritative. Note: `pyproject.toml` declares MIT, but the project carries an Apache LICENSE — see the license-discrepancy thread below. |
| `pyproject.toml` | MythicVibeCLI (NEW) | Declares `mythic_vibe_cli` only; license = MIT | `DEFER — NEEDS VOLMARR` | License string `MIT` in pyproject contradicts the Apache-2.0 `LICENSE` file at the repo root. This must be reconciled before any public release. Trivially fixed — just a typo or an early draft — but Volmarr should pick the canonical license and harmonise both sides. |
| `PHILOSOPHY.md` (root) | Mythic-Engineering | Short methodology essay; copies exist inside MindSpark and WYRD | `KEEP AS-IS` at root; `DROP — DUPLICATE` in the subtrees if those subtrees are dropped | The root copy is the canonical one for this repo. |
| `PROJECT_LAWS.md`, `RULES.AI.md`, `CHARACTER_RULES.md`, `INSTRUCTIONS_FOR_AI.md`, `JULS_INSTRUCTIONS.md`, `FILE_AI_IS_NOT_TO_CHANGE.md` | Mythic-Engineering / cross-project | Operational instruction scrolls | `KEEP AS-IS` | These are the protocols the repo runs on. Leave the canonical copies at root; the subtree copies disappear with their parents. |
| `Mystic_Engineering_Protocals1.0.md`, `Mythic_Engineers_Codex.md`, `Ada_Lovelace_Explains_Mythic_Engineering.md`, `practical_mythic_engineering_step_by_step.md`, `Quick_Guide_to_Mythic_Engineering_Vibe_Coding.md` | Mythic-Engineering | Methodology corpus — large essays (170 KB, 88 KB, etc.) | `DEFER — NEEDS VOLMARR` | **The canonical home of this methodology is the `hrabanazviking/Mythic-Engineering` GitHub repo**, which the CLI already syncs from via `mythic_data.py`. Carrying a second copy inside the CLI repo creates a silent split-brain: when the canonical repo advances, this copy will stale. Two futures: **(a)** drop these and let `mythic-vibe import-md` be the single source of truth; **(b)** keep them and accept the maintenance cost of updating two places. `(a)` is the cleaner architectural answer; `(b)` is defensible only if Volmarr wants the CLI repo to *embody* the methodology, not merely reference it. Note also the typo `Mystic` → `Mythic` in the first filename. |
| `Mythic_Engineering_CLI_Design_Ideas_7373y4yj.md` | MythicVibeCLI (NEW) / Mythic-Engineering | 47 KB direct predecessor-notes for this CLI | `KEEP AS-IS` or `MERGE INTO CLI` | This is the CLI's own design substrate. Could be preserved verbatim, or distilled into a cleaner `docs/DESIGN_HISTORY.md` once the CLI is stable. |
| `ABOUT_THE_VIKING_ROLEPLAY.md`, `AI Viking TTRPG Emotional Engine Modeling Theory.md` (178 KB) | NSE | Narrative framing and the foundational emotional-engine treatise | `DEFER — NEEDS VOLMARR` | These belong conceptually with NSE. If `systems/` is excised, these should leave with it. |
| `ARCHITECTURE_STUDY_March-8-2026.md`, `Enhancing Stability, Robustness, and Error-Proofing main.py in Norse Saga Engine Startup Process.md`, `Emotional Engine Integration Plan for Norse Saga Engine.md`, `Emotional_Engine_Integration_Plan_for_Norse_Saga_Engine.md`, `Emotional_Engine_Optimization_Recommendations.md`, `Fate-Weaver_Protocol_Integrating_Emotion,_Destiny,_and_Simulation.md` | NSE | Large NSE-specific study documents | `DROP — UNUSED` in this repo; move to NSE's own documentation tree | None of these describe the Mythic Vibe CLI. `Emotional Engine Integration Plan for Norse Saga Engine.md` and `Emotional_Engine_Integration_Plan_for_Norse_Saga_Engine.md` are **the same document under two filenames** — at minimum one of the two pair-members is `DROP — DUPLICATE` unconditionally. |
| `Building the Yggdrasil Cognitive Architecture in Python_ A Step-by-Step Guide.md`, `building_a_local_knowledge_graph.md`, `YGGDRASIL_MANIFESTO.md` | NSE (Yggdrasil era) | Design essays for the older NSE-era Yggdrasil | `DEFER — NEEDS VOLMARR` | Coupled to the `yggdrasil/` directory decision. If `yggdrasil/` stays, these are its charter; if `yggdrasil/` is excised, these go with it. |
| `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md` | Cross-project ecosystem ref | 55 KB, triplicated at root, in MindSpark, in WYRD | `KEEP AS-IS` at root; `DROP — DUPLICATE` in subtrees | This reads as Volmarr's canonical ecosystem overview. Declare the root copy authoritative; the others disappear with their subtrees. |
| `WORLD_MODELING_SKILL.md` | Cross-project | 19 KB, same triplication pattern | Same as above | Same resolution. |
| `CHARACTER_TEMPLATE_SCHEM.yaml` | NSE | 177 KB YAML — the character schema driving `systems/personality_engine.py` | `DROP — UNUSED` in this repo | Belongs with NSE. No CLI code reads it. |
| `config.yaml` | NSE | 35 KB — header explicitly `Norse Saga Engine Configuration v8.0.0` | `DROP — UNUSED` in this repo | The CLI uses `.mythic-vibe.json` via `ConfigStore`. Carrying an unrelated NSE config file at root is actively confusing to future readers. Belongs in NSE. |
| `debug_router_integration.py`, `diagnostics.py` (19 KB) | NSE | NSE router / diagnostics harness | `DROP — UNUSED` | CLI has no use for these; they belong with NSE. |
| `diagnostics_*.md` (ten paired sidecars), `generate_debugging.py`, `generate_dependencies.py`, `generate_tasks.py` | NSE (Yggdrasil era) | Paired-sidecar documentation generators | `DROP — UNUSED` in this repo | These belong with `yggdrasil/` — they are its documentation convention. Follow whatever decision the `yggdrasil/` directory receives. |
| `install_linux.sh`, `install_windows.bat` | uncertain | Install scripts | `KEEP AS-IS` if they correctly install the CLI; `DROP — UNUSED` otherwise | Verify first that these install `mythic-vibe-cli` specifically, not NSE. If they install NSE, they must leave with NSE. |
| `AI_PYTHON_PROGRAMMING_GUIDES.md`, `PYTHONIC_PATTERNS_FOR_AI.md`, `Gemini's_advice_about_prompting_LLMs.md`, `Good_AI_Models_March-2026.md`, `latest_ai_theories_integration_report.md`, `arxiv_AI_theories_integration_report_March-13-2026.md` | Cross-project reference | Advisory essays | `KEEP AS-IS` or move to `docs/reference/` | Useful as ambient reference for the methodology. Tidy into a `docs/reference/` folder so they do not crowd the root. |
| `arxiv_all_papers.json`, `arxiv_papers.json`, `arxiv_results.json`, `relevant_papers.json` | Cross-project research | Scraped arXiv metadata | `EXTRACT SELECTED PIECES` | Three overlapping arXiv JSON dumps at root is excess. Keep one canonical copy (likely `relevant_papers.json`, the curated subset), drop the others. If the research pipeline is live, move the data file into `data/` and document its producer (`scripts/parse_arxiv_and_generate.py`). |
| `example_html_to_get_ideas_for_style.html` | uncertain | Style reference | `DROP — UNUSED` | 45 KB stray reference file with no integration point. |
| `IMG_0407.jpeg` | Cross-project shared asset | Triplicated | `DROP — DUPLICATE` at root if it is README-referenced from a subtree; otherwise `KEEP AS-IS` if the CLI's README uses it | Root-level imagery should only live at root if the root `README.md` references it. Verify. |
| `Viking_Apache_V2_1.jpg` | MythicVibeCLI (NEW) | Repo cover image | `KEEP AS-IS` | Assumed README-referenced. |
| `TASK_exploration.md` | MythicVibeCLI (NEW) | Charter for this exploration pass | `KEEP AS-IS` for now; eventually archive into `docs/history/` once exploration closes | The charter that produced this register. |
| `INVENTORY.md`, `ORIGINS.md`, `DEVLOG.md`, `MAP.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`, `DATA_FLOW.md`, `RECOMMENDATIONS.md` | MythicVibeCLI (NEW — exploration pass) | The seed-chronicle of the exploration phase, authored by Runa's hands (Védis and Eirwyn) | `KEEP AS-IS` | These *are* the living record of the gathering-hall phase. Integration work should add to them, not replace them. |

---

## Threads that only Volmarr can untangle

Five decisions sit upstream of almost every row above. They are not complex, but they are his to make. Until they are made, the register cannot tighten further.

1. **Is this CLI ever going to *run* local models, or is it a scaffolder + Codex-bridge only?**
   - If "yes, run local models": `ai/` keeps `local_providers.py`, a `mythic-vibe run` subcommand is added, `ollama/` stays vendored-and-frozen *or* is depended upon externally.
   - If "no, scaffolder only": `ai/`, `ollama/`, `whisper/`, `chatterbox/` all go. The CLI stays pure. This is the cleaner story.
2. **Which Yggdrasil survives — the NSE-era cognitive router (`yggdrasil/`) or the WYRD ECS Yggdrasil (`wyrdforge/ecs/yggdrasil.py`)?** These are *not* the same design. They share a name and nothing else. Védis's forthcoming `YGGDRASIL_COMPARISON.md` will diagram the contrast; my recommendation is that the CLI repo should hold **at most one** of them, and probably neither — both belong in their own respective project repos.
3. **Are MindSpark and WYRD *incorporated into* this repo as sibling packages, or are they *referenced from* this repo as external installs?**
   - Incorporated: big maintenance surface, one-repo-rules-all, slow release cadence.
   - Referenced: clean boundaries, each project evolves independently, CLI integrates via pip dependencies when a real edge is wanted.
   - The incorporated path has been started-but-not-completed here (snapshots sit dormant with no install edges). The referenced path is the more mature of the two choices.
4. **Does the CLI repo *embody* the Mythic Engineering methodology, or *reference* it?**
   - Currently it does both: the canonical methodology lives at `hrabanazviking/Mythic-Engineering` (the CLI syncs from it), and a full copy also sits at this repo's root. Pick one.
5. **License.** `pyproject.toml` says MIT. `LICENSE` says Apache-2.0. Pick one and harmonise. Trivial to resolve, mandatory before public release.

---

## Suggested sequence of motion (non-binding)

If Volmarr wishes to act on this register in stages, an order that minimises risk:

1. **Resolve the cheap, unambiguous cleanups first.** Delete the empty MindSpark nested shell (`mindspark_thoughtform/MindSpark_ThoughtForge/`). Delete the duplicated Emotional Engine Integration Plan (one filename, keep the other). Delete the partial `research_data/src/wyrdforge/` shadow. Harmonise the license. These cost nothing.
2. **Decide the scope question** (1 above: does the CLI run models?). That single decision removes or keeps `ai/`, `ollama/`, `whisper/`, `chatterbox/` together.
3. **Decide the incorporation question** (3 above: is MindSpark/WYRD part of this repo or external?). That removes or keeps the two largest subtrees together.
4. **Apply the canonical-home rule.** For every file that is triplicated across root / MindSpark / WYRD, declare the root copy canonical and let the duplicates leave with their parents when (3) resolves.
5. **Write `docs/` for the CLI itself** to replace the inherited MindSpark docs tree.
6. **Refine `pyproject.toml`** if `ai/` or any other subtree is promoted into the installed package.

---

## Closing

This register is not a verdict. It is a set of proposals weighed against the CLI's declared scope, with the honest admission that five decisions rest upstream of it. When those five are settled, most of the deferred rows collapse into clean `KEEP` or `DROP` calls, and the repository will become what it is trying to be: a small, coherent Mythic Vibe CLI with a preserved record of where it came from.

May the hall be tidied with the same care with which it was filled.

_End of register._
