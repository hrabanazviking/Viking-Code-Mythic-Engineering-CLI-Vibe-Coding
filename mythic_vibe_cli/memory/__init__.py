"""Conversation memory & compaction (PH-15).

Persists provider conversations and compacts long histories so
context windows stay well-used without losing the reasoning trail.

Storage layout:

    <root>/mythic/ai/conversations/<conversation_id>.json
    <root>/mythic/ai/summaries/<conversation_id>.md
    <root>/mythic/ai/summaries/<conversation_id>.json

Conversation IDs follow the existing Mythic style: ``CV-<6 hex>``.
"""

from __future__ import annotations

__all__: list[str] = []
