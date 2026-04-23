# wyrd_system.py — INTERFACE.md

## Class: `WellType`

The three sacred wells.

## Class: `NornType`

The three Norns who tend the wells.

## Class: `WyrdThread`

A single thread of fate.

## Class: `WellContents`

Contents of a sacred well.

## Class: `SacredWell`

A single sacred well that stores threads of fate.

### `add_thread(content, thread_type, importance, tags, characters, location, turn_number, norn_source)`
Add a new thread to the well.

### `get_thread(thread_id)`
Get a specific thread.

### `get_threads_by_type(thread_type)`
Get all threads of a specific type.

### `get_threads_by_tag(tag)`
Get all threads with a specific tag.

### `get_threads_by_character(character)`
Get all threads involving a character.

### `get_recent_threads(count)`
Get most recent threads.

### `get_important_threads(min_importance)`
Get threads above importance threshold.

### `link_threads(thread_id1, thread_id2)`
Link two threads together.

## Class: `Norn`

A Norn who tends a sacred well and weaves fate.

### `weave(content, thread_type, importance)`
Weave a new thread into the well.

### `divine(query)`
Divine relevant threads based on a query.

## Class: `WyrdSystem`

The complete Wyrd system managing all three sacred wells
and the three Norns who tend them.

All game events flow through this system:
- Past events are recorded in Urðarbrunnr
- Current state is maintained in Mímisbrunnr
- Prophecies and possibilities go to Hvergelmir

### `record_past_event(event_description, event_type, importance, characters, location, turn_number, tags)`
Record a past event in the Well of Fate.

### `record_turn_summary(turn_number, player_action, narrative_result, characters_involved, location, ai_summary)`
Record a complete turn summary.

### `get_past_events(count)`
Get recent past events.

### `get_character_history(character)`
Get all past events involving a character.

### `update_current_state(state_key, state_value, importance)`
Update current state in the Well of Wisdom.

### `store_knowledge(knowledge, knowledge_type, importance, tags)`
Store knowledge in the Well of Wisdom.

### `store_character_data(character_id, character_data, importance)`
Store character data for AI consumption.

### `get_current_knowledge(query)`
Divine current knowledge related to a query.

### `store_prophecy(prophecy, probability, related_to, importance)`
Store a prophecy or prediction.

### `store_potential_outcome(action, possible_outcomes, importance)`
Store potential outcomes for an action.

### `get_prophecies(character)`
Get prophecies, optionally filtered by character.

### `weave_fate(past_thread_id, present_thread_id, future_thread_id)`
Weave threads from all three wells together,
creating a complete fate tapestry.

### `divine_fate(query)`
Divine fate across all three wells.

### `get_context_for_ai(query, max_past, max_present, max_future)`
Get context from all three wells for AI consumption.
This is the primary interface for feeding the AI.

### `get_statistics()`
Get statistics about the wells.

## Module Functions

### `create_wyrd_system(storage_path, llm_callable)`
Create a Wyrd system instance.

---
**Contract Version**: 1.0 | v8.0.0
