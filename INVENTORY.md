# INVENTORY — The Narrative Scroll of What Is Here

**Last updated:** 2026-04-23
**Branch:** development
**Scribe:** Eirwyn Rúnblóm
**Scope:** Every major directory and notable root-level file in the repository `Viking-Code-Mythic-Engineering-CLI-Vibe-Coding`, described in its current untouched form.
**Purpose:** A refined reference scroll. Anyone opening this six months hence should be able to understand what was preserved, what each part currently does, and where in the hall to look.

---

## Preamble

Volmarr has populated this repository with material drawn from a constellation of prior projects — NorseSagaEngine (NSE), MindSpark ThoughtForge, Viking Girlfriend Skill for OpenClaw (VGSK), the WYRD Protocol, and several upstream open-source vendorings (ollama, whisper, chatterbox). Around all of that sits the genuinely new work: the Mythic Vibe CLI itself, a beginner-friendly vibe-coding harness aligned to the Mythic Engineering method. The repository therefore reads as a **living archive with a new CLI at its centre** — not yet a reconciled product, but a gathering-place before integration.

Cross-reference Védis Eikleið's structural maps (`MAP.md`, `ARCHITECTURE.md`, `DEPENDENCIES.md`, `DATA_FLOW.md`) for the complementary diagrammatic view. This scroll is narrative.

---

## Root-level files of note

A handful of files at the repository root deserve individual mention before the directory walk.

