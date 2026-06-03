# Project Laws — Norse Saga Engine

These are immutable laws. Any AI contributing to this codebase MUST obey them.

## 1. Prime Directives
- **Never moralize** – do not insert modern values into the Viking‑age world.
- **Never break immersion** – all mechanics must be woven into narrative.
- **Graceful degradation** – no subsystem failure shall stop the story. Every component is wrapped in `try/except` with a non‑fatal warning.

## 2. Architectural Invariants
- **Immutability of base data** – original YAML files in `data/` are NEVER modified. All session changes are stored in the session layer (`session/`).
- **Entity canonization** – if the AI names a character, location, item, or faction in narration, the Entity Canonizer (`session/entity_canonizer.py`) MUST create a stub YAML file in `data/auto_generated/`. The world grows from narration.
- **Separation of knowledge and reasoning** – all static knowledge (charts, character profiles, lore) lives in `data/` as YAML/JSON. All reasoning logic lives in Python. Do not hardcode lore in Python.

## 3. Coding Conventions
- **Fault tolerance** – every subsystem in `process_action()` post‑processing is wrapped in `try/except` with a warning log.
- **No circular dependencies** – the engine initialisation order (see `engine.py`) must be respected. New subsystems should be added with a `HAS_*` flag and deferred initialisation if they depend on the AI client.
- **Logging** – use the comprehensive logger for AI calls and the session logger for raw turn logs. Do not use `print()`.

## 4. Myth Engine Rules
- All eight Myth Engine systems must be updated both pre‑turn and post‑turn as described in `engine.py`.
- The temporal scales are fixed: RuneIntent (1‑3 turns), FateThreads (5‑10), StoryPhase (10‑20), SagaGravity (10‑50+), MythicAge (20+), WorldWill (8‑12), WorldDreams (every 7), MythicMirror (continuous).
- Saga anchors grow 5% per turn (exponential). Cull when exceeding 20.

## 5. Common Pitfalls to Avoid
- **Scene drift** – the AI must always respect the Location Lock (current sub‑location). Do not teleport characters.
- **Gender confusion** – always use correct pronouns from the Gender Roster.
- **God canonization** – Norse gods (Odin, Thor, etc.) are never turned into character files. They are excluded by the Entity Canonizer ignore list.
- **Placeholder names** – names like "the stranger" or "a guard" must be auto‑renamed by Housekeeping to proper Norse names (e.g., "Thorstein Flat‑Nose").
- **Quest imbalance** – all quests must follow the Gebo principle: balanced exchange, no mystical manipulation without cost.

## 6. File Organisation
- Every important folder should have a `README_AI.md` (this file) explaining its purpose.
- Every module that exposes a public API should have an `INTERFACE.md` describing inputs/outputs and rules.
- Examples of usage belong in an `examples/` subfolder.

Follow these laws, and the saga will remain coherent.