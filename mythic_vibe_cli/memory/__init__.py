"""Conversation memory, compaction, and the Reforge SQLite spine.

Persists provider conversations and compacts long histories so
context windows stay well-used without losing the reasoning trail.
Reforge Phase 5 adds a project-level SQLite memory spine for shell
resume questions and handoff continuity.

Storage layout:

    <root>/mythic/ai/conversations/<conversation_id>.json
    <root>/mythic/ai/summaries/<conversation_id>.md
    <root>/mythic/ai/summaries/<conversation_id>.json
    <root>/.mythic/memory.sqlite

Conversation IDs follow the existing Mythic style: ``CV-<6 hex>``.
"""

from __future__ import annotations

__all__: list[str] = []