- **`README.md`** — the public face: describes the Mythic Vibe CLI, the `mythic-vibe init / checkin / codex-pack / codex-log / status / doctor / sync / method` command set, the ChatGPT Plus / Codex copy-paste bridge workflow, and the ritual command aliases (`imbue`, `evoke`, `scry`, `weave`, `prune`, `heal`, `oath`, `grimoire`). States Apache 2.0 license and the privacy position.
- **`LICENSE`** — Apache License, Version 2.0.
- **`NOTICE`** and **`LEGAL-NOTICE.md`** — attribution and the author's published distribution / privacy stance (no age-gate, no ID collection required to use source).
- **`PHILOSOPHY.md`** — short (but literal-escape-peppered) statement of the Modern Viking ethos: frith, honor, open knowledge, vibe coding, synthesis of spirit and technology. Identical in spirit to the `PHILOSOPHY.md` carried inside `mindspark_thoughtform/` and `WYRD-Protocol-*/`.
- **`PROJECT_LAWS.md`**, **`RULES.AI.md`**, **`CHARACTER_RULES.md`**, **`INSTRUCTIONS_FOR_AI.md`**, **`JULS_INSTRUCTIONS.md`**, **`FILE_AI_IS_NOT_TO_CHANGE.md`** — operational instruction documents for AI collaborators. `RULES.AI.md` (20 KB) is the canonical ruleset and is duplicated verbatim into MindSpark and WYRD subdirectories.
- **`Mystic_Engineering_Protocals1.0.md`** (170 KB), **`Mythic_Engineers_Codex.md`** (88 KB), **`Mythic_Engineering_CLI_Design_Ideas_7373y4yj.md`** (47 KB), **`Ada_Lovelace_Explains_Mythic_Engineering.md`** (12 KB), **`practical_mythic_engineering_step_by_step.md`**, **`Quick_Guide_to_Mythic_Engineering_Vibe_Coding.md`** — the Mythic Engineering methodology corpus. Theory, method, ritual command design.
- **`ABOUT_THE_VIKING_ROLEPLAY.md`** (12 KB) — narrative framing of the Viking TTRPG vision.
- **`AI Viking TTRPG Emotional Engine Modeling Theory.md`** (178 KB) — the large theoretical treatise underpinning the NSE emotional engine. The single biggest document in the repo.
- **`ARCHITECTURE_STUDY_March-8-2026.md`** (29 KB), **`Enhancing Stability, Robustness, and Error-Proofing main.py in Norse Saga Engine Startup Process.md`** (34 KB), **`Emotional Engine Integration Plan for Norse Saga Engine.md`** + **`Emotional_Engine_Integration_Plan_for_Norse_Saga_Engine.md`** (the same plan in two spellings), **`Emotional_Engine_Optimization_Recommendations.md`**, **`Fate-Weaver_Protocol_Integrating_Emotion,_Destiny,_and_Simulation.md`** — the NSE architecture / integration study corpus.
- **`Building the Yggdrasil Cognitive Architecture in Python_ A Step-by-Step Guide.md`** (46 KB), **`building_a_local_knowledge_graph.md`** (54 KB), **`YGGDRASIL_MANIFESTO.md`** — design essays for the Yggdrasil cognitive layer; the Manifesto declares the "one tree, one breath" rule that all decision-making scripts must call the OpenRouter API.
- **`Technical_Architecture_of_Volmarrs_AI_Ecosystem.md`** (55 KB) — the ecosystem-wide architecture reference. Appears at the root and is duplicated inside `mindspark_thoughtform/`, `WYRD-Protocol-*/`. This file acts as the connective overview across all the imported sub-projects.
- **`WORLD_MODELING_SKILL.md`** (19 KB) — world-model skill specification; also duplicated inside MindSpark and WYRD trees.
- **`CHARACTER_TEMPLATE_SCHEM.yaml`** (177 KB) — the large character schema that drives the personality engine. A single YAML document defining every psychological, cultural, and spiritual dimension the engine can read.
- **`config.yaml`** (35 KB) — the runtime configuration. Its header explicitly says *"Norse Saga Engine Configuration v8.0.0"*; it catalogues OpenRouter models, local AI providers, and system toggles. This is NSE's live config imported wholesale.
- **`debug_router_integration.py`** (10 KB) and **`diagnostics.py`** (19 KB) — diagnostic / router-testing entry points. The latter is a fully standalone diagnostics harness.
- **`diagnostics_*.md`** — a family of small paired markdown files (`AI_HINTS`, `DEBUGGING`, `DEPENDENCIES`, `EXAMPLES`, `INTERFACE`, `METRICS`, `PATTERNS`, `PROMPTS`, `README_AI`, `TASKS`, `TESTS`) following the Yggdrasil-style auto-documentation convention.
- **`generate_debugging.py`**, **`generate_dependencies.py`**, **`generate_tasks.py`** — generators for the paired AI-companion markdown sidecars seen throughout `yggdrasil/`.
- **`install_linux.sh`** and **`install_windows.bat`** — install scripts.
- **`pyproject.toml`** — the project's Python build manifest; packages the `mythic_vibe_cli` module.
- **`Gemini's_advice_about_prompting_LLMs.md`**, **`Good_AI_Models_March-2026.md`**, **`AI_PYTHON_PROGRAMMING_GUIDES.md`** (16 KB), **`PYTHONIC_PATTERNS_FOR_AI.md`** (16 KB), **`latest_ai_theories_integration_report.md`**, **`arxiv_AI_theories_integration_report_March-13-2026.md`** — advisory / reference essays.
- **`arxiv_all_papers.json`** (77 KB), **`arxiv_papers.json`**, **`arxiv_results.json`**, **`relevant_papers.json`** (67 KB) — scraped arXiv metadata, presumably fed to `scripts/parse_arxiv_and_generate.py`.
- **`example_html_to_get_ideas_for_style.html`** (45 KB) — a stylistic HTML reference.
- **`IMG_0407.jpeg`** (382 KB), **`Viking_Apache_V2_1.jpg`** (466 KB) — project imagery used in the README.
- **Tooling dotfiles:** `.aider.conf.yml`, `.aider.instructions.md`, `.clinerules`, `.rooignore`, `.roomodes`, `.roorules`, `.claude/`, `.roo/`, `.gitignore`, `.gitkeep`. The repository is configured to welcome several AI coding assistants simultaneously.
- **`TASK_exploration.md`** — the charter under which Védis and I are presently working.

