"""Phase 20.C — workflow lineage viewer.

Reads the existing PH-03 forge artifacts (``forge_ledger.json``
+ optional ``forge_reflection`` files) and emits a
human-readable graph view of the workflow's per-step
progression. Pure read; no mutation.

Two outputs per workflow:

- **Markdown** — Mermaid ``flowchart LR`` diagram with one
  node per step, status-coloured edges, and a per-step caption
  carrying the role and duration.
- **JSON** — structured payload (`steps`, `edges`,
  `terminal_status`) suitable for downstream tooling that
  doesn't speak Mermaid.

The CLI surface is ``mythic-vibe workflow lineage [--workflow
ID]``. Defaults to the most recent workflow in the ledger when
no id is passed.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Mermaid node-style hints per ledger status. Operators reading
# the rendered diagram see status at a glance via the colour
# stylesheet appended after the flowchart body.
_STATUS_STYLES: dict[str, str] = {
    "succeeded": "fill:#a4d4a4,stroke:#2c662d,color:#0d3a0d",
    "failed":    "fill:#f4a4a4,stroke:#8b1f1f,color:#3a0d0d",
    "blocked":   "fill:#f0d068,stroke:#7a5b00,color:#3a2a00",
    "pending":   "fill:#d4d4d4,stroke:#5a5a5a,color:#1f1f1f",
    "running":   "fill:#a4c8e0,stroke:#1f4f7a,color:#0d2a3a",
}


@dataclass(frozen=True)
class LineageStep:
    step_id: str
    role: str
    status: str
    started_at: str
    completed_at: str | None
    duration_ms: int | None
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "role": self.role,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "summary": self.summary,
        }


@dataclass
class LineageGraph:
    workflow_id: str
    steps: list[LineageStep] = field(default_factory=list)
    terminal_status: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        edges = [
            {"from": prev.step_id, "to": nxt.step_id}
            for prev, nxt in zip(self.steps, self.steps[1:])
        ]
        return {
            "workflow_id": self.workflow_id,
            "terminal_status": self.terminal_status,
            "steps": [s.to_dict() for s in self.steps],
            "edges": edges,
        }


def _summary_for(entry: Any) -> str:
    """Best-effort one-liner from an AgentOutput. Truncates so
    the Mermaid diagram doesn't get unwieldy."""
    output = getattr(entry, "agent_output", None)
    if output is None:
        return ""
    text = getattr(output, "summary", "") or ""
    if not text and getattr(output, "raw_response", None):
        # Fall back to first non-empty line of raw response.
        for line in str(output.raw_response).splitlines():
            stripped = line.strip()
            if stripped:
                text = stripped
                break
    text = text.replace("\n", " ").strip()
    if len(text) > 80:
        return text[:77] + "..."
    return text


def build_lineage(root: Path, workflow_id: str | None) -> LineageGraph | None:
    """Walk the ledger for ``workflow_id`` (or the most recent
    workflow if None) and return a :class:`LineageGraph`.
    Returns None when no workflow can be resolved (empty ledger
    OR unknown id)."""
    from .forge_ledger import ForgeLedger

    ledger = ForgeLedger(root)

    target_id = (workflow_id or "").strip()
    if not target_id:
        # Mirror the resolution logic from forge.py — most
        # recent workflow is "the workflow_id of the newest
        # ledger entry". Replicating here so this module has
        # zero forge.py dependencies.
        latest = ledger.latest(limit=1)
        if not latest:
            return None
        target_id = latest[0].workflow_id

    entries = ledger.find_by_workflow(target_id)
    if not entries:
        return None

    # Resolve to most-recent entry per step_id (mirror
    # forge_reflection.build_forge_reflection's resolution).
    resolved: dict[str, Any] = {}
    for entry in entries:
        existing = resolved.get(entry.step_id)
        if existing is None or entry.started_at > existing.started_at:
            resolved[entry.step_id] = entry

    ordered = sorted(resolved.values(), key=lambda e: e.step_id)
    steps = [
        LineageStep(
            step_id=entry.step_id,
            role=entry.role,
            status=entry.status,
            started_at=entry.started_at,
            completed_at=entry.completed_at,
            duration_ms=entry.duration_ms,
            summary=_summary_for(entry),
        )
        for entry in ordered
    ]

    terminal_status = steps[-1].status if steps else "unknown"
    return LineageGraph(
        workflow_id=target_id,
        steps=steps,
        terminal_status=terminal_status,
    )


def _mermaid_node_id(step_id: str) -> str:
    """Mermaid node IDs can't contain dashes — sanitise."""
    return step_id.replace("-", "_")


def render_markdown(graph: LineageGraph) -> str:
    """Render the lineage as a Mermaid flowchart embedded in
    Markdown. Includes a caption table below the diagram so
    operators reading the raw markdown still get full
    information when Mermaid isn't rendered."""
    lines: list[str] = []
    lines.append(f"# Workflow Lineage — {graph.workflow_id}")
    lines.append("")
    lines.append(f"**Terminal status:** {graph.terminal_status}")
    lines.append("")
    lines.append("```mermaid")
    lines.append("flowchart LR")

    # Nodes with role + status caption.
    for step in graph.steps:
        node_id = _mermaid_node_id(step.step_id)
        caption = (
            f"{step.step_id}<br/>{step.role}<br/>"
            f"<i>{step.status}</i>"
        )
        lines.append(f"    {node_id}[\"{caption}\"]")

    # Edges connecting steps in declared order.
    for prev, nxt in zip(graph.steps, graph.steps[1:]):
        lines.append(
            f"    {_mermaid_node_id(prev.step_id)} --> "
            f"{_mermaid_node_id(nxt.step_id)}"
        )

    # Style each node by status.
    for step in graph.steps:
        style = _STATUS_STYLES.get(step.status)
        if not style:
            continue
        node_id = _mermaid_node_id(step.step_id)
        lines.append(f"    style {node_id} {style}")
    lines.append("```")
    lines.append("")

    # Caption table for non-Mermaid readers.
    lines.append("| Step | Role | Status | Duration | Summary |")
    lines.append("|------|------|--------|----------|---------|")
    for step in graph.steps:
        duration = (
            f"{step.duration_ms}ms"
            if step.duration_ms is not None
            else "-"
        )
        summary = (
            step.summary.replace("|", "/") if step.summary else "-"
        )
        lines.append(
            f"| {step.step_id} | {step.role} | "
            f"{step.status} | {duration} | {summary} |"
        )
    return "\n".join(lines) + "\n"


__all__ = [
    "LineageGraph",
    "LineageStep",
    "build_lineage",
    "render_markdown",
]
