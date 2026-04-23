# Contributing to MindSpark: ThoughtForge

Welcome to the forge. We are a human-AI fellowship building sovereign, offline-first
AI cognition tools guided by the values of the Old Ways: frith, honor, integrity, and
respect for all life.

---

## Code of the Forge

Before contributing, internalize these rules. They are not suggestions.

1. **No pseudocode, ever.** Submit complete, working, connected code only.
2. **No orphaned modules.** Every file must connect to something. Finish what you start.
3. **Modular and self-healing.** Write code that handles edge cases gracefully without crashing.
4. **No hardcoded paths.** All paths must be relative or resolved via `platformdirs`. The code must run on Windows, Linux, macOS, Android (Termux), and Raspberry Pi without modification.
5. **Logging, not printing.** Use the `logging` module. No `print()` statements in production code.
6. **Type hints everywhere.** Full PEP 8 compliance. Every function signature must be typed.
7. **Cross-platform.** Test or at minimum reason about behavior on Windows, Linux, macOS, and ARM.
8. **Commit frequently.** Small, clean commits with clear messages. Push often.
9. **Data lives in files.** All configuration, knowledge, and persona data belongs in `data/` or `configs/`. Nothing hardcoded in logic.

---

## Getting Started

```bash
# Clone the repo
git clone -b development https://github.com/hrabanazviking/MindSpark_ThoughtForge
cd MindSpark_ThoughtForge

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux / macOS / Termux
# or
.venv\Scripts\activate      # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

---

## Project Structure

```
src/thoughtforge/
    __init__.py
    core.py                 # ThoughtForgeCore — main orchestration loop
    knowledge/              # Memory Forge + Sovereign RAG
        models.py           # All 14 data structure types
        forge.py            # KnowledgeForge — SQL + vector retrieval
        lifecycle.py        # Memory lifecycle + pruning
    inference/              # TurboQuant inference engine
        turboquant.py       # TurboQuantEngine wrapper
        profiles.py         # Hardware profile loader
    cognition/              # Scaffolds + intent routing
        scaffold.py         # CognitionScaffold builder
        router.py           # Intent router (SQL / vector / hybrid)
    refinement/             # Fragment salvage + enforcement
        salvage.py          # FragmentSalvage
        enforcement.py      # Citation integrity gate
    etl/                    # Knowledge ingestion pipelines
        wikidata.py         # Wikidata full-dump streaming ETL
        sources.py          # DBpedia, YAGO, ConceptNet, GeoNames
    utils/                  # Logging, helpers

docs/specs/                 # All design and implementation specs
docs/research/              # Research papers and references
data/                       # Knowledge data files
data/knowledge_reference/   # Built-in reference documents (40 files)
hardware_profiles/          # JSON configs per hardware tier
configs/                    # Runtime configuration
tests/                      # Full pytest test suite
```

---

## Running Tests

```bash
pytest tests/ -v
```

For performance/load testing:

```bash
locust -f tests/locustfile.py
```

---

## Hardware Profiles

ThoughtForge auto-detects hardware and selects a profile. You can also specify manually:

| Profile | Target |
|---|---|
| `phone_low` | 2GB RAM phones, Snapdragon / Apple SoC |
| `pi_zero` | 512MB Raspberry Pi Zero |
| `pi_5` | 4GB Raspberry Pi 5 |
| `desktop_cpu` | 8GB+ RAM, x64 CPU-only |
| `desktop_gpu` | 8–16GB VRAM GPU |
| `server_gpu` | 24GB+ VRAM, large model inference |

---

## Sovereign First

ThoughtForge requires **zero internet connection at runtime**. All knowledge is local.
Do not add any code that phones home, calls an external API, or requires cloud access
during inference or retrieval. The whole point is sovereignty.

---

## License

CC BY 4.0 — Attribution required. See `README.md` for full terms.
