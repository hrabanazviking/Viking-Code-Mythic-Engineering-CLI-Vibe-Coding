# deep_integration.py — INTERFACE.md

## Class: `RealmRole`

The specific role each realm plays in processing.

## Class: `RealmProcessingResult`

Result from a single realm's AI processing.

## Class: `CognitiveSession`

A complete cognitive processing session through all realms.

## Class: `DeepYggdrasilIntegration`

Deep integration layer connecting Yggdrasil to NorseSagaEngine.

Each realm makes a SEPARATE AI call with role-specific prompts.

### `process_full_pipeline(query, game_context)`
Process a query through ALL nine realms with separate AI calls.

Args:
    query: The player's input or query
    game_context: Current game state and context
    
Returns:
    CognitiveSession with results from all realms

### `process_dialogue(npc_id, npc_data, player_input, conversation_history, game_context)`
Generate NPC dialogue with full realm processing.

Args:
    npc_id: NPC identifier
    npc_data: Full NPC data dict
    player_input: What the player said
    conversation_history: Previous exchanges
    game_context: Current game state
    
Returns:
    NPC dialogue response

### `process_action(action, game_state, characters_present)`
Process a player action with full realm processing.

Args:
    action: The player's action
    game_state: Current game state
    characters_present: NPCs in the scene
    
Returns:
    Narrative result of the action

### `get_stats()`
Get integration statistics.

## Module Functions

### `create_deep_integration(llm_callable, data_path, engine)`
Create a deep Yggdrasil integration instance.

---
**Contract Version**: 1.0 | v8.0.0