---

## Directory walk

### `ai/`

Two standalone Python files — `local_providers.py` (23 KB) and `openrouter.py` (35 KB). Hardened client wrappers for local LLM backends (Ollama, LM Studio, OpenAI-compatible) and for OpenRouter. The local providers module identifies itself as *"v4.6.0 — hardened"* with jittered backoff, defensive JSON parsing, auto-reconnect, input sanitisation, and a safe model-list. These are the connective tissue between the Norse-Saga-flavoured cores elsewhere in the repo and the actual LLM services.

### `chatterbox/`

A full upstream vendoring of the Chatterbox TTS project — README, example scripts (`example_tts.py`, `example_tts_turbo.py`, `example_vc.py`, `example_for_mac.py`), multiple Gradio app launchers, marketing PNG/JPG, MIT LICENSE, `pyproject.toml`, and `src/chatterbox/` containing the real model code (`tts.py`, `tts_turbo.py`, `mtl_tts.py`, `vc.py`, plus `models/` with `s3gen`, `s3tokenizer`, `t3`, `tokenizers`, `voice_encoder`). Untouched upstream library intended to supply voice synthesis to the ecosystem.

### `core/`

Six small Python modules — the leanest directory of "new" original logic:

- `ai_runtime_settings.py` — runtime settings / feature flags.
- `dream_system.py` (9.6 KB) — between-turn dream generation.
- `emotional.py` (8.4 KB) — compact emotional layer.
- `message_queue.py` — a basic message queue.
- `saga_odin_rag.py` — a RAG pipeline for a Saga-to-Odin "lore channel," with a hard-coded SRD condition lookup that injects combat/status lore when the query mentions specific terms. Imports from `..yggdrasil_core` — a module *not* present in the repo, which marks this file as partially orphaned.
- `yggdrasil.py` (2.6 KB) — rune-tagging of emotion vectors against the twenty-four Elder Futhark centroids, and an `add_memory_node` stub whose storage is left as a comment.

These read as small Core building blocks extracted from NSE's innards.

### `diagnostics/`

Contains a single file: **`turn_trace.jsonl` (46 MB)** — a very large JSONL log of turn traces. The only data artefact in this subtree. Likely a captured NSE session log retained for diagnostic replay.

### `docs/`

Public documentation in a `mkdocs`-friendly shape.

- `index.md`, `quickstart.md`, `api.md`, `hardware_profiles.md` — top-level doc pages.
- `docs/research/data_project_development_resources/` — a research sub-folder.
- `docs/specs/` — a large, rich design-specs folder: `Algorithms_and_Pseudocode_Spec.md`, `Alternative_Knowledge_Graphs.md`, `Data_Structures_Spec.md`, `GALDRABOK_PREFACE.md`, `Master_Game_Plan_Roadmap.md`, `Memory_Guided_Cognition_Resources.md`, `Memory_Lifecycle_and_Pruning_Spec.md`, `Production_Ready_Implementation_Package.md`, `Prompt_Templates_Spec.md`, `Retrieval_and_Scoring_Spec.md`, `Sovereign_RAG_Brainstorming.md`, `Sovereign_RAG_Technical_Overview.md`, `SQL_RAG_Memory_Enforced_Cognition.md`, `The_Heathen_Third_Path_Essay.md`, `The_Heathen_Third_Path_Overview.md`, `ThoughtForge_Complete_Implementation_Guide.md`, `ThoughtForge_Complete_Module_Library.md`, `ThoughtForge_Complete_System_Library_v1.md` and `_v2.md`, `ThoughtForge_Full_Expanded_Implementation.md`, `ThoughtForge_Full_Implementation_Package.md`, `ThoughtForge_Implementation_Game_Plan_Draft1.md`, `TurboQuant_Cognition_Blueprint.md`, `TurboQuant_Guided_Memory_Cognition.md`, `Various_Astrid_Freyjasdottir_Outfits.md`, `Warding_of_Huginns_Well.md`, `Wikidata_ETL_Pipeline.md`.

