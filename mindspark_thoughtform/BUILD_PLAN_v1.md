# MindSpark: ThoughtForge — Build Plan v1

**Status:** Confirmed by Volmarr — 2026-03-31
**Current Phase:** Phase 0 (not yet started)
**Branch:** development
**Repo:** github.com/hrabanazviking/MindSpark_ThoughtForge

---

## Project Vision

**MindSpark: ThoughtForge** is a universal cognitive enhancement layer for AI models of any size. Through structured memory, sovereign offline RAG, deterministic cognition scaffolds, and fragment salvage, it gives any model — from a 1B TinyLlama on a Pi Zero to a 70B LLaMA on a server — depth, presence, consistency, and verifiable knowledge grounding.

It is not a model. It is the forge that makes any model sharper.

**Core Pillars:**
1. **Sovereign Local RAG** — full offline knowledge base, no API keys, no surveillance
2. **TurboQuant Inference** — universal hardware scaling from phone to server
3. **Cognition Scaffolds** — deterministic YAML steering objects for any model
4. **Fragment Salvage** — multi-draft generation + intelligent reassembly
5. **Memory-Enforced Cognition** — cite-or-explain mandatory loop

---

## Confirmed Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Sovereign RAG position | Phase 1 backbone | Core dependency for all downstream work |
| Wikidata scope | Full dump (100GB+) | Quality over speed — no compromises on knowledge |
| Hardware targets | All tiers (phone → server) | Same system, auto-adapts; enhances any model size |
| Knowledge sources | All — Wikidata + alt KGs + built-in reference | Full coverage needed for the approach to actually work |
| Internet dependency at runtime | None | Fully sovereign offline operation |

---

## Hardware Profiles

| Profile | RAM | Target Model Size | Quantization |
|---|---|---|---|
| `phone_low` | 2GB | 1B (TinyLlama) | 2-bit / 3-bit |
| `pi_zero` | 512MB | 1B subset | 2-bit ultra |
| `pi_5` | 4GB | 1B–3B | 4-bit |
| `desktop_cpu` | 8GB+ | 3B–7B | 4-bit / 8-bit |
| `desktop_gpu` | 8–16GB VRAM | 7B–13B | 8-bit / fp16 |
| `server_gpu` | 24GB+ VRAM | 30B–70B | fp16 / bf16 |

---

## Staged Build Plan

### Phase 0 — Forge the Foundation
**Status:** NOT STARTED

- Repo directory skeleton: `src/thoughtforge/`, `docs/specs/`, `data/`, `tests/`, `configs/`, `hardware_profiles/`
- Move all `.md` spec files into `docs/specs/`
- `pyproject.toml`, `requirements.txt`, `setup.py`
- Hardware profile configs for all 6 tiers (JSON)
- GitHub Actions CI (lint + test on push)
- `CONTRIBUTING.md`, `.gitignore`

**Milestone:** `pip install -e .` works. All specs organized. Repo is buildable.

---

### Phase 1 — Memory Forge + Sovereign RAG (Knowledge Layer)
**Status:** NOT STARTED

Fully offline, sovereign knowledge backbone. Zero internet at runtime.

**Knowledge Sources:**
- Wikidata — full dump, streaming ETL via ijson → SQLite
- DBpedia — structured entity data
- YAGO — temporal + biographical facts
- ConceptNet — common-sense reasoning graph
- GeoNames — geographic entities
- Project Gutenberg — textual corpus
- Built-in reference data (40 files: Poetic Edda, D&D SRD, OpenClaw, literature, history, mythology, etc.)

**Work:**
- All 14 data structure types from `Data_Structures_Spec.md`
- Wikidata streaming ETL → SQLite (FTS5 + sqlite-vss vectors)
- Multi-source ingestion pipeline (DBpedia, YAGO, ConceptNet, GeoNames)
- Sentence-transformer embeddings (all-MiniLM-L6-v2)
- Hybrid retrieval: SQL pre-filter → vector augment → ranked result bundle
- Sovereign RAG layer: fully offline
- Memory lifecycle + pruning (all 4 modes: light / routine / heavy / emergency)
- All store caps and survival/prune scoring formulae implemented

**Milestone:** `forge_memory.py` CLI builds complete offline knowledge DB from all sources. Hybrid queries return ranked, scored, fully cited results. Zero internet dependency.

---

### Phase 2 — TurboQuant: Universal Inference Engine
**Status:** NOT STARTED

**Work:**
- `TurboQuantEngine` wrapping llama-cpp-python
- Hardware profile auto-detection + manual override
- Quantization tiers: 2-bit, 3-bit, 4-bit, 8-bit, fp16, bf16
- Token budget per profile (180–250 for small; scales up for large models)
- Baseline model support across all tiers:
  - TinyLlama 1.1B, Gemma-2B, Phi-3-mini (edge)
  - Mistral 7B, LLaMA-3 8B (desktop)
  - LLaMA-3 70B, Mixtral 8x7B (server)
