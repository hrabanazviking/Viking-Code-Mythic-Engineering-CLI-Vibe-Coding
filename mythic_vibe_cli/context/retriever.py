"""Relevance-ranked retriever over the knowledge graph (PH-05 slice 5.3).

Given a query (a list of tags / keywords), :func:`rank_entities`
returns every matching entity scored by:

1. Tag overlap — sum of ``entity_tags.weight`` across matching tags
   (the slice 5.2 ``entities_with_tags`` substrate).
2. 1-hop neighbour expansion — entities directly connected to a
   matched entity get a fraction of the connecting entity's score
   so packets pull related context, not just exact-match nodes.

The retriever is intentionally simple — TF-IDF / vector embeddings
belong to a later slice (PH-15 conversation memory or PH-08 routing).
For PH-05's goals (packet relevance, session rehydration), tag-
overlap with neighbour-expansion is enough to beat the current
fixed-file packet builder.

Public surface:

- :class:`RetrievalResult` — frozen dataclass: ``entity``, ``score``,
  ``reasons`` list of human-readable explanations.
- :func:`rank_entities(store, tags)` — full ranked list.
- :func:`top_k(store, tags, k=10)` — bounded helper.

Cross-platform: stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .graph import Entity, GraphStore


NEIGHBOUR_DECAY = 0.5  # 1-hop neighbours get half a parent's score
DEFAULT_TOP_K = 10


@dataclass(frozen=True)
class RetrievalResult:
    """One ranked entry. ``score`` is non-negative; higher is better.
    ``reasons`` lists the contributing rules (``"tag:cli"``,
    ``"neighbour-of:42"``, etc.) so consumers can debug rankings.
    """

    entity: Entity
    score: float
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity.to_dict(),
            "score": self.score,
            "reasons": list(self.reasons),
        }


def _normalize_tags(tags: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        if not tag:
            continue
        cleaned = str(tag).strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        out.append(cleaned)
    return out


def rank_entities(
    store: GraphStore,
    tags: Iterable[str],
    *,
    expand_neighbours: bool = True,
    neighbour_decay: float = NEIGHBOUR_DECAY,
) -> list[RetrievalResult]:
    """Score every entity matching at least one tag, optionally
    expanding to 1-hop neighbours with a decayed score.

    Order of the returned list: descending by score, then by entity
    kind, then by entity name (deterministic — easier to diff in
    tests).
    """
    cleaned_tags = _normalize_tags(tags)
    if not cleaned_tags:
        return []

    direct = store.entities_with_tags(cleaned_tags)
    if not direct:
        return []

    # Build the seed table keyed by entity id.
    scored: dict[int, tuple[Entity, float, list[str]]] = {}
    for entity, weight in direct:
        # Re-derive which tags actually matched so the reasons list is
        # informative without storing per-tag scores.
        matched_tags = [
            tag for tag, _ in store.tags_for(entity.id) if tag in cleaned_tags
        ]
        reasons = [f"tag:{tag}" for tag in matched_tags]
        scored[entity.id] = (entity, float(weight), reasons)

    if expand_neighbours:
        # Snapshot the seed ids before we add neighbours so we don't
        # double-count neighbours of neighbours.
        seed_ids = list(scored.keys())
        for seed_id in seed_ids:
            seed_score = scored[seed_id][1]
            for neighbour in store.entity_neighbours(seed_id, direction="both"):
                if neighbour.id in scored:
                    continue
                contribution = seed_score * neighbour_decay
                if contribution <= 0:
                    continue
                reasons = [f"neighbour-of:{seed_id}"]
                scored[neighbour.id] = (neighbour, contribution, reasons)

    results = [
        RetrievalResult(entity=entity, score=score, reasons=tuple(reasons))
        for entity, score, reasons in scored.values()
    ]
    results.sort(key=lambda r: (-r.score, r.entity.kind, r.entity.name))
    return results


def top_k(
    store: GraphStore,
    tags: Iterable[str],
    *,
    k: int = DEFAULT_TOP_K,
    expand_neighbours: bool = True,
) -> list[RetrievalResult]:
    """Convenience: return only the top ``k`` results from
    :func:`rank_entities`. ``k <= 0`` returns an empty list."""
    if k <= 0:
        return []
    return rank_entities(store, tags, expand_neighbours=expand_neighbours)[:k]


__all__ = [
    "DEFAULT_TOP_K",
    "NEIGHBOUR_DECAY",
    "RetrievalResult",
    "rank_entities",
    "top_k",
]
