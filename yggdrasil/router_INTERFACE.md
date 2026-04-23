# router.py — INTERFACE.md

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

## Class: `YggdrasilAIRouter`

The unified AI router. ALL AI calls MUST go through here.

This ensures:
- Full character data is always sent
- Viking social protocols are applied
- Chaos factor influences results
- Results are logged
- Wyrd is updated

### `prepare_character_data(character, is_player)`
Prepare complete character data for AI.

### `prepare_context(call_type, game_state, involved_npcs, additional_context)`
Prepare complete context for an AI call.

This gathers ALL relevant data for the AI.

### `route_call(call_type, prompt, game_state, involved_npcs, additional_context, system_prompt, use_prompt_builder)`
Route an AI call through Yggdrasil.

This is the ONLY method that should call the LLM.

### `generate_dialogue(npc, game_state, player_action, use_prompt_builder)`
Generate NPC dialogue.

### `generate_narration(game_state, action, npcs, use_prompt_builder)`
Generate scene narration.

### `generate_combat_narration(game_state, combat_results, npcs)`
Generate combat narration with dice results.

### `generate_turn_summary(game_state, player_action, narrative_result)`
Generate a turn summary for memory.

## Module Functions

### `create_yggdrasil_router(llm_callable, data_path, comprehensive_logger, wyrd_system, enhanced_memory, prompt_builder, yggdrasil_cognition)`
Create a Yggdrasil AI router.

---
**Contract Version**: 1.0 | v8.0.0
