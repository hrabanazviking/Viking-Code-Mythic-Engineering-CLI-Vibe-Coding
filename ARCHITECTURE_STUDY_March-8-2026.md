# Norse Saga Engine - Architecture Study Report
**Date:** March 8, 2026  
**Author:** Runa Gridweaver Freyjasdottir (AI Architecture Analyst)

---

## Executive Summary

The Norse Saga Engine is a sophisticated AI-driven solo RPG system that blends D&D 5E 2024 mechanics, Mythic GME oracle elements, and authentic Norse mysticism. The architecture follows a **monolithic orchestrator pattern** with modular subsystems, using Norse cosmological metaphors throughout the codebase. The system demonstrates strong domain modeling and comprehensive error handling, with primary architectural concerns around file size and complexity management.

---

## Architecture Overview

### System Architecture Layers

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE LAYER                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  main.py (202,125 chars) - Rich Console UI, Voice Bridge    │   │
│  │  - 60+ slash commands                                       │   │
│  │  - Image display for portraits                              │   │
│  │  - Voice integration (Whisper STT + Chatterbox TTS)         │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  core/engine.py (298,399 chars) - YggdrasilEngine          │   │
│  │  - 40+ subsystem coordination                                │   │
│  │  - GameState management                                      │   │
│  │  - process_action() pipeline                                │   │
│  │  - AI completion routing                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AI INTEGRATION LAYER                        │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐  │
│  │  ai/openrouter.py         │  │  ai/prompt_builder.py        │  │
│  │  - OpenRouter API client  │  │  - Dynamic prompt assembly   │  │
│  │  - Circuit breaker        │  │  - RAG integration            │  │
│  │  - Fallback models        │  │  - Chart data loading        │  │
│  │  - Context management    │  │  - Scene context building    │  │
│  └──────────────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          SYSTEMS LAYER                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  40+ Subsystems in systems/ directory                        │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │   │
│  │  │  Memory     │ │   Chaos     │ │  Emotional  │           │   │
│  │  │  System     │ │   System    │ │  Engine     │           │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │   │
│  │  │    Dice     │ │    RAG      │ │   Quest     │           │   │
│  │  │   System    │ │   System    │ │  Causality  │           │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘           │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    YGGDRASIL COGNITIVE LAYER                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  yggdrasil/router.py - YggdrasilAIRouter                    │   │
│  │  - Unified AI call routing                                  │   │
│  │  - Nine realm processors for cognitive domains              │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Ravens: Huginn (Thought) / Muninn (Memory)         │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Worlds: Midgard | Asgard | Helheim | Jotunheim    │   │   │
│  │  │          Alfheim | Muspelheim | Niflheim           │   │   │
│  │  │          Svartalfheim | Vanaheim                    │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  data/charts/ - 100+ lore/data files                        │   │
│  │  data/characters/ - YAML character sheets                   │   │
│  │  data/world/ - Location definitions                         │   │
│  │  session/ - Runtime state persistence                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Analysis

### 1. Entry Point Layer - [`main.py`](main.py)

**Size:** 202,125 chars (~4,270 lines)

**Primary Responsibilities:**
- Game loop initialization and command handling
- Rich console UI with panels, tables, markdown rendering
- 60+ slash commands for player interaction
- Voice integration via VoiceBridge
- Image display for character portraits
- Character disambiguation for NPC lookup

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `main()` | Initialization and startup sequence |
| `game_loop()` | Main input/command processing loop |
| `handle_command()` | Slash command routing |
| `display_narration()` | AI response rendering |
| `show_status()` | Character status display |

**Command Categories:**
- **Navigation:** `/travel`, `/location`, `/map`
- **Character:** `/status`, `/inventory`, `/equipment`
- **Social:** `/talk`, `/ask`, `/trade`
- **Combat:** `/attack`, `/defend`, `/flee`
- **System:** `/save`, `/load`, `/quit`, `/help`

---

### 2. Core Orchestrator - [`core/engine.py`](core/engine.py)

**Size:** 298,399 chars (~7,500+ lines) ⚠️ **Very Large**

**Central Class:** `YggdrasilEngine`

**GameState Dataclass Fields:**
```python
@dataclass
class GameState:
    session_id: str
    turn_count: int
    current_location: str
    sub_location: str
    npcs_present: List[NPCState]
    player_state: PlayerState
    chaos_factor: float
    emotional_states: Dict[str, EmotionalState]
    quest_progress: Dict[str, QuestState]
    world_state: WorldState
    conversation_history: List[TurnMemory]
    active_effects: List[ActiveEffect]
```