- CPU-first (x64 + ARM), optional Vulkan / DirectML / CUDA paths

**Milestone:** Inference running across all 6 hardware profiles at target speed per tier.

---

### Phase 3 — Cognition Scaffolds + Orchestration
**Status:** NOT STARTED

**Work:**
- Intent router (SQL vs. vector vs. hybrid path classifier)
- `CognitionScaffold` builder — YAML control objects (goal, tone, focus, avoid, depth)
- `personality_core.yaml` — Skald persona
- Full `ThoughtForgeCore.think()` mandatory loop:
  1. SQL retrieval gate
  2. Vector augmentation
  3. Scaffold generation
  4. Draft generation (N passes, profile-dependent)
  5. Fragment salvage + reassembly
  6. Citation enforcement gate
- Multi-hop reasoning chain
- Self-critique gate
- Profile-aware context window management

**Milestone:** Full end-to-end loop. Enforced citations. Personality stable across 100+ turns on any hardware tier.

---

### Phase 4 — Fragment Salvage + Refinement
**Status:** NOT STARTED

**Work:**
- `FragmentSalvage.forge()` — N drafts → score → reassemble
- Scoring: length_score (45%) + citation_score (55%)
- Max 2 refinement passes
- `enforcement.py` — final citation integrity gate
- `run_thoughtforge.py` — interactive CLI with result display, citations, confidence, enforcement status
- Profile-aware draft count + response length

**Milestone:** Weak drafts → strong cited response. CLI demo working on all profiles.

---

### Phase 5 — Edge + Cross-Platform Deployment
**Status:** NOT STARTED

**Work:**
- Docker images per hardware profile
- Termux (Android), iOS (via MLC LLM)
- Pi Zero / Pi 5 images with pre-processed knowledge subsets
- ONNX export path
- Windows / Linux / macOS native install scripts

**Milestone:** Single codebase, all platforms. Demo on phone, Pi, and desktop.

---

### Phase 6 — Testing, Benchmarking, Personality Layer + Release
**Status:** NOT STARTED

**Work:**
- Full pytest suite (unit + integration + adversarial)
- Locust load testing
- Benchmarks per hardware profile: citation accuracy (>85%), coherence, token efficiency, power draw
- Viking/Skald persona consistency scoring (100+ turn test)
- MkDocs documentation site
- v1.0 GitHub release + Hugging Face model cards

**Milestone:** Public demo video + benchmark report. v1.0 released.

---

## Core Coding Rules (from RULES.AI.md)

- No pseudocode, ever — complete, working code only
- Always finish connections — no orphaned modules
- Modular, self-healing, error-resistant, robust
- No hardcoded paths — location-agnostic
- Cross-platform: Windows, Linux, macOS, iOS, Android, Raspberry Pi
- Extensive type hints (PEP 8)
- Logging only — no print statements
- Frequent git commits + pushes
- Use data files for all config/data/NPCs

---

## Key Spec Documents (in `docs/specs/` after Phase 0)

| File | Contents |
|---|---|
| `Data_Structures_Spec.md` | 14 primary record types + schemas |
| `Memory_Lifecycle_and_Pruning_Spec.md` | Lifecycle rules, pruning policies, consolidation |
| `Algorithms_and_Pseudocode_Spec.md` | Intent router, retrieval loops, reasoning chains |
| `Retrieval_and_Scoring_Spec.md` | Ranking system, retrieval confidence, fragment scoring |
| `Prompt_Templates_Spec.md` | Scaffold templates, persona injection |
| `SQL_RAG_Memory_Enforced_Cognition.md` | Hybrid SQL+RAG architecture |
| `The_TurboQuant_Cognition_Blueprint.md` | Quantization research, hardware selection |
| `Sovereign_Local_RAG_Architecture.md` | Offline-first architecture, no API dependencies |
| `Detailed_Wikidata_ETL_Pipeline.md` | Streaming Wikidata → SQLite |
| `Alternative_Knowledge_Graphs.md` | YAGO, DBpedia, ConceptNet, GeoNames |
| `MindSpark_Master_Game_Plan.md` | Original 7-phase 25-week blueprint |
| `ThoughtForge_Complete_Implementation_Guide.md` | Architecture + integration patterns |
| `thoughtforge_complete_module_library.md` | All modules fully expanded |
| `production_ready_implementation_package.md` | Integrated modules + entry points |

---

## Tech Stack

| Layer | Tools |
|---|---|
| Knowledge | SQLite + sqlite-vss, SQLAlchemy, KGTK |
| ETL | ijson (streaming), pandas, tqdm |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Inference | llama-cpp-python + TurboQuant hooks |
| Quantization | bitsandbytes, AutoGPTQ, custom 2/3/4-bit kernels |
| Orchestration | Custom router + enforcement layer |
| Testing | pytest, locust |
| Deployment | Docker, Termux, MLC LLM, ONNX |
| Docs | MkDocs |