The specs folder reads overwhelmingly as MindSpark ThoughtForge specification material lifted into the top-level docs shelf.

### `imports/`

Currently holds a single sub-project, `imports/norsesaga/systems/`, with three Python files: `event_dispatcher.py`, `world_dreams.py` (whose header explicitly reads *"Part of the Norse Saga Engine Myth Engine (v4.2.0)"*), and `world_will.py`. Seems to be the chosen place for staging imports from NSE that are not yet reconciled with the repo-root `systems/` directory.

### `mindspark_thoughtform/`

A near-complete snapshot of the **MindSpark ThoughtForge** project, reproduced in full:

- Repo-level scaffolding: `.aider.conf.yml`, `.aider.instructions.md`, `.dockerignore`, `.github/`, `.gitignore`, `Dockerfile`, `docker-compose.yml`, `mkdocs.yml`, `pyproject.toml`, `requirements.txt`, `setup.py`, `CHANGELOG.md`, `CONTRIBUTING.md`, `MODEL_CARD.md`, `README.md`.
- Methodology: `PHILOSOPHY.md`, `RULES.AI.md`, `BUILD_PLAN_v1.md`.
- Top-level scripts: `forge_doctor.py`, `forge_memory.py`, `locustfile.py`, `run_thoughtforge.py`, `setup_thoughtforge.py` (28 KB).
- Phase task files: `TASK_PHASE0_SETUP.md`, `TASK_PHASE3_COGNITION.md`, `TASK_PHASE4_SALVAGE.md`, `TASK_PHASE5_DEPLOYMENT.md`, `TASK_PHASE6_RELEASE.md`, `TASK_PHASE7_SETUP_WIZARD.md`, `TASK_PHASE8_ROBUSTNESS.md`.
- `assets/` — project imagery and a video.
- `benchmarks/` — `benchmark_profiles.py`, `persona_consistency.py`.
- `configs/` — `default.yaml`, `personality_core.yaml`, `user_config.yaml`.
- `data/` — a rich Viking knowledge corpus: Authentic Norse Religious Practices, Norse Gods and Goddesses training pairs, Poetic Edda, viking values, viking honour, viking frith, viking sailing/trade/raiding, voluspa, legendary vikings, and more — both `.json`, `.jsonl`, and `.yaml` forms, plus a `knowledge_reference/` subfolder.
- `docs/` — `api.md`, `hardware_profiles.md`, `index.md`, `quickstart.md`, `research/`, `specs/` (mirrors the root-level `docs/specs/` content).
- `hardware_profiles/` — `desktop_cpu.json`, `desktop_gpu.json`, `phone_low.json`, `pi_5.json`, `pi_zero.json`, `server_gpu.json`.
- `MindSpark_ThoughtForge/` — a small nested triple of `PHILOSOPHY.md`, `README.md`, `RULES.AI.md` (appears to be a redundant inner copy).
- `research_data/` — a full copy of the 00–25 numbered research docs plus `BondGraphSpec.md`, `MemorySchemas.md`, `MicroRAGPipelineSpec.md`, `PersonaCompilerSpec.md`, `TruthCalibrationEvalSet.md`, `V4_IMPLEMENTATION_INDEX.md`, `wyrd_runtime/` packet docs — identical set to the one at the top-level `research_data/` (see Duplicates).
- `scripts/` — installers for linux, mac, pi, termux, windows.
- `src/thoughtforge/` — **the real engine code**:
  - `cognition/`: `chat_history.py`, `core.py`, `prompt_builder.py`, `router.py`, `scaffold.py`.
  - `etl/`: `db_integrity.py`, `embeddings.py`, `schema.py`, `sources.py`, `subset.py`, `wikidata.py`.
  - `inference/`: `backends.py`, `hf_backend.py`, `lmstudio_backend.py`, `model_browser.py`, `ollama_backend.py`, `onnx_export.py`, `profiles.py`, `turboquant.py`, `turboquant_backend.py`, `unified_backend.py`.
  - `knowledge/`: `forge.py`, `lifecycle.py`, `models.py`, `scoring.py`, `store.py`.
  - `refinement/`: `enforcement.py`, `salvage.py`.
  - `utils/`: `config.py`, `health.py`, `logging_setup.py`, `paths.py`, `perf.py`, `retry.py`, `self_heal.py`.
