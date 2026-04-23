# Model Card — MindSpark: ThoughtForge v1.0.0

**Type:** Cognitive enhancement layer (not a model — a framework)
**License:** CC BY 4.0
**Repository:** https://github.com/hrabanazviking/MindSpark_ThoughtForge
**Version:** 1.0.0
**Release date:** 2026-03-31

---

## What ThoughtForge Is

ThoughtForge is **not a model** — it is a universal cognitive enhancement layer
that can be placed around **any** GGUF-compatible LLM to give it:

- Verified, sovereign offline knowledge grounding
- Deterministic cognition scaffolds (goal, tone, focus, constraints)
- Multi-draft fragment salvage + intelligent reassembly
- Citation enforcement: every claim must be grounded or flagged
- Hardware-adaptive inference from Pi Zero to 70B server

Think of it as a forge. You bring the metal (your model). ThoughtForge makes it sharper.

---

## Intended Use

### Designed for

- **Offline sovereign AI** — zero cloud, zero API keys, zero internet at runtime
- **Edge deployment** — phones, Raspberry Pi, low-power ARM
- **Research** — studying citation-grounded generation and memory-enforced cognition
- **Developers** — building privacy-respecting, knowledge-grounded AI applications
- **Knowledge workers** — local assistants with verifiable, cited responses

### Not intended for

- Real-time high-frequency trading or medical diagnosis without human oversight
- Replacing domain-expert review in legal, medical, or safety-critical contexts
- Generating high-volume synthetic data without human review
- Any application that requires internet connectivity at inference time

---

## Compatible Models

ThoughtForge wraps any GGUF model via `llama-cpp-python`. Recommended pairs:

| Hardware Profile | Recommended Model | Quantization |
|---|---|---|
| `phone_low` (2GB RAM) | TinyLlama-1.1B-Chat | Q2_K |
| `pi_zero` (512MB) | TinyLlama-1.1B subset | Q2_K |
| `pi_5` (4GB) | Phi-3-mini-128k | Q4_K_M |
| `desktop_cpu` (8GB+) | Mistral-7B-Instruct | Q4_K_M |
| `desktop_gpu` (12GB VRAM) | LLaMA-3-8B-Instruct | Q8_0 |
| `server_gpu` (24GB+ VRAM) | Mixtral-8x7B / LLaMA-3-70B | Q4_K_M |

ThoughtForge also operates in **knowledge-only mode** (no model required), assembling
responses directly from retrieved knowledge records.

---

## Knowledge Sources

The offline knowledge base is built from:

| Source | Description | Coverage |
|---|---|---|
| Wikidata | Full dump (~100GB) | 100M+ entities, multilingual |
| DBpedia | Structured entity data | Wikipedia-derived |
| ConceptNet | Common-sense relations | Everyday knowledge |
| GeoNames | Geographic entities | 11M+ locations |
| Built-in reference | 40 domain files | Norse mythology, D&D SRD, history, literature |

All sources are sovereign — ingested offline once, queried locally forever.

---

## Architecture

```
User Query
    │
    ▼
┌─────────────┐    SQL + Vector     ┌──────────────────────┐
│ InputRouter │ ──────────────────▶ │   MemoryForge (RAG)  │
│  (intent +  │                     │  SQLite + FTS5 +      │
│   tone)     │                     │  sentence-transformers│
└─────────────┘                     └──────────┬───────────┘
                                               │ MemoryActivationBundle
    ▼                                          ▼
┌──────────────────┐              ┌────────────────────────┐
│ ScaffoldBuilder  │◀─────────────│    PromptBuilder       │
│ (CognitionScaffold│             │  mode-specific prompts │
│  goal/tone/focus) │             └────────────────────────┘
└──────────┬───────┘
           │ prompt
           ▼
┌──────────────────┐   N drafts   ┌────────────────────────┐
│ TurboQuantEngine │─────────────▶│   FragmentSalvage      │
│ (llama-cpp-python│              │  score + extract +      │
│  or knowledge    │              │  reassemble (≤2 passes) │
│  summary)        │              └──────────┬─────────────┘
└──────────────────┘                         │ SalvageResult
                                             ▼
                                  ┌──────────────────────┐
                                  │   EnforcementGate    │
                                  │  citations + length  │
                                  │  + genericness check │
                                  └──────────┬───────────┘
                                             │ FinalResponseRecord
                                             ▼
                                       User Response
```

---

## Evaluation

### Target Metrics (Phase 6 benchmark suite)

| Metric | Target | How Measured |
|---|---|---|
| Citation accuracy | ≥ 85% | Turns with ≥1 QID citation / total turns |
| Enforcement pass rate | ≥ 90% | EnforcementGate.passed / total turns |
| Persona consistency | ≥ 0.75 | PersonaConsistencyScorer across 100+ turns |
| Avg response words | ≥ 30 | Per-turn word count |

### Scoring Formula (Fragment Salvage)

```
composite = length_score × 0.45 + citation_score × 0.55

length_score = min(1.0, char_count / 550)
citation_score = cited_qids / retrieved_qids  (0.5 if no QIDs retrieved)
```

---

## Limitations

- **Knowledge cutoff:** Wikidata dump date determines knowledge currency. Updating requires re-running ETL.
- **No real-time learning:** ThoughtForge does not update its knowledge base from runtime interactions (by design).
- **Citation hallucination:** The underlying LLM may still hallucinate QIDs not in the knowledge base. The enforcement gate flags but does not always prevent this.
- **Edge inference speed:** Pi Zero and phone_low profiles are slow (minutes per response without model optimization).
- **Language:** Knowledge base is primarily English (Wikidata `label_en`). Multilingual support is possible but not tested.

---

## Ethical Considerations

ThoughtForge is built with sovereign AI principles:

- **Privacy-first:** No telemetry, no cloud calls, no data leaves the device.
- **Transparency:** All citations are QID-traceable to the knowledge source.
- **Auditability:** The enforcement gate provides explicit fail reasons.
- **No lock-in:** Works with any GGUF model. You own the stack.

---

## Citation

```bibtex
@software{thoughtforge2026,
  title   = {MindSpark: ThoughtForge — Universal Cognitive Enhancement Layer},
  author  = {RuneForgeAI},
  year    = {2026},
  version = {1.0.0},
  url     = {https://github.com/hrabanazviking/MindSpark_ThoughtForge},
  license = {CC BY 4.0}
}
```
