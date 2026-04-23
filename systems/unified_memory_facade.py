"""
Unified Memory Facade (P3-3)
============================

Composite wrapper that presents a single ``UnifiedMemoryManager`` API while
internally delegating to two complementary memory subsystems:

* **EnhancedMemoryManager** — fast in-memory tiers (short/medium-term
  summaries, signals, character/location/relationship event lists).
  Authoritative for active-session context; data lives only for the
  duration of the session.

* **CharacterMemoryRAG** — YAML-persisted character memory store.
  Previously orphaned (0 call sites in engine.py).  Now receives
  write-through for significant memories (importance >= 3) so that
  character histories survive across sessions.

All existing ``self.enhanced_memory`` call sites in ``engine.py`` work
unchanged — the facade is a drop-in replacement that exposes the same
method signatures and properties.

New capabilities surfaced through the facade:
* ``search_memories(query)`` — full-text search across persistent RAG tier
* ``get_character_context(character_id, include_persistent=True)`` — unified
  context merging in-memory + persistent tiers
* ``get_character_development(character_id)`` — full arc: events + backstory

Integration point:
    Replace ``create_enhanced_memory_manager(...)`` with
    ``create_unified_memory_manager(...)`` in ``core/engine.py``.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from systems.enhanced_memory import (
    EnhancedMemoryManager,
    create_enhanced_memory_manager,
)
from systems.character_memory_rag import CharacterMemoryRAG, create_memory_system

logger = logging.getLogger(__name__)


class UnifiedMemoryManager:
    """
    Drop-in replacement for ``EnhancedMemoryManager`` that transparently
    adds YAML persistence via ``CharacterMemoryRAG``.

    All method signatures and properties mirror ``EnhancedMemoryManager``
    exactly so engine.py call sites require no changes.
    """

    def __init__(self, llm_callable: Any = None, data_path: str = "data") -> None:
        # Primary in-memory tier
        self._enhanced: EnhancedMemoryManager = create_enhanced_memory_manager(
            llm_callable=llm_callable,
            data_path=data_path,
        )

        # Persistent RAG tier — non-fatal if unavailable
        self._rag: Optional[CharacterMemoryRAG] = None
        try:
            self._rag = create_memory_system(data_path)
        except Exception as exc:
            logger.warning("CharacterMemoryRAG init failed (non-fatal): %s", exc)

    # ── Session lifecycle ────────────────────────────────────────────────────

    def start_session(
        self,
        session_id: str,
        player_character: Any,
        starting_location: str,
    ) -> None:
        self._enhanced.start_session(session_id, player_character, starting_location)

    # ── Turn processing ──────────────────────────────────────────────────────

    def process_turn(
        self,
        turn_number: int,
        player_input: str,
        narrative: str,
        game_state: Any,
    ) -> Any:
        return self._enhanced.process_turn(
            turn_number, player_input, narrative, game_state
        )

    # ── Memory write paths ───────────────────────────────────────────────────

    def add_character_memory(
        self,
        character_id: str,
        event_type: str,
        description: str,
        importance: int = 5,
    ) -> None:
        """Write to in-memory tier; persist to RAG for important events."""
        self._enhanced.add_character_memory(character_id, event_type, description, importance)

        if self._rag is not None and importance >= 3:
            try:
                self._rag.add_memory(
                    character_id=character_id,
                    character_name=character_id,
                    memory_type=event_type,
                    content=description,
                    importance=importance,
                )
            except Exception as exc:
                logger.debug("RAG write-through failed for %s: %s", character_id, exc)

    def add_location_memory(
        self,
        location_id: str,
        event_type: str,
        description: str,
        importance: int = 5,
    ) -> None:
        self._enhanced.add_location_memory(location_id, event_type, description, importance)

    def add_relationship_memory(
        self,
        character1: str,
        character2: str,
        change_type: str,
        description: str,
    ) -> None:
        self._enhanced.add_relationship_memory(character1, character2, change_type, description)
        if self._rag is not None:
            try:
                self._rag.add_memory(
                    character_id=character1,
                    character_name=character1,
                    memory_type="relationship",
                    content=f"{character2}: {description}",
                    related_characters=[character2],
                    importance=3,
                )
            except Exception as exc:
                logger.debug("RAG relationship write-through failed: %s", exc)

    def add_condition_event_memory(self, *args: Any, **kwargs: Any) -> None:
        self._enhanced.add_condition_event_memory(*args, **kwargs)

    # ── Context read paths ───────────────────────────────────────────────────

    def get_short_term_context_for_ai(self, max_items: int = 12) -> str:
        return self._enhanced.get_short_term_context_for_ai(max_items)

    def get_medium_term_context_for_ai(self, max_items: int = 18) -> str:
        return self._enhanced.get_medium_term_context_for_ai(max_items)

    def get_event_signal_context(self, max_items: int = 20) -> str:
        return self._enhanced.get_event_signal_context(max_items)

    def get_full_context_for_ai(
        self,
        game_state: Any,
        max_items: int = 15,
        scene_type: Optional[str] = None,
    ) -> str:
        return self._enhanced.get_full_context_for_ai(game_state, max_items, scene_type)

    def get_character_context(
        self,
        character_id: str,
        max_memories: int = 10,
        include_persistent: bool = True,
    ) -> str:
        """
        Unified context: in-memory recent events + persistent backstory/history.

        Falls back gracefully if either tier is unavailable.
        """
        parts: List[str] = []

        try:
            in_mem = self._enhanced.get_character_context(character_id, max_memories)
            if in_mem:
                parts.append(in_mem)
        except Exception as exc:
            logger.debug("In-memory character context failed: %s", exc)

        if include_persistent and self._rag is not None:
            try:
                persistent = self._rag.build_context_for_character(
                    character_id, max_memories=max_memories
                )
                if persistent:
                    parts.append(persistent)
            except Exception as exc:
                logger.debug("Persistent character context failed: %s", exc)

        return "\n".join(parts)

    def get_location_context(self, location_id: str, max_memories: int = 10) -> str:
        return self._enhanced.get_location_context(location_id, max_memories)

    # ── New unified methods (not on EnhancedMemoryManager) ───────────────────

    def search_memories(
        self,
        query: str,
        character_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Full-text search across the persistent RAG tier."""
        if self._rag is None:
            return []
        try:
            return self._rag.search_memories(query, character_id, limit)
        except Exception as exc:
            logger.debug("search_memories failed: %s", exc)
            return []

    def get_character_development(self, character_id: str) -> Dict[str, Any]:
        """Full development arc: recent in-memory events + persistent backstory."""
        result: Dict[str, Any] = {
            "recent_events": [],
            "backstory": [],
            "interaction_history": [],
        }
        try:
            result["recent_events"] = self._enhanced.get_recent_events_for_character(
                character_id, 30
            )
        except Exception as exc:
            logger.debug("get_recent_events_for_character failed: %s", exc)

        if self._rag is not None:
            try:
                result["backstory"] = self._rag.get_backstory(character_id)
                result["interaction_history"] = self._rag.get_memories(
                    character_id, limit=50
                )
            except Exception as exc:
                logger.debug("RAG character development read failed: %s", exc)

        return result

    # ── Identity drift (delegates unchanged) ─────────────────────────────────

    def check_identity_drift(
        self,
        character_id: str,
        current_turn: int,
        base_traits: Optional[Any] = None,
        config: Optional[Any] = None,
    ) -> Any:
        return self._enhanced.check_identity_drift(
            character_id, current_turn, base_traits, config
        )

    def get_drift_history(self, character_id: str) -> Any:
        return self._enhanced.get_drift_history(character_id)

    def get_recent_events_for_character(self, character_id: str, count: int) -> Any:
        return self._enhanced.get_recent_events_for_character(character_id, count)

    def collect_event_signals(self, *args: Any, **kwargs: Any) -> Any:
        return self._enhanced.collect_event_signals(*args, **kwargs)

    # ── Property delegation (engine.py accesses these directly) ─────────────

    @property
    def llm(self) -> Any:
        return self._enhanced.llm

    @llm.setter
    def llm(self, value: Any) -> None:
        self._enhanced.llm = value

    @property
    def summarizer(self) -> Any:
        return self._enhanced.summarizer

    @property
    def character_memories(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._enhanced.character_memories

    @property
    def location_memories(self) -> Dict[str, List[Dict[str, Any]]]:
        return self._enhanced.location_memories

    @property
    def relationship_memories(self) -> Any:
        return self._enhanced.relationship_memories

    @property
    def event_signals(self) -> List[Dict[str, Any]]:
        return self._enhanced.event_signals

    # ── RAG access (for callers that want the persistent tier directly) ───────

    @property
    def rag(self) -> Optional[CharacterMemoryRAG]:
        """Direct access to the persistent RAG tier, if available."""
        return self._rag


def create_unified_memory_manager(
    llm_callable: Any = None,
    data_path: str = "data",
) -> UnifiedMemoryManager:
    """Factory matching ``create_enhanced_memory_manager`` signature."""
    return UnifiedMemoryManager(llm_callable=llm_callable, data_path=data_path)
