# norse_saga.py — INTERFACE.md

## Class: `NorseSagaCognition`

Game-specific cognitive system for Norse Saga Engine.

Provides high-level interfaces for:
- Character memories and personalities
- World knowledge and lore
- Dialogue generation with context
- Quest and event processing
- Combat AI decisions

### `start_session(session_id)`
Start a new game session.

### `end_session()`
End the current game session.

### `store_character_memory(character_id, memory_content, memory_type, importance, related_characters, location)`
Store a memory for a character.

Args:
    character_id: Character's unique ID
    memory_content: The memory content
    memory_type: Type (experience, interaction, knowledge, emotion)
    importance: 1-10 scale
    related_characters: Other characters involved
    location: Where the memory occurred
    
Returns:
    Memory node ID

### `recall_character_memories(character_id, query, memory_type, limit)`
Recall memories for a character.

Args:
    character_id: Character's unique ID
    query: Optional search query
    memory_type: Filter by type
    limit: Maximum memories
    
Returns:
    List of memory dictionaries

### `get_character_context(character_id, situation, include_relationships)`
Build comprehensive context for a character.

Args:
    character_id: Character's unique ID
    situation: Current situation description
    include_relationships: Include relationship data
    
Returns:
    Context dictionary for LLM prompts

### `generate_dialogue(npc_id, player_input, conversation_history, situation)`
Generate NPC dialogue response.

Args:
    npc_id: NPC's character ID
    player_input: What the player said
    conversation_history: Previous exchanges
    situation: Current situation
    
Returns:
    Dialogue response with metadata

### `store_world_fact(fact, category, location, importance)`
Store a fact about the game world.

Args:
    fact: The fact content
    category: Category (lore, geography, history, rules)
    location: Related location
    importance: 1-10 scale
    
Returns:
    Fact node ID

### `query_world_knowledge(query, category)`
Query world knowledge.

Args:
    query: Search query
    category: Optional category filter
    
Returns:
    List of relevant facts

### `log_event(event_type, description, participants, location, importance)`
Log a game event.

Args:
    event_type: Type of event
    description: Event description
    participants: Characters involved
    location: Where it happened
    importance: 1-10 scale
    
Returns:
    Event node ID

### `process_quest_update(quest_id, update_type, details)`
Process a quest update.

Args:
    quest_id: Quest identifier
    update_type: Type of update (start, progress, complete, fail)
    details: Update details
    
Returns:
    Processing result

### `get_combat_decision(combatant_id, combat_state, available_actions)`
Get AI decision for combat.

Args:
    combatant_id: The combatant's ID
    combat_state: Current combat state
    available_actions: List of possible actions
    
Returns:
    Decision with action and reasoning

### `get_stats()`
Get system statistics.

### `persist()`
Persist all data to disk.

### `heal()`
Self-healing operation.

## Module Functions

### `create_norse_saga_cognition(llm_callable, data_path)`
Factory function to create Norse Saga cognition system.

Args:
    llm_callable: LLM function
    data_path: Data storage path
    **kwargs: Additional configuration
    
Returns:
    Configured NorseSagaCognition instance

---
**Contract Version**: 1.0 | v8.0.0
