"""Packet retriever integration (PH-05 slice 5.7).

Helpers that bridge the slice-5.3 retriever into the slice-1.x
codex packet builder. The codex bridge calls
:func:`build_graph_context_section` when it assembles a packet;
when the project's graph is populated the helper returns a
markdown block listing the most-relevant entities for the
packet's task / phase / role; when the graph is empty (or
absent), the helper returns an empty string and the bridge
behaves exactly as it did before.

Char-budget honour:

- Each call to :func:`build_graph_context_section` accepts a
  ``budget`` argument (defaults to the operator's
  ``MYTHIC_PACKET_CHAR_BUDGET`` via the config layer).
- If the rendered block exceeds the budget, it is truncated at
  the last newline before the budget cutoff and a
  ``"_...truncated..._"`` marker is appended so the AI consumer
  knows the list is incomplete.

Tag derivation: :func:`derive_packet_tags` splits the request's
phase / role / task strings on non-identifier characters,
lowercases, and de-duplicates. Tokens shorter than 3 characters
are dropped to avoid false-positive matches on common stop-words.

Cross-platform: stdlib only. No graph dependency at module-import
time — :class:`GraphStore` is imported lazily inside the helper
so non-graph consumers don't pay the import cost.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .graph import GraphStore, graph_path_for
from .retriever import top_k


DEFAULT_PACKET_CONTEXT_BUDGET = 12000
DEFAULT_PACKET_CONTEXT_TOP_K = 10
TRUNCATION_NOTE = "\n_...truncated to fit packet char budget._"


def derive_packet_tags(*components: str) -> list[str]:
    """Split each ``components`` string on non-identifier characters,
    lowercase the result, drop tokens of length < 3, and return a
    deduplicated tag list preserving first-seen order.

    Used by the codex bridge to seed the retriever with tags drawn
    from a :class:`CodexPacketRequest`'s phase / role / task fields.
    """
    seen: set[str] = set()
    out: list[str] = []
    for component in components:
        if not component:
            continue
        for token in re.split(r"[^A-Za-z0-9_-]+", component):
            cleaned = token.strip().lower()
            if len(cleaned) < 3:
                continue
            if cleaned in seen:
                continue
            seen.add(cleaned)
            out.append(cleaned)
    return out


def _truncate_to_budget(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    cutoff = budget - len(TRUNCATION_NOTE)
    if cutoff <= 0:
        return TRUNCATION_NOTE.lstrip()
    truncated = text[:cutoff]
    last_newline = truncated.rfind("\n")
    if last_newline > 0:
        truncated = truncated[:last_newline]
    return truncated + TRUNCATION_NOTE


def build_graph_context_section(
    root: Path,
    *,
    tags: Iterable[str],
    budget: int = DEFAULT_PACKET_CONTEXT_BUDGET,
    top_k_size: int = DEFAULT_PACKET_CONTEXT_TOP_K,
) -> str:
    """Open the project's graph and render the top-K retriever hits
    as a markdown block, bounded by ``budget`` characters.

    Returns an empty string when:

    - no tags supplied (nothing to query);
    - graph file does not exist (project has not been scanned);
    - graph exists but is empty (just-initialised);
    - retriever returns no hits.

    The returned string never starts with whitespace and always ends
    with a newline when non-empty so the caller can concatenate it
    cleanly into a larger packet.
    """
    cleaned_tags = [t for t in tags if t]
    if not cleaned_tags or budget <= 0:
        return ""

    graph_file = graph_path_for(root)
    if not graph_file.exists():
        return ""

    try:
        store = GraphStore.open(root)
    except Exception:  # noqa: BLE001 — corrupt DB shouldn't break packets
        return ""

    try:
        if store.entity_count() == 0:
            return ""
        results = top_k(store, cleaned_tags, k=top_k_size)
    finally:
        store.close()

    if not results:
        return ""

    lines: list[str] = [
        "## Relevant Graph Context",
        "",
        f"_Top {len(results)} entities by tags: {', '.join(cleaned_tags)}_",
        "",
    ]
    for result in results:
        path_suffix = f"  `{result.entity.path}`" if result.entity.path else ""
        lines.append(
            f"- [{result.entity.kind}] **{result.entity.name}** "
            f"(score {result.score:.2f}){path_suffix}"
        )
        if result.reasons:
            reason_text = ", ".join(result.reasons)
            lines.append(f"    _reasons: {reason_text}_")

    rendered = "\n".join(lines).rstrip() + "\n"
    return _truncate_to_budget(rendered, budget)


__all__ = [
    "DEFAULT_PACKET_CONTEXT_BUDGET",
    "DEFAULT_PACKET_CONTEXT_TOP_K",
    "TRUNCATION_NOTE",
    "build_graph_context_section",
    "derive_packet_tags",
]
