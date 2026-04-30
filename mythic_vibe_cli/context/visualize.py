"""Mermaid + DOT exporters for the knowledge graph (PH-05 slice 5.6).

Two pure-text rendering helpers — :func:`render_mermaid` and
:func:`render_dot` — that walk a :class:`GraphStore` and emit a
visualisation an external tool (Mermaid Live Editor, Graphviz)
can render. Optional ``focus_node`` arg restricts the output to a
1-hop subgraph around a single entity, useful when the full graph
is too large to render.

Cross-platform: stdlib only. No ``graphviz`` Python dep — we emit
DOT text the user can pipe into the ``dot`` binary themselves.
"""

from __future__ import annotations

from .graph import Edge, Entity, GraphStore


def _mermaid_safe_id(entity: Entity) -> str:
    """Mermaid node identifiers must be alphanumeric + a few specials.
    We use ``e<id>`` so collisions with reserved words / spaces are
    impossible regardless of the entity name."""
    return f"e{entity.id}"


def _mermaid_safe_label(entity: Entity) -> str:
    """Mermaid node labels go inside ``[...]`` — escape pipes and
    brackets to keep the renderer happy."""
    label = f"{entity.kind}:{entity.name}"
    return label.replace("|", "\\|").replace("[", "(").replace("]", ")")


def _scope_to_node(
    store: GraphStore, focus_node: int
) -> tuple[list[Entity], list[Edge]]:
    """Return the (entities, edges) tuple for the 1-hop subgraph
    centered on ``focus_node``."""
    centre = store._fetch_entity(focus_node)  # raises KeyError if absent
    neighbours = store.entity_neighbours(focus_node, direction="both")
    entities = [centre] + neighbours
    entity_ids = {e.id for e in entities}
    edges = [
        edge
        for edge in store.find_edges()
        if edge.src_id in entity_ids and edge.dst_id in entity_ids
    ]
    return entities, edges


def render_mermaid(store: GraphStore, *, focus_node: int | None = None) -> str:
    """Render the graph as a Mermaid ``graph LR`` block.

    With ``focus_node``, restricts to that entity's 1-hop subgraph;
    without, renders every entity and edge in the store.
    """
    if focus_node:
        entities, edges = _scope_to_node(store, focus_node)
    else:
        entities = store.find_entities()
        edges = store.find_edges()

    lines = ["graph LR"]
    for entity in entities:
        node_id = _mermaid_safe_id(entity)
        label = _mermaid_safe_label(entity)
        lines.append(f"    {node_id}[\"{label}\"]")

    for edge in edges:
        try:
            src = store._fetch_entity(edge.src_id)
            dst = store._fetch_entity(edge.dst_id)
        except KeyError:
            continue
        src_id = _mermaid_safe_id(src)
        dst_id = _mermaid_safe_id(dst)
        lines.append(f"    {src_id} -->|{edge.kind}| {dst_id}")

    return "\n".join(lines)


def render_dot(store: GraphStore, *, focus_node: int | None = None) -> str:
    """Render the graph as a Graphviz DOT digraph."""
    if focus_node:
        entities, edges = _scope_to_node(store, focus_node)
    else:
        entities = store.find_entities()
        edges = store.find_edges()

    lines = ["digraph mythic {", "    rankdir=LR;"]
    for entity in entities:
        label = f"{entity.kind}:{entity.name}".replace('"', '\\"')
        lines.append(f'    e{entity.id} [label="{label}"];')

    for edge in edges:
        lines.append(
            f"    e{edge.src_id} -> e{edge.dst_id} "
            f'[label="{edge.kind}"];'
        )
    lines.append("}")
    return "\n".join(lines)


__all__ = ["render_dot", "render_mermaid"]