**Key Methods:**
| Method | Lines | Purpose |
|--------|-------|---------|
| `process_action()` | 700+ | Main turn processing pipeline |
| `_ai_complete()` | 200+ | AI completion with routing |
| `initialize_ai()` | 150+ | Multi-client AI setup |
| `_build_continuity_context_packet()` | 300+ | Context assembly for prompts |

**Subsystems Initialized (40+):**
- SoulRegistry - Character soul/hugr tracking
- WyrdTethers - Fate connections
- RunicResonance - Rune influences
- ObjectAgency - Object sentience
- CosmicCycle - World cycles
- EmotionalEngine - Per-character emotions
- StressSystem - Character stress tracking
- MenstrualCycleSystem - Female character cycles
- AdvancedChaosSystem - Chaos factor management
- EnhancedMemoryManager - AI-powered memory

---

### 3. AI Integration Layer

#### [`ai/openrouter.py`](ai/openrouter.py) - API Client

**Size:** 875 lines

**Key Classes:**
```python
class OpenRouterClient:
    - Async API access to LLMs
    - Support for 20+ models
    - Circuit breaker pattern
    - Context window management
    - Streaming completion support

class CompletionResponse:
    - content: str
    - model: str
    - usage: Dict
    - finish_reason: str
```

**Supported Models:**
- DeepSeek (deepseek-chat, deepseek-reasoner)
- Anthropic Claude (claude-3.5-sonnet, claude-3-opus)
- OpenAI GPT (gpt-4o, gpt-4-turbo)
- Meta Llama (llama-3.1-70b, llama-3.1-405b)
- Qwen (qwen-2.5-72b, qwen-2.5-coder)
- Mistral (mistral-large, mistral-medium)

**Features:**
- Automatic fallback model support
- Provider preferences for faster routing
- Retry logic with exponential backoff
- Emergency context compaction

#### [`ai/prompt_builder.py`](ai/prompt_builder.py) - Prompt Assembly

**Size:** 1,576 lines

**Key Classes:**
```python
@dataclass
class GameContext:
    location: str
    sub_location: str
    time_of_day: str
    weather: str
    npcs_present: List[NPCContext]
    player_state: PlayerContext
    recent_events: List[str]
    active_quests: List[str]
    emotional_atmosphere: str

class PromptBuilder:
    - build_base_personality()
    - build_cultural_filter()
    - build_scene_context()
    - build_npc_context()
    - build_memory_context()
    - build_system_prompt()
```

**Chart Loading:**
- Auto-loads all YAML, JSON, JSONL, CSV, MD, PDF files
- Multi-format parsing with error handling
- RAG system integration for lore retrieval

---

### 4. Systems Layer - [`systems/`](systems/)

**40+ Subsystems organized by domain:**

#### Memory Systems
| File | Lines | Purpose |
|------|-------|---------|
| `memory_system.py` | 436 | Three-tier memory (short/medium/long) |
| `enhanced_memory.py` | 740 | AI-powered turn summarization |

**Memory Tiers:**
```
Short-term:  5 turns   → Immediate context
Medium-term: 20 turns  → Recent events
Long-term:   Session   → Persistent memories
```

#### Chaos & Fate
| File | Lines | Purpose |
|------|-------|---------|
| `chaos_system.py` | 1,307 | Moon cycles, sabbats, time effects |
| `fate_threads.py` | - | Fate thread tracking |
| `rune_intent.py` | - | Rune influence system |

**Chaos Factors:**
- Moon phase modifiers
- Time of day effects
- Location-based modifiers
- Action-based modifiers with cooldowns
- Narrative keyword detection

#### Character Systems
| File | Purpose |
|------|---------|
| `emotional_engine.py` | Per-character emotional states |
| `stress_system.py` | Stress accumulation and effects |
| `menstrual_cycle.py` | Female character cycle tracking |
| `soul_mechanics.py` | Soul/hugr system mechanics |

#### Game Mechanics
| File | Purpose |
|------|---------|
| `dice_system.py` | D&D 5E dice rolling |
| `dnd_rules_engine.py` | 5E mechanics implementation |
| `combat_system.py` | Combat handling |
| `inventory_system.py` | Item management |