- `tests/` — phase-aligned test files: `test_phase1_knowledge.py` through `test_phase8_perf.py` covering knowledge, inference, cognition, refinement, deployment, adversarial, release, backends, chat, errors, health, performance.
- `TODO.md`, `hello_world.md`, `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md` (duplicated at root), `WORLD_MODELING_SKILL.md` (duplicated at root).

A complete, self-contained ThoughtForge installation, staged intact inside the new repo.

### `mythic_vibe_cli/`

The **new work at the centre of this repository** — the Mythic Vibe CLI package. Small and purposeful:

- `__init__.py` (version constant).
- `cli.py` (20 KB) — the argparse entry with subcommands `init`, `start`, `checkin`, `status`, `import-md`, `codex-pack`, `codex-log`, `sync`, `method`, `doctor`, plus the ritual aliases (`imbue`, `evoke`, `scry`, `weave`, `prune`, `heal`, `oath`, `grimoire`, `config set`, `db migrate`).
- `codex_bridge.py` (5.4 KB) — the ChatGPT-Plus / Codex copy-paste packet generator.
- `config.py` (3.2 KB) — layered config resolver (global, XDG, project).
- `mythic_data.py` (4.4 KB) — `MethodStore`, holding Mythic Engineering method notes.
- `workflow.py` (13 KB) — the core scaffold: defines the seven phases `intent → constraints → architecture → plan → build → verify → reflect`; emits the starter documents (`PHILOSOPHY.md`, `ARCHITECTURE.md`, `DOMAIN_MAP.md`, `DATA_FLOW.md`, `DEVLOG.md`, `tasks/current_GOALS.md`, `mythic/plan.md`, `mythic/loop.md`, `mythic/status.json`, `MYTHIC_ENGINEERING.md`, `SYSTEM_VISION.md`).

This is the only sub-tree in the repository that appears to have been authored specifically *for this repo*. Everything else is imported.

### `ollama/`

A complete upstream vendoring of **Ollama** — the Go-language LLM server. The entire top-level is Ollama's own layout: `api/`, `app/`, `auth/`, `cmd/`, `convert/`, `discover/`, `docs/`, `envconfig/`, `format/`, `fs/`, `harmony/`, `integration/`, `internal/`, `kvcache/`, `llama/`, `llm/`, `logutil/`, `manifest/`, `middleware/`, `ml/`, `model/`, `openai/`, `anthropic/`, `parser/`, `progress/`, `readline/`, `runner/`, `sample/`, `scripts/`, `server/`, `template/`, `thinking/`, `tokenizer/`, `tools/`, `types/`, `version/`, `x/`, plus `main.go`, `CMakeLists.txt`, `Dockerfile`, `go.mod`, `go.sum`, `Makefile.sync`, `MLX_VERSION`, `README.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`. This is what supplies the 681 Go files, the 185 C++ files, the 158 CUDA files, and the 143 shaders noted in the file census. Untouched upstream.

### `research_data/`

