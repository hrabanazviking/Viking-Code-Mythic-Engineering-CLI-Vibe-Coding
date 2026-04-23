# router_enhanced.py — INTERFACE.md

## Class: `AICallType`

Types of AI calls that can be routed.

## Class: `CharacterDataFeed`

Complete character data prepared for AI consumption.

This ensures AI ALWAYS has full character information.

### `to_ai_text()`
Convert to text for AI prompt.

### `from_character_dict(cls, char)`
Create from a character dictionary.

## Class: `AICallContext`

Complete context for an AI call.

Everything the AI needs to know is packaged here.

### `to_prompt_context()`
Generate context text for AI prompt.

## Class: `EnhancedYggdrasilAIRouter`

Enhanced AI router with prompt_builder integration.

This router:
1. Uses prompt_builder for all prompt construction
2. Integrates Yggdrasil cognitive context
3. Supports all AI call types with enhanced context
4. Maintains backward compatibility with existing router

### `prepare_context(call_type, game_state, involved_npcs, additional_context)`
Prepare complete context for an AI call.

### `route_call(call_type, prompt, game_state, involved_npcs, additional_context, system_prompt, use_prompt_builder)`
Route an AI call through enhanced Yggdrasil.

This method can use prompt_builder for enhanced prompt construction.

### `generate_dialogue(npc, game_state, player_action, use_prompt_builder)`
Generate NPC dialogue.

### `generate_narration(game_state, action, npcs, use_prompt_builder)`
Generate scene narration.

### `generate_character_voice(character, game_state, situation, use_prompt_builder)`
Generate dialogue in a specific character's voice.

### `generate_combat_narration(game_state, combat_results, npcs, use_prompt_builder)`
Generate combat narration with dice results.

### `generate_turn_summary(game_state, player_action, narrative_result, use_prompt_builder)`
Generate a turn summary for memory.

## Module Functions

### `create_enhanced_yggdrasil_router(llm_callable, prompt_builder, data_path, comprehensive_logger, wyrd_system, enhanced_memory, yggdrasil_cognition)`
Create an enhanced Yggdrasil AI router with prompt_builder integration.

---
**Contract Version**: 1.0 | v8.0.0