#### Social & Narrative
| File | Purpose |
|------|---------|
| `relationship_graph.py` | NPC relationship tracking |
| `social_ledger.py` | Social standing and debts |
| `quest_causality.py` | Quest management |
| `mead_hall_system.py` | Mead hall simulation |

#### Infrastructure
| File | Purpose |
|------|---------|
| `rag_system.py` | Retrieval-augmented generation |
| `event_dispatcher.py` | Global event bus |
| `comprehensive_logging.py` | Logging system |

---

### 5. Yggdrasil Cognitive Architecture - [`yggdrasil/`](yggdrasil/)

**Norse Cosmology-Based AI Cognition System**

#### Core Router - [`router.py`](yggdrasil/router.py)

**Size:** 708 lines

```python
class YggdrasilAIRouter:
    - route_call(call_type, context)
    - prepare_character_data(character_id)
    - assemble_context(game_state)
    - store_memory(turn_data)
```

**Call Types:**
```python
class AICallType(Enum):
    DIALOGUE = "dialogue"
    NARRATION = "narration"
    COMBAT = "combat"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    CRAFTING = "crafting"
    REST = "rest"
    TRAVEL = "travel"
```

#### Nine Worlds Processors

| Realm | File | Cognitive Domain |
|-------|------|------------------|
| Midgard | `worlds/midgard.py` | Material world, primary gameplay |
| Asgard | `worlds/asgard.py` | Divine realm, fate decisions |
| Helheim | `worlds/helheim.py` | Death realm, memory retrieval |
| Jotunheim | `worlds/jotunheim.py` | Giant realm, chaos processing |
| Alfheim | `worlds/alfheim.py` | Elf realm, light/insight |
| Muspelheim | `worlds/muspelheim.py` | Fire realm, passion/conflict |
| Niflheim | `worlds/niflheim.py` | Ice realm, preservation |
| Svartalfheim | `worlds/svartalfheim.py` | Dwarf realm, crafting |
| Vanaheim | `worlds/vanaheim.py` | Vanir realm, nature magic |

#### Ravens (Memory & Thought)

| Raven | File | Purpose |
|-------|------|---------|
| Huginn | `ravens/huginn.py` | Thought, retrieval, reasoning |
| Muninn | (in cognition/) | Memory storage and recall |

#### Cognition Layer

| File | Purpose |
|------|---------|
| `cognition/huginn_advanced.py` | Advanced thought processing |
| `cognition/memory_orchestrator.py` | Memory coordination |
| `cognition/hierarchical_memory.py` | Tiered memory management |
| `cognition/domain_crosslinker.py` | Cross-domain linking |

---

### 6. Session Management - [`session/session_manager.py`](session/session_manager.py)

**Size:** 558 lines

**Key Classes:**
```python
@dataclass
class CharacterChanges:
    hp_change: int
    conditions: List[str]
    inventory_changes: Dict[str, int]
    xp_gained: int

@dataclass
class QuestProgress:
    quest_id: str
    stage: int
    objectives_completed: List[str]

@dataclass
class WorldStateChanges:
    location_changes: Dict[str, str]
    npc_state_changes: Dict[str, NPCState]

class SessionManager:
    - save_session(game_state)
    - load_session(session_id)
    - get_character_changes(session_id)
    - update_world_state(changes)
```

**Persistence Features:**
- YAML + JSON serialization
- Atomic writes for safety
- Conversation history (last 50 exchanges)
- Chaos factor persistence
- Character change tracking

---

### 7. Data Layer - [`data/`](data/)

#### Charts Directory - [`data/charts/`](data/charts/)

**100+ lore and data files including:**

| File | Purpose | Size |
|------|---------|------|
| `viking_values.yaml` | Cultural values | 27,223 chars |
| `elder_futhark.yaml` | Rune meanings | 15,800 chars |
| `gm_mindset.yaml` | GM personality | 32,185 chars |
| `fate_twists.yaml` | Narrative complications | 16,618 chars |
| `dnd_5e_rules.json` | 5E mechanics | 1,248,696 chars |
| `norse_gods.json` | Deity data | 7,021,961 chars |
| `viking_locations.json` | Location data | 108,646 chars |

#### Characters Directory - [`data/characters/`](data/characters/)