At the repo root, a complete copy of Volmarr's research-doc series 00–25 (architecture overview, memory architecture patterns, system prompt engineering, tool system architecture, theory of mind, agent security, sandboxing, personality companion system, hooks/skills/plugins, swarm architecture, memory lifecycle, theory of mind personality, world model belief graph, cyber viking applications, theory of mind inference, agent security attack taxonomy, Rust runtime deep dive, MCP protocol, permission classifier, API streaming/caching/cost, eval red team, config settings/feature flags, project branches, Norse mythology data structures, original theories, AI companion psychology, build sequence v2, local model integration, small-model scaffolding, cybersecurity patterns, personality lattice, prompt engineering cookbook, symbolic memory, relationship continuity / bond model, WYRD protocol ECS worldmodel, Orlog engine full design, scene director / emotional presence, memory compression distillation, NSE agent architecture, MindSpark phase 7/8 architecture, multi-scale retrieval / micro-RAG, master synthesis reference, truth calibration, persona compiler). Accompanied by `BondGraphSpec.md`, `MemorySchemas.md`, `MicroRAGPipelineSpec.md`, `PersonaCompilerSpec.md`, `TruthCalibrationEvalSet.md`, `V4_IMPLEMENTATION_INDEX.md`, `README.md`, `README_V5_IMPLEMENTATION.md`, `pyproject.toml`, plus `config/`, `examples/`, `scripts/`, `src/wyrdforge/` (empty-ish placeholder), `tests/` (two tests), and `wyrd_runtime/` (five runtime packet docs: index, session manager, engine wiring, prompt builder, drop-in runtime module).

The same directory appears in three places — repo root, inside `mindspark_thoughtform/`, and inside `WYRD-Protocol-*/` — with essentially identical content.

### `scripts/`

Five small Python scripts: `build_poetic_edda_masterworks.py` (7 KB), `compile_edda.py` (3.5 KB), `fix_absolute_paths.py` (1.7 KB), `parse_arxiv_and_generate.py` (2.7 KB), `quality_gate.py` (2.3 KB). Utility generators for content compilation and QA.

### `sessions/`

One file: `memory_manager.py` (16 KB). Session-memory management extracted from a larger system.

### `systems/`

The largest concentration of **pure engine code** at the repo root — 28 Python modules totalling ~500 KB. These are the NSE systems lifted up:

- `context_optimizer.py`, `crash_reporting.py`, `data_system.py` (24 KB), `dice_system.py` (33 KB), `emotional_engine.py` (30 KB, described as "profile-weighted emotional computation layer for the Norse Saga Engine"), `enhanced_memory.py` (37 KB), `event_dispatcher.py`, `housekeeping.py` (37 KB), `local_servers.py`, `location_ai_manager.py`, `memory_hardening.py`, `memory_query_engine.py`, `memory_retrieval.py`, `memory_system.py`, `personality_engine.py` (80 KB — the largest single file, a 20-framework psychological profile derivation), `prompt_budgeter.py`, `rag_system.py` (35 KB), `religion_system.py`, `romance_system.py`, `rune_intent.py`, `runic_resonance.py`, `stress_system.py`, `thor_guardian.py`, `unified_memory_facade.py`, `user_services.py`, `voice_bridge.py` (29 KB), `wyrd_system.py` (33 KB — the Three Wells / Norns fate system), `wyrd_tethers.py`.

This is NSE's engine room, in its live v4+ form.

### `tests/`

Four files scoped to the Mythic Vibe CLI: `__init__.py`, `test_cli.py`, `test_config_and_bridge.py`, `test_workflow.py`. The only tests that cover the repo's new work (the CLI itself); the imported sub-projects carry their own test suites within their own directories.

### `whisper/`

A full upstream vendoring of OpenAI's **Whisper** speech-to-text project — `.flake8`, `.github/`, `.pre-commit-config.yaml`, `CHANGELOG.md`, `LICENSE`, `MANIFEST.in`, `README.md`, `model-card.md`, `pyproject.toml`, `requirements.txt`, `approach.png`, `language-breakdown.svg`, `data/meanwhile.json`, `notebooks/LibriSpeech.ipynb` and `Multilingual_ASR.ipynb`, `tests/` (audio, normaliser, timing, tokenizer, transcribe tests, plus `jfk.flac`), and `whisper/` package (`__init__.py`, `__main__.py`, `assets/`, `audio.py`, `decoding.py`, `model.py`, `normalizers/`, `timing.py`, `tokenizer.py`, `transcribe.py`, `triton_ops.py`, `utils.py`, `version.py`). Untouched.

