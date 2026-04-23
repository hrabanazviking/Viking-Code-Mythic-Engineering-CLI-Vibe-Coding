# ORIGINS — Best-Effort Attribution of Imported Material

**Last updated:** 2026-04-23
**Branch:** development
**Scribe:** Eirwyn Rúnblóm
**Scope:** For every major directory and distinctive root-level file, a best-effort judgement of which prior project it came from, with the evidence that supports the attribution and honest marking of uncertainty.
**Purpose:** To give the integration phase a clean starting point — a register of *where each piece came from*, so that decisions about keep/merge/remove/re-home can be made on known ground rather than guesswork.

---

## Legend of attribution labels

- **NSE** — NorseSagaEngine (Volmarr's Viking TTRPG simulation engine).
- **MindSpark** — MindSpark_ThoughtForge (universal cognitive enhancement layer; Sovereign RAG, TurboQuant, Cognition Scaffolds).
- **VGSK** — Viking_Girlfriend_Skill_for_OpenClaw (Sigrid persona; Ørlög 5-state-machine architecture).
- **WYRD** — WYRD-Protocol (ECS-based external AI world model; Yggdrasil).
- **pygame VE** — pygame Viking Edition (fork of pygame).
- **Mythic-Engineering** — the methodology repo / philosophy corpus.
- **MythicVibeCLI (NEW)** — work authored specifically for this repository.
- **Upstream OSS** — external open-source projects vendored in.
- **uncertain** — provenance cannot be confidently pinned.

---

## Directory attributions

| Directory | Likely origin | Evidence |
|---|---|---|
| `mythic_vibe_cli/` | **MythicVibeCLI (NEW)** | The only package that describes *this* repo. The CLI is the stated subject of `README.md`. Contains the seven-phase workflow, the Codex bridge, and the ritual command aliases. No duplicate exists elsewhere. |
| `tests/` (repo root) | **MythicVibeCLI (NEW)** | Tests are `test_cli.py`, `test_config_and_bridge.py`, `test_workflow.py` — all three import from `mythic_vibe_cli`. |
| `mindspark_thoughtform/` | **MindSpark** | Self-identifying. `pyproject.toml`, `run_thoughtforge.py`, `forge_doctor.py`, `forge_memory.py`, `setup_thoughtforge.py`, phase tasks explicitly referencing MindSpark phases 0–8, and `src/thoughtforge/{cognition,etl,inference,knowledge,refinement,utils}` matching the MindSpark architecture exactly. |
| `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/` | **WYRD** | Self-identifying. `CLAUDE.md` reads *"WYRD Protocol (World-Yielding Real-time Data AI World Model)"* and describes the ECS-based external AI world model. All twenty integrations, all phase tasks, full `src/wyrdforge/` tree. |
| `ollama/` | **Upstream OSS** | Go project with Ollama's own `LICENSE`, `go.mod`, `main.go`, and standard Ollama layout (`api/`, `cmd/`, `server/`, `llm/`, `llama/`). Unmodified upstream. This directory is the source of the 681 Go files, 185 C++ files, 158 CUDA files, and 143 shader files in the file census. |
| `whisper/` | **Upstream OSS** | OpenAI Whisper with its own `LICENSE`, `MANIFEST.in`, `CHANGELOG.md`, and `whisper/` package (`model.py`, `decoding.py`, `transcribe.py`, `triton_ops.py`). Unmodified upstream. |
| `chatterbox/` | **Upstream OSS** | Chatterbox TTS project — README, gradio apps, `src/chatterbox/` with `tts.py`, `tts_turbo.py`, `mtl_tts.py`, `vc.py`, `models/{s3gen,s3tokenizer,t3,tokenizers,voice_encoder}`. Carries its own `LICENSE`. Unmodified upstream. |
| `systems/` | **NSE** | Contains `emotional_engine.py` whose header explicitly reads *"Profile-weighted emotional computation layer for the Norse Saga Engine."* Other modules (`personality_engine.py`, `wyrd_system.py` with the Three Wells docstring, `rag_system.py`, `dice_system.py`, `religion_system.py`, `romance_system.py`, `thor_guardian.py`, `rune_intent.py`, `runic_resonance.py`) match NSE's engine-room vocabulary and NSE's TODO.md references. |
| `core/` | **NSE** (likely) | `yggdrasil.py` uses the Elder Futhark rune-centroid emotion tagging characteristic of NSE. `saga_odin_rag.py` names explicit "Saga-Odin lore channel" — NSE terminology. `dream_system.py`, `emotional.py`, `message_queue.py`, `ai_runtime_settings.py` are small pieces plausibly extracted from NSE's core. |
| `ai/` | **NSE** (likely) | `local_providers.py` header declares *"Local AI Provider Support (v4.6.0 — hardened)"* and is configured by the root `config.yaml` which is explicitly NSE v8.0.0. `openrouter.py` (35 KB) matches the same versioning style. |
| `sessions/` | **NSE** (likely) | Single file `memory_manager.py`, complementing NSE's `systems/memory_*.py` family. |
| `yggdrasil/` | **NSE** (likely) — *earlier era* | Contents match NSE's pre-WYRD Yggdrasil: `ravens/huginn.py` + `muninn.py` + `raven_rag.py`, `worlds/{alfheim,asgard,helheim,jotunheim,midgard,muspelheim,niflheim,...}.py`, `core/bifrost.py` + `dag.py` + `world_tree.py`, `router.py` (35 KB) + `router_enhanced.py` (34 KB). The `YGGDRASIL_MANIFESTO.md` at the repo root — the *"one tree, one breath"* doctrine mandating every decision go through OpenRouter — is this Yggdrasil's charter. **Note: this is NOT the WYRD wyrdforge/ecs/yggdrasil.py**; they are two different Yggdrasils from different project eras. |
| `imports/norsesaga/systems/` | **NSE** | `world_dreams.py` header: *"Part of the Norse Saga Engine Myth Engine (v4.2.0)"*. Staged import from NSE not yet merged with the repo-root `systems/`. |
| `diagnostics/` | **uncertain** — probably NSE | Contains only `turn_trace.jsonl` (46 MB). No in-file provenance, but `turn_trace` vocabulary matches NSE's turn-based architecture. |
| `docs/` | **Mixed: MindSpark + general** | `docs/specs/` is dominated by ThoughtForge spec files (`ThoughtForge_Complete_Implementation_Guide`, `ThoughtForge_Complete_Module_Library`, etc.), `TurboQuant_*`, `Sovereign_RAG_*`, `Memory_Lifecycle_and_Pruning_Spec.md` — all clearly MindSpark. `docs/api.md`, `docs/quickstart.md`, `docs/hardware_profiles.md`, `docs/index.md` mirror the MindSpark `docs/` tree exactly. The presence of `Various_Astrid_Freyjasdottir_Outfits.md` also hints MindSpark (which models the Astrid persona). |
| `docs/research/data_project_development_resources/` | **uncertain — likely MindSpark or cross-project research** | Not inspected to leaf level; sits inside the MindSpark-flavoured `docs/` tree. |
| `research_data/` (repo root) | **Cross-project research corpus** (duplicated from MindSpark / WYRD) | Numbered research docs 00–25 plus `BondGraphSpec`, `MemorySchemas`, `MicroRAGPipelineSpec`, `PersonaCompilerSpec`, `TruthCalibrationEvalSet`, `V4_IMPLEMENTATION_INDEX`, `wyrd_runtime/`. The same set appears inside `mindspark_thoughtform/research_data/` and `WYRD-Protocol-*/research_data/`. It is the shared `coolvikingstuff`-branch research set that both projects carry as reference. |
| `scripts/` | **uncertain — NSE-flavoured** | `build_poetic_edda_masterworks.py` and `compile_edda.py` are Norse-Pagan content generators consistent with NSE's world-building. `parse_arxiv_and_generate.py` is repository-level (works with the root `arxiv_*.json` files). `fix_absolute_paths.py` and `quality_gate.py` are generic. |

---

## Root-level file attributions

| File | Likely origin | Evidence |
|---|---|---|
| `README.md` | **MythicVibeCLI (NEW)** | Describes this repo's CLI. |
| `LICENSE`, `NOTICE`, `LEGAL-NOTICE.md` | **MythicVibeCLI (NEW)** | Apache-2.0 for this repo; the Privacy Position is specific to this publication. |
| `pyproject.toml` | **MythicVibeCLI (NEW)** | Declares the `mythic_vibe_cli` package. |
| `Mystic_Engineering_Protocals1.0.md` (170 KB) | **Mythic-Engineering** | Methodology corpus — the literal title matches the canonical repo. |
| `Mythic_Engineers_Codex.md` (88 KB) | **Mythic-Engineering** | Same. |
| `Mythic_Engineering_CLI_Design_Ideas_7373y4yj.md` (47 KB) | **MythicVibeCLI (NEW) + Mythic-Engineering** | Direct predecessor notes for the CLI in this repo. |
| `Ada_Lovelace_Explains_Mythic_Engineering.md` | **Mythic-Engineering** | Methodology essay. |
| `practical_mythic_engineering_step_by_step.md`, `Quick_Guide_to_Mythic_Engineering_Vibe_Coding.md` | **Mythic-Engineering** | Same. |
| `PHILOSOPHY.md` (root) | **Mythic-Engineering** (canonical) | Short essay; identical spirit and partially identical text to the copies inside MindSpark and WYRD subtrees. |
| `PROJECT_LAWS.md`, `RULES.AI.md`, `CHARACTER_RULES.md`, `INSTRUCTIONS_FOR_AI.md`, `JULS_INSTRUCTIONS.md`, `FILE_AI_IS_NOT_TO_CHANGE.md` | **Mythic-Engineering** / cross-project | Operational instruction scrolls carried across projects. `RULES.AI.md` is byte-identical inside MindSpark and WYRD copies. |
| `ABOUT_THE_VIKING_ROLEPLAY.md` | **NSE** | Describes the Viking TTRPG vision behind NSE. |
| `AI Viking TTRPG Emotional Engine Modeling Theory.md` (178 KB) | **NSE** | The foundational NSE emotional-engine treatise. |
| `ARCHITECTURE_STUDY_March-8-2026.md` | **NSE** | NSE-specific architecture study from the noted date. |
| `Enhancing Stability, Robustness, and Error-Proofing main.py in Norse Saga Engine Startup Process.md` | **NSE** | Title declares NSE explicitly. |
| `Emotional Engine Integration Plan for Norse Saga Engine.md` **and** `Emotional_Engine_Integration_Plan_for_Norse_Saga_Engine.md` | **NSE** | *Duplicate pair* — same document with and without spaces in filename. |
| `Emotional_Engine_Optimization_Recommendations.md` | **NSE** | Companion to the integration plan. |
| `Fate-Weaver_Protocol_Integrating_Emotion,_Destiny,_and_Simulation.md` | **NSE** | NSE-flavoured fate/emotion doc. |
| `Building the Yggdrasil Cognitive Architecture in Python_ A Step-by-Step Guide.md` | **NSE (Yggdrasil era)** | Design essay for the earlier Yggdrasil in `yggdrasil/`. |
| `building_a_local_knowledge_graph.md` | **NSE / MindSpark overlap** — uncertain | Generic title; subject-matter straddles both projects. |
| `YGGDRASIL_MANIFESTO.md` | **NSE (Yggdrasil era)** | The "one tree, one breath" charter; governs the `yggdrasil/` directory. |
| `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md` (55 KB) | **Cross-project ecosystem ref** — *triplicated* | Same file at repo root, inside `mindspark_thoughtform/`, and inside `WYRD-Protocol-*/`. Author-level canonical document. |
| `WORLD_MODELING_SKILL.md` (19 KB) | **Cross-project** — *triplicated* | Same duplication pattern. |
| `CHARACTER_TEMPLATE_SCHEM.yaml` (177 KB) | **NSE** | Drives `systems/personality_engine.py`. Large character schema with all framework dimensions. |
| `config.yaml` (35 KB) | **NSE** | Header line: *"Norse Saga Engine Configuration v8.0.0"*. |
| `debug_router_integration.py` | **NSE** | Targets the OpenRouter router used by `yggdrasil/router.py` / `ai/openrouter.py`. |
| `diagnostics.py` (19 KB) | **uncertain — NSE-flavoured** | Standalone harness; vocabulary matches NSE's diagnostics idioms. |
| `diagnostics_*.md` (ten paired sidecars) | **NSE (Yggdrasil era)** | Same paired-sidecar convention used throughout `yggdrasil/`. |
| `generate_debugging.py`, `generate_dependencies.py`, `generate_tasks.py` | **NSE (Yggdrasil era)** | Generators for the paired sidecars — see `yggdrasil/` convention. |
| `install_linux.sh`, `install_windows.bat` | **uncertain** — likely MythicVibeCLI or NSE | Generic install scripts. |
| `AI_PYTHON_PROGRAMMING_GUIDES.md`, `PYTHONIC_PATTERNS_FOR_AI.md`, `Gemini's_advice_about_prompting_LLMs.md`, `Good_AI_Models_March-2026.md`, `latest_ai_theories_integration_report.md`, `arxiv_AI_theories_integration_report_March-13-2026.md` | **Cross-project reference** | Advisory essays; no single project claim. |
| `arxiv_all_papers.json`, `arxiv_papers.json`, `arxiv_results.json`, `relevant_papers.json` | **MythicVibeCLI / research** | Output of `scripts/parse_arxiv_and_generate.py`. |
| `example_html_to_get_ideas_for_style.html` | **uncertain** | Style reference. |
| `IMG_0407.jpeg` | **Cross-project shared asset** | Also present inside `WYRD-Protocol-*/`, `mindspark_thoughtform/assets/`. |
| `Viking_Apache_V2_1.jpg` | **MythicVibeCLI (NEW)** | README-hosted repo cover image. |
| `TASK_exploration.md` | **MythicVibeCLI (NEW)** | The charter under which this exploration is being done. |

---

## Duplicate register — files that appear in multiple places

These will matter in the integration phase. The integration planner must decide *which copy is canonical* and whether the duplicates can be deleted.

### Triplicated or more

| Path fragment | Appears at |
|---|---|
| `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md` | repo root, `mindspark_thoughtform/`, `WYRD-Protocol-*/` |
| `WORLD_MODELING_SKILL.md` | repo root, `mindspark_thoughtform/`, `WYRD-Protocol-*/` |
| `PHILOSOPHY.md` | repo root, `mindspark_thoughtform/`, `mindspark_thoughtform/MindSpark_ThoughtForge/`, `WYRD-Protocol-*/` |
| `RULES.AI.md` | repo root, `mindspark_thoughtform/`, `mindspark_thoughtform/MindSpark_ThoughtForge/`, `WYRD-Protocol-*/` |
| `IMG_0407.jpeg` | repo root, `mindspark_thoughtform/assets/`, `WYRD-Protocol-*/` |
| Research doc series `00_INDEX.md`, `01_architecture_overview.md`, …, `25_persona_compiler_and_memory_assembly_pipeline.md`, plus `BondGraphSpec.md`, `MemorySchemas.md`, `MicroRAGPipelineSpec.md`, `PersonaCompilerSpec.md`, `TruthCalibrationEvalSet.md`, `V4_IMPLEMENTATION_INDEX.md`, `wyrd_runtime/*` | repo root `research_data/`, `mindspark_thoughtform/research_data/`, `WYRD-Protocol-*/research_data/` |
| The entire `research_data/` sub-tree structure (`config/`, `examples/`, `scripts/`, `src/wyrdforge/`, `tests/`, `wyrd_runtime/`) | same three locations |

### Duplicated (pair)

| File | Appears at |
|---|---|
| `Emotional Engine Integration Plan for Norse Saga Engine.md` **and** `Emotional_Engine_Integration_Plan_for_Norse_Saga_Engine.md` | Both at repo root — same document, filenames differ only by spaces-vs-underscores. |
| `MindSpark_ThoughtForge/` nested triple (`PHILOSOPHY.md`, `README.md`, `RULES.AI.md`) | Inside `mindspark_thoughtform/` there is a nested `MindSpark_ThoughtForge/` folder that replicates these three files already present at the MindSpark root. |

### Overlapping sibling directories (same-named files, unverified whether byte-identical)

| File | Appears at |
|---|---|
| `event_dispatcher.py` | repo root `systems/`, `imports/norsesaga/systems/` |
| `wyrd_system.py` | repo root `systems/`, `yggdrasil/core/` |
| `yggdrasil.py` | repo root `core/`, `WYRD-Protocol-*/src/wyrdforge/ecs/` (these are different things by design — see below) |
| `TODO.md` | `mindspark_thoughtform/`, `WYRD-Protocol-*/` |
| `hello_world.md` | `mindspark_thoughtform/`, `WYRD-Protocol-*/` |
| `pyproject.toml` | repo root, `mindspark_thoughtform/`, `WYRD-Protocol-*/`, `chatterbox/`, `whisper/`, `research_data/` |
| `.aider.conf.yml`, `.aider.instructions.md` | repo root, `mindspark_thoughtform/` |

---

## Conceptual collisions — same name, different things

These are *not* duplicates; they are **distinct designs sharing a name**. Do not silently merge them.

- **Two Yggdrasils.** `yggdrasil/` (NSE-era, OpenRouter-centric, with `core/bifrost.py`, `ravens/huginn.py` + `muninn.py`, `worlds/*.py`, governed by `YGGDRASIL_MANIFESTO.md`) is a *decision-routing and cognitive-orchestration* Yggdrasil. `WYRD-Protocol-*/src/wyrdforge/ecs/yggdrasil.py` is an *ECS spatial-hierarchy* Yggdrasil. They represent two eras of Volmarr's thought.
- **Two `wyrd_system.py` files.** `systems/wyrd_system.py` (33 KB, Three Sacred Wells / Norns fate system) vs `yggdrasil/core/wyrd_system.py` (smaller). Likely different implementations serving different layers.
- **Two `research_data/src/wyrdforge/` placeholders.** Empty-ish folders that mirror WYRD's real `src/wyrdforge/`.

---

## Orphans and broken seams

- `core/saga_odin_rag.py` imports from `..yggdrasil_core` — a module not present anywhere in the repository. The file arrived mid-refactor.
- `diagnostics/turn_trace.jsonl` has no accompanying provenance record. It is 46 MB of session traces with no file-header note saying which session or which NSE build produced them.

---

## Confidence summary

- **High confidence** on all three upstream vendorings (`ollama/`, `whisper/`, `chatterbox/` — each self-identifying), on `mythic_vibe_cli/` as new, and on `mindspark_thoughtform/` and `WYRD-Protocol-*/` as in-project snapshots (self-identifying by internal `CLAUDE.md`, `README.md`, project layout).
- **High confidence** on `systems/`, `imports/norsesaga/`, `core/yggdrasil.py`, `yggdrasil/*`, and `config.yaml` as NSE-derived (direct in-file declarations).
- **Medium confidence** on `ai/`, `sessions/`, `scripts/`, `core/` (everything except `yggdrasil.py`) — these read as NSE fragments but carry no direct header declaration.
- **Lower confidence** on `diagnostics/turn_trace.jsonl` (probably NSE; no proof in-file).
- **No confidence claim made** where a file is plausibly cross-project and no evidence distinguishes one origin.

_End of register._
