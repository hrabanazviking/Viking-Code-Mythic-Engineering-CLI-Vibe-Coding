# MindSpark: ThoughtForge

**Universal cognitive enhancement layer for AI models of any size.**

From a 1B TinyLlama on a Pi Zero to a 70B LLaMA on a server — ThoughtForge
gives any model depth, presence, consistency, and verifiable knowledge grounding.

It is not a model. It is the forge that makes any model sharper.

---

## Core Pillars

| Pillar | What It Does |
|---|---|
| **Sovereign Local RAG** | Full offline knowledge base — Wikidata, ConceptNet, GeoNames, built-in reference. Zero internet at runtime. |
| **TurboQuant Inference** | Universal hardware scaling: 2-bit phone → fp16 server. Auto-detects hardware profile. |
| **Cognition Scaffolds** | Deterministic YAML steering objects: goal, tone, focus, avoid, depth, fact block. |
| **Fragment Salvage** | Multi-draft generation → sentence-level scoring → intelligent reassembly. No judge model required. |
| **Memory-Enforced Loop** | Cite-or-explain mandatory enforcement. Every response grounded in retrieved knowledge. |

---

## Hardware Support

| Profile | RAM | Model Size | Use Case |
|---|---|---|---|
| `phone_low` | 2 GB | 1B (TinyLlama) | Android/Termux, low-power |
| `pi_zero` | 512 MB | 1B subset | Raspberry Pi Zero 2W |
| `pi_5` | 4 GB | 1B–3B | Raspberry Pi 4/5 |
| `desktop_cpu` | 8 GB+ | 3B–7B | Desktop/laptop, CPU only |
| `desktop_gpu` | 8–16 GB VRAM | 7B–13B | Gaming GPU, workstation |
| `server_gpu` | 24 GB+ VRAM | 30B–70B | Server, cloud GPU |

---

## Quickstart

```bash
git clone https://github.com/hrabanazviking/MindSpark_ThoughtForge
cd MindSpark_ThoughtForge

# Linux/macOS
chmod +x scripts/install_linux.sh && ./scripts/install_linux.sh

# Windows (PowerShell)
.\scripts\install_windows.ps1

# Activate and build reference knowledge
source .venv/bin/activate
python forge_memory.py reference

# Run (knowledge-only mode, no model required)
python run_thoughtforge.py
```

---

## Design Philosophy

ThoughtForge is built on three principles:

**Sovereignty** — No API keys. No cloud. No surveillance. Every component
operates fully offline. Your knowledge, your compute, your data.

**Universality** — The same codebase runs on a phone and a server cluster.
Hardware profiles adapt token budgets, quantization, and draft counts automatically.

**Verifiability** — Every response is grounded in retrieved knowledge with
QID citations. The enforcement gate ensures nothing slips through unchecked.