### `WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model/`

A near-complete snapshot of the **WYRD Protocol** project:

- Governance: `.github/`, `.gitignore`, `CLAUDE.md`, `PHILOSOPHY.md`, `README.md`, `ROADMAP.md` (25 KB), `RULES.AI.md`, `TODO.md`, `mkdocs.yml`, `pyproject.toml`, `requirements.txt`.
- Phase tasks: `TASK_PHASE0_FOUNDATION.md`, `TASK_PHASE1_ECS_CORE.md`, `TASK_PHASE2_PERSISTENT_MEMORY.md`, plus `TASK_wyrd_phase11d.md` through `TASK_wyrd_phase19.md` — the phased build log.
- Design: `WYRD_Phased_Implementation_Plan.md` (30 KB), `WYRD_Research_Determinations.md` (14 KB), `Technical_Architecture_of_Volmarrs_AI_Ecosystem.md` (the duplicated 55 KB reference), `WORLD_MODELING_SKILL.md`.
- Imagery: eight large PNG/JPG concept images (`Image_4343gd.png`, `Image_44445343gfg.png`, `Image786hjghj.png`, `Image888dvvkdsk3.png`, `rsezclrsezclrsez.png` at 8.6 MB, `IMG_0407.jpeg`, and five UUID-named JPGs).
- `configs/` — `memory_promotion.yaml`, `memory_store.example.yaml`, `micro_rag.example.yaml`, `persona_modes.example.yaml`, `truth_eval_suite.example.yaml`, and a `worlds/` folder.
- `docs/` — `api/`, `guides/` (`architecture.md`, `quickstart.md`), `index.md`, `integrations/`, `research/`, `specs/` (with `shared/` and `wyrd/` sub-spec folders), `tools/`, plus a large single essay `AI_World_Simulation__Foundations,_Architectures,_Applications,_Challenges,_and_Future_Horizons_in_Generative_World_Models_and_Embodied_Intelligence.md`.
- `examples/` — `micro_rag_candidates.yaml`, `seed_bond.yaml`.
- `install/` — cross-language installers (`install_cpp.py`, `install_csharp.py`, `install_js.py`, `install_native.py`, `install_python.py`, `_common.py`, `wyrd_setup.py`, `tests/`).
- `integrations/` — **twenty engine bridges**: `construct3`, `cryengine`, `defold`, `dndbeyond`, `fgu`, `foundry`, `gamemaker`, `godot`, `minecraft`, `monogame`, `o3de`, `opensim`, `owlbear`, `pygame`, `roblox`, `roll20`, `rpgmaker`, `sillytavern`, `unity`, `unreal`. Each holds a `wyrdforge` sub-package.
- `research_data/` — full 00–25 series duplicated again, with `config/`, `examples/`, `scripts/`, `src/`, `tests/`, `wyrd_runtime/`, and the supporting `.md` specs.
- `scripts/generate_json_schemas.py`.
- `sdk/` — `csharp/`, `gdscript/`, `js/`.
- `src/wyrdforge/` — the full engine source:
  - `bridges/`: `agentzero_bridge.py`, `base.py`, `hermes_bridge.py`, `http_api.py`, `kindroid_bridge.py`, `nse_bridge.py`, `openclaw_bridge.py`, `python_rpg.py`, `voxta_bridge.py`.
  - `ecs/`: `component.py`, `components/` (`character.py`, `identity.py`, `physical.py`, `runic.py`, `spatial.py`), `entity.py`, `system.py`, `systems/` (`presence.py`, `state_transition.py`), `world.py`, `yggdrasil.py`.
  - `evals/harness.py`.
  - `hardening/`: `backoff.py`, `config_validator.py`, `normalization.py`, `pool.py`.
  - `llm/`, `loaders/`, `models/`, `schemas/`, `security/`, `services/` — further sub-packages.
  - `oracle/`: `models.py`, `passive_oracle.py`.
  - `persistence/`: `bond_store.py`, `memory_store.py`, `world_store.py`.
  - `runtime/`: `character_context.py`, `demo_seed.py`, `turn_loop.py`.
