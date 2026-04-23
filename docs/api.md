# API Reference

Core public API for integrating ThoughtForge into your application.

---

## ThoughtForgeCore

The main entry point. Handles the full `think()` pipeline.

```python
from thoughtforge.cognition.core import ThoughtForgeCore
from pathlib import Path

core = ThoughtForgeCore(
    model_path=Path("/models/mistral-7b-q4.gguf"),   # optional
    memory_dir=Path("~/.local/share/thoughtforge/memory"),
    db_path=Path("~/.local/share/thoughtforge/knowledge/thoughtforge.db"),
)

result = core.think("What is Yggdrasil?")
print(result.text)
print(result.citations)     # ["Q42240"]
print(result.enforcement_passed)   # True/False
```

### `ThoughtForgeCore(model_path, memory_dir, db_path)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model_path` | `Path \| None` | `None` | Path to GGUF model. `None` = knowledge-only mode. |
| `memory_dir` | `Path \| None` | Auto | Directory for episodic memory, preferences, etc. |
| `db_path` | `Path \| None` | Auto | Path to SQLite knowledge DB. |

### `think(user_text, retrieval_path=None, num_drafts=None) → FinalResponseRecord`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `user_text` | `str` | — | User query text. |
| `retrieval_path` | `"sql" \| "vector" \| "hybrid" \| None` | Auto | Override retrieval path. |
| `num_drafts` | `int \| None` | Profile default | Override draft count. |

---

## FinalResponseRecord

Returned by `think()`. All fields are always populated.

```python
@dataclass
class FinalResponseRecord:
    turn_id: str               # UUID for this turn
    text: str                  # final response text
    citations: list[str]       # QID strings cited in text (e.g. ["Q42240"])
    scores: CandidateScores    # composite, quality_tier, etc.
    token_count: int           # estimated tokens in response
    enforcement_passed: bool   # True if EnforcementGate passed
    enforcement_notes: str     # notes if enforcement review needed
    salvage_path: str          # "best_draft" | "refine_pass_1" | "knowledge_only"
    retrieval_confidence: float
    mode: str                  # generation mode used
```

### Quality Tiers (`scores.quality_tier`)

| Tier | Composite Score | Meaning |
|---|---|---|
| `excellent` | ≥ 0.85 | Strong citations + adequate length |
| `good` | ≥ 0.65 | Solid response with some citations |
| `adequate` | ≥ 0.45 | Acceptable but could improve |
| `poor` | < 0.45 | Weak — enforcement likely flagged |

---

## FragmentSalvage

```python
from thoughtforge.refinement.salvage import FragmentSalvage

salvage = FragmentSalvage()
result = salvage.forge(candidates, bundle)

# result.salvage_path: "best_draft" | "refine_pass_1" | "empty"
# result.confidence: 0.0 – 1.0
# result.citations: list of QID strings
```

---

## EnforcementGate

```python
from thoughtforge.refinement.enforcement import EnforcementGate

gate = EnforcementGate()
result = gate.check(text, citations, retrieved_qids)

# result.passed: bool
# result.status: "pass" | "review"
# result.citation_check, result.length_check, result.genericness_check: bool
# result.notes: str (empty if all pass)
```

---

## EdgeSubsetBuilder

```python
from thoughtforge.etl.subset import EdgeSubsetBuilder
from pathlib import Path

builder = EdgeSubsetBuilder()
result = builder.build(
    source_db=Path("data/thoughtforge.db"),
    output_path=Path("data/thoughtforge_pi_zero.db"),
    profile_id="pi_zero",       # uses 50K entity limit
    max_entities=30_000,        # optional override
)

print(result.entities_copied)
print(result.size_mb)
print(result.success)
```

---

## OnnxExporter / ONNXEmbedder

```python
from thoughtforge.inference.onnx_export import OnnxExporter, ONNXEmbedder
from pathlib import Path

# Export (requires optimum or torch)
exporter = OnnxExporter()
result = exporter.export_embedder(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    output_dir=Path("models/onnx/all-MiniLM-L6-v2"),
    quantize=True,   # produce int8 model
)

# Embed at runtime (requires onnxruntime)
embedder = ONNXEmbedder(result.output_dir)
vectors = embedder.encode(["Yggdrasil", "Midgard"])
# vectors.shape == (2, 384)
```

---

## ProfileBenchmark

```python
from benchmarks.benchmark_profiles import ProfileBenchmark

result = ProfileBenchmark().run("desktop_cpu")
print(result.summary())
print(result.citation_accuracy)       # 0.0–1.0
print(result.enforcement_pass_rate)   # 0.0–1.0
print(result.avg_latency_ms)          # milliseconds
```

---

## PersonaConsistencyScorer

```python
from benchmarks.persona_consistency import PersonaConsistencyScorer

responses = [r.text for r in turn_results]
scorer = PersonaConsistencyScorer()
result = scorer.score(responses)

print(result.consistency_score)   # 0.0–1.0 (target ≥ 0.75)
print(result.passes)              # bool
print(result.summary())

# Generate markdown report
report = PersonaConsistencyScorer.generate_report(result, "persona_report.md")
```
