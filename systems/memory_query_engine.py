"""
Memory Query Engine
===================

Phase 4.1 of the Memory Consolidation Plan.

Provides a unified, structured query surface over the Muninn memory raven,
translating dot-notation filter predicates and semantic queries into
Muninn.retrieve() calls.  All subsystems that need to read memory should
go through this class rather than calling Muninn directly.

Usage::

    from systems.memory_query_engine import MemoryQueryEngine

    engine = MemoryQueryEngine(muninn_instance)

    ctx  = engine.query_turn_context(turn_number=42)
    char = engine.query_character_development("sigrid_ironweave")
    world = engine.query_world_state(location="hedeby")
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _get_nested(obj: Any, dotted_key: str) -> Any:
    """
    Traverse a nested mapping using a dot-separated key.

    Returns *None* if any intermediate key is absent or the value is
    not a mapping.

    Examples::

        _get_nested({"game_timestamp": {"turn": 5}}, "game_timestamp.turn")
        # → 5

        _get_nested({"a": 1}, "b.c")
        # → None
    """
    parts = dotted_key.split(".")
    current = obj
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


class MemoryQueryEngine:
    """
    Unified query system for all memory needs.

    Wraps a ``Muninn`` instance and translates structured queries into
    ``Muninn.retrieve()`` calls, applying additional filter predicates
    that Muninn's own API cannot express (e.g. nested-field matching,
    list-membership checks).

    The returned results are plain ``dict`` objects (node content only),
    not ``MemoryNode`` instances, so callers remain decoupled from the
    Muninn storage layer.
    """

    MAX_RESULTS: int = 100

    def __init__(self, muninn: Any) -> None:
        """
        Args:
            muninn: A ``Muninn`` instance, or any object whose
                ``retrieve(memory_type, top_k)`` signature is compatible
                with the Muninn raven API.
        """
        self.muninn = muninn

    # ------------------------------------------------------------------ #
    # Public query interface                                               #
    # ------------------------------------------------------------------ #

    def query_turn_context(
        self,
        turn_number: int,
        limit: Optional[int] = None,
        game_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict]]:
        """
        Return complete context for a specific turn.

        T3-B: if *game_state* is provided and *limit* is not explicitly set,
        compute an elastic window size from chaos_factor, emotional intensity,
        and the last action text.

        Returns::

            {
                "events":         [... turn_event records ...],
                "emotional_state": [... emotional_state records ...],
                "scene_context":  [... scene_context records ...],
            }
        """
        # T3-B: elastic window for limit
        if limit is None and game_state:
            try:
                from systems.memory_hardening import ElasticWindowCalculator, infer_scene_type
                scene_type = infer_scene_type(game_state.get("last_action", ""))
                limit = ElasticWindowCalculator().compute(
                    chaos_factor=int(game_state.get("chaos_factor", 5)),
                    dominant_emotion_intensity=float(
                        game_state.get("dominant_emotion_intensity", 0.0)
                    ),
                    scene_type=scene_type,
                )
            except Exception as exc:
                logger.warning("ElasticWindowCalculator failed in query_turn_context: %s", exc)
        limit = limit or 15

        filters: Dict[str, Any] = {"game_timestamp.turn": turn_number}
        return {
            "events": self._query("turn_event", filters=filters, limit=limit),
            "emotional_state": self._query("emotional_state", filters=filters, limit=limit),
            "scene_context": self._query("scene_context", filters=filters, limit=limit),
        }

    def query_character_development(self, character_id: str) -> Dict[str, Any]:
        """
        Return comprehensive character development history.

        Returns::

            {
                "skill_progression":    [... records ...],
                "relationship_evolution": [... records ...],
                "emotional_patterns":   [{"emotion": str, "count": int}, ...],
                "narrative_arc":        [... milestone records sorted by turn ...],
            }
        """
        char_filter: Dict[str, Any] = {"involved_characters": character_id}
        return {
            "skill_progression": self._query(
                "skill_progression", filters=char_filter
            ),
            "relationship_evolution": self._query(
                "relationship_update", filters=char_filter
            ),
            "emotional_patterns": self.analyze_emotional_patterns(character_id),
            "narrative_arc": self.extract_character_arc(character_id),
        }

    def query_world_state(
        self, location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Return comprehensive world state, optionally scoped to a location.

        Args:
            location: If provided, world events are filtered to those
                whose ``location_context`` matches this value.

        Returns::

            {
                "current_events":         [... last 10 world_event records ...],
                "faction_status":         [... faction_event records ...],
                "cultural_climate":       [... cultural_shift records ...],
                "environmental_conditions": [... environmental_state records ...],
            }
        """
        filters: Dict[str, Any] = {}
        if location:
            filters["location_context"] = location

        return {
            "current_events": self._query(
                "world_event",
                filters=filters,
                sort_by="game_timestamp.turn",
                limit=10,
            ),
            "faction_status": self.query_faction_dynamics(),
            "cultural_climate": self.query_cultural_shifts(),
            "environmental_conditions": self.query_environmental_state(),
        }

    # ------------------------------------------------------------------ #
    # Analytical helpers                                                   #
    # ------------------------------------------------------------------ #

    def analyze_emotional_patterns(self, character_id: str) -> List[Dict]:
        """
        Tally recurring emotional states associated with *character_id*.

        Returns a list of ``{"emotion": str, "count": int}`` dicts sorted
        by count descending.
        """
        raw = self._query(
            "emotional_state",
            filters={"involved_characters": character_id},
        )
        tally: Dict[str, int] = {}
        for record in raw:
            emotion = (
                record.get("emotion")
                or record.get("state")
                or "unknown"
            )
            tally[str(emotion)] = tally.get(str(emotion), 0) + 1

        return sorted(
            [{"emotion": e, "count": c} for e, c in tally.items()],
            key=lambda x: x["count"],
            reverse=True,
        )

    def extract_character_arc(self, character_id: str) -> List[Dict]:
        """
        Return narrative milestones for *character_id*, sorted by turn.

        Milestones are stored in Muninn under memory_type
        ``"narrative_milestone"`` with an ``involved_characters`` list
        and a ``game_timestamp.turn`` field.
        """
        milestones = self._query(
            "narrative_milestone",
            filters={"involved_characters": character_id},
        )
        return sorted(
            milestones,
            key=lambda x: _get_nested(x, "game_timestamp.turn") or 0,
        )

    def query_faction_dynamics(self) -> List[Dict]:
        """Return recent faction dynamic records, newest last."""
        return self._query(
            "faction_event", limit=20, sort_by="game_timestamp.turn"
        )

    def query_cultural_shifts(self) -> List[Dict]:
        """Return recent cultural shift records, newest last."""
        return self._query(
            "cultural_shift", limit=20, sort_by="game_timestamp.turn"
        )

    def query_environmental_state(self) -> List[Dict]:
        """Return recent environmental condition records, newest last."""
        return self._query(
            "environmental_state", limit=10, sort_by="game_timestamp.turn"
        )

    def query_emotional_state(
        self, turn_number: int
    ) -> Dict[str, Dict[str, float]]:
        """
        Aggregate emotional states at *turn_number* into a per-character mapping.

        Returns::

            {
                "sigrid_ironweave": {"grief": 2.0, "fury": 1.0},
                "bjorn_hammerhand": {"pride": 1.5},
                ...
            }

        Intensity values are summed when multiple records share the same
        character + emotion pair for the same turn.
        """
        records = self._query(
            "emotional_state",
            filters={"game_timestamp.turn": turn_number},
        )
        result: Dict[str, Dict[str, float]] = {}
        for rec in records:
            for char_id in rec.get("involved_characters") or []:
                if char_id not in result:
                    result[char_id] = {}
                emotion = (
                    rec.get("emotion") or rec.get("state") or "neutral"
                )
                intensity = float(rec.get("intensity", 1.0))
                result[char_id][emotion] = (
                    result[char_id].get(emotion, 0.0) + intensity
                )
        return result

    def query_narrative_state(self) -> Dict[str, Any]:
        """
        Return the most recent narrative state snapshot.

        Expects Muninn nodes of memory_type ``"narrative_state"`` with at
        least ``current_phase`` and ``active_themes`` fields.

        Falls back to a safe default when no records exist::

            {"current_phase": "unknown", "active_themes": []}
        """
        records = self._query(
            "narrative_state", sort_by="game_timestamp.turn", limit=20
        )
        if records:
            latest = records[-1]  # list is sorted ascending by turn
            return {
                "current_phase": latest.get("current_phase", "unknown"),
                "active_themes": latest.get("active_themes") or [],
            }
        return {"current_phase": "unknown", "active_themes": []}

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _query(
        self,
        memory_type: str,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        Low-level query against Muninn.

        Args:
            memory_type: Muninn memory_type label (e.g. ``"turn_event"``).
            filters: Flat dict whose keys may use dot-notation to address
                nested fields inside node content.  A scalar expected value
                must match exactly; if the stored value is a list, membership
                is checked instead.
            sort_by: Dot-notation key used to sort results ascending.
            limit: Maximum number of results to return.

        Returns:
            List of content dicts (MemoryNode.content), never MemoryNodes.
        """
        top_k = min(limit if limit is not None else self.MAX_RESULTS, self.MAX_RESULTS)

        try:
            nodes = self.muninn.retrieve(memory_type=memory_type, top_k=top_k)
        except Exception:
            logger.exception(
                "MemoryQueryEngine._query failed for memory_type=%r", memory_type
            )
            return []

        results: List[Dict] = []
        for node in nodes:
            content = node.content if hasattr(node, "content") else node
            if not isinstance(content, dict):
                continue
            if filters and not self._matches(content, filters):
                continue
            results.append(content)

        if sort_by:
            results.sort(key=lambda x: _get_nested(x, sort_by) or 0)

        return results[:top_k]

    @staticmethod
    def _matches(content: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Return ``True`` when *content* satisfies **all** filter predicates.

        For each ``key → expected`` pair in *filters*:

        * The key may be dot-notation (e.g. ``"game_timestamp.turn"``).
        * If the resolved value is a list, *expected* must be a member.
        * Otherwise *expected* must equal the resolved value exactly.
        * A missing key always returns ``False``.
        """
        for key, expected in filters.items():
            actual = _get_nested(content, key)
            if actual is None:
                return False
            if isinstance(actual, list):
                if expected not in actual:
                    return False
            else:
                if actual != expected:
                    return False
        return True