| Subdirectory | Purpose |
|--------------|---------|
| `player_characters/` | PC sheets |
| `npcs/` | NPC sheets |
| `mead_hall/` | Mead hall NPCs |
| `villains/` | Antagonists |
| `generated/` | Procedurally generated NPCs |

---

## Data Flow Architecture

### Turn Processing Pipeline

```
Player Input
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  main.py: game_loop()                                           │
│  - Parse input                                                  │
│  - Route to command handler or process_action                   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  YggdrasilEngine.process_action()                               │
│  1. Pre-turn updates (chaos, emotional, fate)                   │
│  2. Build continuity context packet                             │
│  3. Assemble prompt with charts and memory                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  PromptBuilder.build_narrator_prompt()                          │
│  - Load chart data (viking_values, gm_mindset, etc.)           │
│  - Build scene context (location, NPCs, weather)               │
│  - Inject memory (short/medium/long-term)                       │
│  - Add emotional atmosphere                                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  YggdrasilAIRouter.route_call()                                 │
│  - Determine call type (DIALOGUE, NARRATION, etc.)              │
│  - Prepare character data                                       │
│  - Route to appropriate AI client                               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  OpenRouterClient.complete()                                    │
│  - Build messages array                                          │
│  - Fit within context budget                                     │
│  - Call OpenRouter API                                           │
│  - Handle streaming response                                     │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  Response Processing                                             │
│  - Parse AI response                                             │
│  - Extract narrative content                                      │
│  - Update game state                                              │
│  - Store in memory system                                         │
│  - Update chaos factor                                            │
│  - Save session                                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  UI Display (main.py)                                            │
│  - Render narration with Rich console                            │
│  - Display character portraits                                    │
│  - Play voice output (if enabled)                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Design Patterns Used

| Pattern | Implementation | Purpose |
|---------|----------------|---------|
| **Orchestrator** | `YggdrasilEngine` | Central coordination of subsystems |
| **Dataclass State** | `GameState`, `GameContext`, `TurnMemory` | Immutable state snapshots |
| **Event-Driven** | `EventDispatcher` | Decoupled subsystem communication |
| **Circuit Breaker** | `OpenRouterClient` | AI failure handling |
| **Repository** | Chart loaders | Data access abstraction |
| **Strategy** | Multiple AI models | Flexible AI selection |
| **Builder** | `PromptBuilder` | Complex prompt construction |

---

## Strengths

1. **Comprehensive Error Handling** - Try/except wrapping throughout all subsystems
2. **Rich Domain Modeling** - Norse cosmology metaphors make code expressive and thematic
3. **Modular Subsystems** - 40+ independent systems with clear responsibilities
4. **Data-Driven Design** - Lore loaded from YAML/JSON, not hardcoded in Python
5. **Multi-Tier Memory** - Short/medium/long-term with AI summarization
6. **Flexible AI Integration** - Multiple models with fallback support
7. **Session Isolation** - Original character data never modified, changes tracked separately

---

## Architectural Concerns

### WARNING: File Size Issues

| File | Size | Concern |
|------|------|---------|
| `core/engine.py` | 298,399 chars | Extremely large, should be split |
| `main.py` | 202,125 chars | Large for entry point |
| `systems/chaos_system.py` | 51,588 chars | Could be modularized |

### SUGGESTION: Complexity Management

- The `YggdrasilEngine` class has too many responsibilities
- Consider extracting into separate managers (AIManager, StateManager, etc.)
- Some methods exceed 50-line guideline from AGENTS.md

### SUGGESTION: Documentation

- Each subsystem has AI_HINTS.md, DEBUGGING.md, etc. (good practice)
- Consider consolidating into a single architecture document

---

## Recommendations

1. **Refactor engine.py** - Split into 5-7 smaller modules by responsibility
2. **Add interface abstractions** - Define protocols for major subsystems
3. **Consider dependency injection** - Reduce tight coupling between engine and subsystems
4. **Add integration tests** - Test subsystem interactions
5. **Document data contracts** - YAML/JSON schema validation

---

## Conclusion

The Norse Saga Engine is a well-architected AI-driven RPG system with sophisticated subsystems for memory, emotion, chaos, and Norse cosmological simulation. The codebase demonstrates strong domain modeling and comprehensive error handling. The primary architectural concern is the size of core files (especially `engine.py`), which could benefit from modularization. The system successfully achieves its goal of invisible mechanics with emergent storytelling.

---

*Report generated by Runa Gridweaver Freyjasdottir, Technomancer of the North*