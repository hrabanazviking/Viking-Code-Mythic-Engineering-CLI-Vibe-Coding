"""Phase 20.I — opt-in TUI panel data builders.

The TUI gets two opt-in panels behind the new ``--panels`` flag:

- **`heatmap`** — drift findings counts as a category × severity
  grid. Useful for at-a-glance triage across many findings.
- **`risk`** — plugin risk indicators (capability declarations,
  unknown-capability warnings, breaker state).

The data builders here are **pure** so they can be tested
without spinning up Textual. The TUI widget rendering reads
these structures and renders them.

Default TUI behavior is preserved — when ``--panels`` is unset
or empty, neither builder runs and the existing TUI shape is
byte-identical.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Recognised panel names. Adding a new panel requires updating
# this tuple AND the --panels argparse choices in app.py.
KNOWN_PANELS: tuple[str, ...] = ("heatmap", "risk")


def parse_panels(raw: str) -> tuple[str, ...]:
    """Parse the comma-separated ``--panels`` argument. Lower-cases
    each entry; drops empty / unknown ones (with no warning here —
    callers can validate against KNOWN_PANELS if they want strict
    rejection)."""
    if not raw:
        return ()
    cleaned = []
    for chunk in raw.split(","):
        token = chunk.strip().lower()
        if token in KNOWN_PANELS:
            cleaned.append(token)
    # Preserve order, dedupe.
    seen: set[str] = set()
    deduped: list[str] = []
    for token in cleaned:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return tuple(deduped)


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeatmapCell:
    category: str
    severity: str
    count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "count": self.count,
        }


@dataclass
class HeatmapData:
    cells: list[HeatmapCell] = field(default_factory=list)
    total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "cells": [c.to_dict() for c in self.cells],
        }


def build_heatmap_data(root: Path) -> HeatmapData:
    """Aggregate drift findings into a category × severity grid.
    Reuses PH-13's `scan_for_drift`."""
    from .drift import scan_for_drift

    findings = scan_for_drift(root)
    grid: dict[tuple[str, str], int] = {}
    for finding in findings:
        key = (finding.category, finding.severity)
        grid[key] = grid.get(key, 0) + 1
    cells = [
        HeatmapCell(category=cat, severity=sev, count=count)
        for (cat, sev), count in sorted(grid.items())
    ]
    return HeatmapData(cells=cells, total=len(findings))


# ---------------------------------------------------------------------------
# Plugin risk
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PluginRiskRow:
    entrypoint: str
    enabled: bool
    capabilities: tuple[str, ...]
    unknown_capabilities: tuple[str, ...]
    risk_level: str  # "low" | "medium" | "high"

    def to_dict(self) -> dict[str, Any]:
        return {
            "entrypoint": self.entrypoint,
            "enabled": self.enabled,
            "capabilities": list(self.capabilities),
            "unknown_capabilities": list(self.unknown_capabilities),
            "risk_level": self.risk_level,
        }


@dataclass
class PluginRiskData:
    rows: list[PluginRiskRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": [r.to_dict() for r in self.rows],
        }


def _classify_risk(
    capabilities: tuple[str, ...],
    unknown: tuple[str, ...],
) -> str:
    """Coarse risk classifier:
    - **high**: any unknown capability declared (typo? supply-chain
      surprise?), OR network + subprocess together.
    - **medium**: any capability beyond `read`.
    - **low**: empty / `read`-only.
    """
    if unknown:
        return "high"
    cap_set = set(capabilities)
    if "network" in cap_set and "subprocess" in cap_set:
        return "high"
    privileged = cap_set - {"read"}
    if privileged:
        return "medium"
    return "low"


def build_plugin_risk_data(root: Path) -> PluginRiskData:
    """Walk the plugin registry and surface declared capabilities
    + risk classification per plugin."""
    from .plugins.capabilities import audit_capabilities
    from .plugins.registry import PluginRegistry

    registry = PluginRegistry(root)
    rows: list[PluginRiskRow] = []
    for record in registry.list(include_disabled=True):
        cap_audit = audit_capabilities(tuple(record.capabilities))
        rows.append(
            PluginRiskRow(
                entrypoint=record.entrypoint,
                enabled=record.enabled,
                capabilities=cap_audit.declared,
                unknown_capabilities=cap_audit.unknown,
                risk_level=_classify_risk(
                    cap_audit.declared, cap_audit.unknown
                ),
            )
        )
    return PluginRiskData(rows=rows)


__all__ = [
    "KNOWN_PANELS",
    "HeatmapCell",
    "HeatmapData",
    "PluginRiskData",
    "PluginRiskRow",
    "build_heatmap_data",
    "build_plugin_risk_data",
    "parse_panels",
]
