"""Scored retrieval for narrative memory context selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import math
import yaml


@dataclass
class ScoredMemory:
    """Memory event with retrieval score and provenance metadata."""

    score: float
    recency: float
    relevance: float
    emotional_resonance: float
    entity_overlap: float
    location_overlap: float
    provenance: str
    event: Dict[str, Any]


class MemoryRetrievalScorer:
    """Ranks memory events using weighted factors and decay profiles."""

    def __init__(self, data_path: str = "data") -> None:
        self.data_path = Path(data_path)
        self.weights = self._load_yaml("charts/memory_scoring_weights.yaml", {}).get("weights", {})
        self.selection = self._load_yaml("charts/memory_scoring_weights.yaml", {}).get("selection", {})
        self.decay_profiles = self._load_yaml("charts/memory_decay_profiles.yaml", {}).get("profiles", {})

    def select_top_memories(
        self,
        events: List[Dict[str, Any]],
        query: str,
        location_id: str,
        npcs_present: List[Dict[str, Any]],
        top_k: int | None = None,
    ) -> List[ScoredMemory]:
        """Muninn weighs memory threads and returns top-k with provenance."""
        if not events:
            return []

        limit = int(top_k or self.selection.get("default_top_k", 12))
        scored = [
            self._score_event(
                event=item,
                query=query,
                location_id=location_id,
                npcs_present=npcs_present,
                event_index=index,
                total_events=len(events),
            )
            for index, item in enumerate(events)
        ]
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def _score_event(
        self,
        event: Dict[str, Any],
        query: str,
        location_id: str,
        npcs_present: List[Dict[str, Any]],
        event_index: int,
        total_events: int,
    ) -> ScoredMemory:
        recency = self._recency_score(event_index=event_index, total_events=total_events)
        relevance = self._relevance_score(query=query, event=event)
        emotional = self._emotional_score(event=event)
        overlap_entity = self._entity_overlap_score(event=event, npcs_present=npcs_present)
        overlap_location = self._location_overlap_score(event=event, location_id=location_id)

        total = (
            recency * float(self.weights.get("recency", 0.35))
            + relevance * float(self.weights.get("relevance", 0.30))
            + emotional * float(self.weights.get("emotional_resonance", 0.20))
            + overlap_entity * float(self.weights.get("entity_overlap", 0.10))
            + overlap_location * float(self.weights.get("location_overlap", 0.05))
        )

        return ScoredMemory(
            score=total,
            recency=recency,
            relevance=relevance,
            emotional_resonance=emotional,
            entity_overlap=overlap_entity,
            location_overlap=overlap_location,
            provenance=f"turn:{event.get('timestamp', '?')}",
            event=event,
        )

    def _recency_score(self, event_index: int, total_events: int) -> float:
        standard = self.decay_profiles.get("standard", {})
        half_life = float(standard.get("half_life_turns", 40))
        floor = float(standard.get("floor", 0.1))
        age = max(0, (total_events - 1) - event_index)
        decay = math.exp(-math.log(2) * age / max(1.0, half_life))
        return max(floor, min(1.0, decay))

    def _relevance_score(self, query: str, event: Dict[str, Any]) -> float:
        text = f"{event.get('input', '')} {event.get('response', '')}".lower()
        terms = [token for token in (query or "").lower().split() if len(token) >= 3]
        if not terms:
            return 0.5
        hits = sum(1 for token in terms if token in text)
        return min(1.0, hits / max(1, len(terms)))

    def _emotional_score(self, event: Dict[str, Any]) -> float:
        text = f"{event.get('input', '')} {event.get('response', '')}".lower()
        markers = ["blood", "oath", "love", "fear", "rage", "grief", "honor", "shame", "death"]
        hits = sum(1 for marker in markers if marker in text)
        return min(1.0, hits / 3.0)

    def _entity_overlap_score(self, event: Dict[str, Any], npcs_present: List[Dict[str, Any]]) -> float:
        text = f"{event.get('input', '')} {event.get('response', '')}".lower()
        names = []
        for npc in npcs_present:
            if isinstance(npc, dict):
                name = npc.get("identity", {}).get("name", "") if isinstance(npc.get("identity", {}), dict) else ""
                if isinstance(name, str) and name:
                    names.append(name.lower())
        if not names:
            return 0.0
        hits = sum(1 for name in names if name in text)
        return min(1.0, hits / max(1, len(names)))

    def _location_overlap_score(self, event: Dict[str, Any], location_id: str) -> float:
        if not location_id:
            return 0.0
        text = f"{event.get('input', '')} {event.get('response', '')}".lower()
        return 1.0 if location_id.lower().replace("_", " ") in text else 0.0

    def _load_yaml(self, relative_path: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        file_path = self.data_path / relative_path
        if not file_path.exists():
            return fallback
        with file_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or fallback
        return loaded if isinstance(loaded, dict) else fallback