- `tests/` — 34 test files covering the full WYRD architecture (ECS, yggdrasil, memory, persona, bond store, oracle, ollama connector, bridges, runic engine, turn loop, hardening, load, normalization, etc.), plus `fixtures/`.
- `tools/`: `prima_scholar/`, `wyrd_cloud_relay/`, `wyrd_tui.py`.
- Two command-line entries: `wyrd_chat_cli.py`, `wyrd_world_cli.py`.
- `hello_world.md` — empty.

This is, effectively, the shipped WYRD v1.0.0 preserved intact.

### `yggdrasil/`

An extensive Python package that appears to be the **earlier, NSE-era Yggdrasil** — heavily instrumented with the paired AI-companion markdown sidecars (every `.py` has eleven matching `_AI_HINTS.md`, `_DEBUGGING.md`, `_DEPENDENCIES.md`, `_EXAMPLES.md`, `_INTERFACE.md`, `_METRICS.md`, `_PATTERNS.md`, `_PROMPTS.md`, `_README_AI.md`, `_TASKS.md`, `_TESTS.md` files).

- Top-level: `__init__.py`, `identity.py`, `router.py` (35 KB), `router_enhanced.py` (34 KB), `cognition_integration.py` (23 KB), `enhanced_router.py`, `README.md`, `README_AI.md`, `INTERFACE.md`.
- `core/`: `bifrost.py`, `dag.py`, `llm_queue.py`, `world_tree.py`, `wyrd_system.py`.
- `cognition/`: `contracts.py`, `domain_crosslinker.py`, `gap_analyzer.py`, `hierarchical_memory.py`, `huginn_advanced.py`, `memory_orchestrator.py`.
- `integration/`: `deep_integration.py`, `norse_saga.py`.
- `knowledge/`: `chart_intelligence.py`, `graph_weaver.py`, `web_search.py`.
- `ravens/`: `huginn.py`, `muninn.py`, `raven_rag.py`.
- `worlds/`: one Python module per realm — `alfheim.py`, `asgard.py`, `helheim.py`, `jotunheim.py`, `midgard.py`, `muspelheim.py`, `niflheim.py`, and the rest of the Nine Worlds.
- `config/default.yaml`, `prompts/system_prompts.yaml`, `tests/test_chart_intelligence.py`, `tests/test_yggdrasil.py`.

This directory embodies the Manifesto's "one tree, one breath" — routing every decision through OpenRouter across nine world-modules and two ravens (Huginn and Muninn).

---

## State of completeness — a candid reading

- **New:** Only `mythic_vibe_cli/`, the accompanying root `tests/`, the root-level CLI docs (`README.md`, `LEGAL-NOTICE.md`, the Mythic Engineering methodology corpus), and perhaps the smaller `core/` / `ai/` extractions appear to be genuinely new to this repository.
- **Complete but vendored upstream:** `chatterbox/`, `whisper/`, `ollama/` — intact OSS libraries.
- **Complete in-project imports:** `mindspark_thoughtform/` and `WYRD-Protocol-*/` — near-full snapshots of those two shipped projects.
- **Live engine fragments:** `systems/`, `core/`, `ai/`, `sessions/`, `yggdrasil/`, `imports/norsesaga/systems/` — NSE's working engine, imported in several overlapping layers.
- **Documentation corpus:** `docs/specs/`, `docs/research/`, all three copies of `research_data/` — spec and study material staged for use but not yet wired to the CLI.
- **Orphan seams:** `core/saga_odin_rag.py` imports `..yggdrasil_core`, a module not present — so at least one fragment is in-broken-state.

No integration has yet been attempted. This repo is a *gathering hall*, not yet a unified product.

---

_End of scroll._
