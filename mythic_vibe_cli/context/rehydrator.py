"""Session brief generator (PH-05 slice 5.4).

Given a project root and the operator's current Mythic phase, build
a typed :class:`SessionBrief` that captures everything a fresh
session needs to pick up cleanly:

- Recent decisions (top decision entities by ``updated_at``).
- Current-phase artefacts pulled from the graph by phase tag.
- Latest verification entity (if any).
- Latest handoff entity (if any).
- Top-K retriever hits seeded with ``[current_phase]``.

The brief itself does no IO beyond reading from the supplied
:class:`GraphStore` — population of the graph happens elsewhere
(slice 5.7 packet builder, slice 5.8 drift wiring, future
``checkin`` / ``scan`` integrations).

When the graph is empty (a fresh project), the brief reports zero
findings in every section without raising — the caller decides
whether to run a fresh ``mythic-vibe scan`` first.

Cross-platform: stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .graph import Entity, GraphStore
from .retriever import DEFAULT_TOP_K, RetrievalResult, top_k


DEFAULT_RECENT_DECISIONS = 5


@dataclass(frozen=True)
class SessionBrief:
    """Read-only snapshot of session-relevant state."""

    current_phase: str
    recent_decisions: tuple[Entity, ...] = field(default_factory=tuple)
    phase_artefacts: tuple[Entity, ...] = field(default_factory=tuple)
    latest_verification: Entity | None = None
    latest_handoff: Entity | None = None
    top_k: tuple[RetrievalResult, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_phase": self.current_phase,
            "recent_decisions": [e.to_dict() for e in self.recent_decisions],
            "phase_artefacts": [e.to_dict() for e in self.phase_artefacts],
            "latest_verification": (
                self.latest_verification.to_dict()
                if self.latest_verification is not None
                else None
            ),
            "latest_handoff": (
                self.latest_handoff.to_dict()
                if self.latest_handoff is not None
                else None
            ),
            "top_k": [r.to_dict() for r in self.top_k],
        }

    @property
    def is_empty(self) -> bool:
        """True if every section is empty — a fresh / unpopulated graph."""
        return (
            not self.recent_decisions
            and not self.phase_artefacts
            and self.latest_verification is None
            and self.latest_handoff is None
            and not self.top_k
        )


def _latest_by_updated(entities: list[Entity]) -> Entity | None:
    if not entities:
        return None
    return max(entities, key=lambda e: e.updated_at)


def build_session_brief(
    store: GraphStore,
    current_phase: str,
    *,
    recent_decisions_limit: int = DEFAULT_RECENT_DECISIONS,
    top_k_size: int = DEFAULT_TOP_K,
) -> SessionBrief:
    """Assemble a :class:`SessionBrief` from the supplied graph store.

    The function is read-only and side-effect-free — it does not
    write to the store, does not touch the filesystem outside what
    SQLite needs for read paths, and never raises on an empty graph
    (every section degrades to its "no data" representation).
    """
    decisions = sorted(
        store.find_entities(kind="decision"),
        key=lambda e: e.updated_at,
        reverse=True,
    )[: max(0, recent_decisions_limit)]

    # Phase artefacts: any entity tagged with the current phase name.
    phase_artefacts: tuple[Entity, ...] = ()
    if current_phase:
        tagged = store.entities_with_tags([current_phase])
        phase_artefacts = tuple(entity for entity, _ in tagged)

    latest_verification = _latest_by_updated(
        store.find_entities(kind="verification")
    )
    latest_handoff = _latest_by_updated(store.find_entities(kind="handoff"))

    top_results: tuple[RetrievalResult, ...] = ()
    if current_phase:
        top_results = tuple(top_k(store, [current_phase], k=top_k_size))

    return SessionBrief(
        current_phase=current_phase,
        recent_decisions=tuple(decisions),
        phase_artefacts=phase_artefacts,
        latest_verification=latest_verification,
        latest_handoff=latest_handoff,
        top_k=top_results,
    )


def render_brief_text(brief: SessionBrief) -> str:
    """Human-readable text rendering — used by the slice 5.5 CLI."""
    lines: list[str] = [
        f"Session brief — phase: {brief.current_phase or '(none)'}",
    ]
    if brief.is_empty:
        lines.append("  (graph is empty — run `mythic-vibe scan` first)")
        return "\n".join(lines)

    if brief.recent_decisions:
        lines.append("Recent decisions:")
        for entity in brief.recent_decisions:
            lines.append(f"  - {entity.name}  [{entity.updated_at}]")
    else:
        lines.append("Recent decisions: none")

    if brief.phase_artefacts:
        lines.append(f"Phase artefacts ({brief.current_phase}):")
        for entity in brief.phase_artefacts:
            lines.append(f"  - [{entity.kind}] {entity.name}")
    else:
        lines.append(f"Phase artefacts ({brief.current_phase}): none")

    if brief.latest_verification is not None:
        lines.append(
            f"Latest verification: {brief.latest_verification.name} "
            f"[{brief.latest_verification.updated_at}]"
        )
    else:
        lines.append("Latest verification: none")

    if brief.latest_handoff is not None:
        lines.append(
            f"Latest handoff: {brief.latest_handoff.name} "
            f"[{brief.latest_handoff.updated_at}]"
        )
    else:
        lines.append("Latest handoff: none")

    if brief.top_k:
        lines.append(f"Top {len(brief.top_k)} relevant:")
        for result in brief.top_k:
            lines.append(
                f"  - [{result.entity.kind}] {result.entity.name}  "
                f"(score {result.score:.2f})"
            )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_RECENT_DECISIONS",
    "SessionBrief",
    "build_session_brief",
    "render_brief_text",
]
