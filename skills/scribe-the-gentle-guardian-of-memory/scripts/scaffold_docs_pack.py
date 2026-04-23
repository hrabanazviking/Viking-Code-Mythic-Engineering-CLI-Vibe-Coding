#!/usr/bin/env python3
"""Scaffold a Scribe documentation pack in the current repository.

Usage:
  python scripts/scaffold_docs_pack.py --modules ingestion memory-api scoring
"""

from __future__ import annotations

import argparse
from pathlib import Path


MODULE_TEMPLATE = """# {module_title}

## Purpose

## Ownership and Boundaries

## Inputs and Outputs

## Data Contracts

## Dependencies and Integration Points

## Failure Modes and Mitigations

## Test Strategy

## Implementation Phases

## Open Questions
"""


PROTOCOL_FILES = {
    "testing-protocol.md": "Testing Protocol — Mythic Engineering Standard",
    "security-protocol.md": "Security Protocol — Mythic Engineering Standard",
    "reliability-protocol.md": "Reliability Protocol — Mythic Engineering Standard",
    "operations-protocol.md": "Operations Protocol — Mythic Engineering Standard",
    "documentation-protocol.md": "Documentation Protocol — Mythic Engineering Standard",
}


def ensure(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modules", nargs="*", default=[])
    args = parser.parse_args()

    root = Path.cwd()
    docs = root / "docs"
    modules_dir = docs / "modules"
    protocols_dir = docs / "protocols"
    plans_dir = docs / "plans"

    for d in (docs, modules_dir, protocols_dir, plans_dir):
        d.mkdir(parents=True, exist_ok=True)

    ensure(root / "DEVLOG.md", "# DEVLOG\n\n## Session Log\n")
    ensure(root / "CHANGELOG.md", "# CHANGELOG\n\n## Unreleased\n\n### Added\n\n### Changed\n\n### Fixed\n")

    ensure(docs / "INDEX.md", "# Documentation Index\n\n- modules/\n- protocols/\n- plans/\n")
    ensure(plans_dir / "implementation-roadmap.md", "# Implementation Roadmap\n")
    ensure(plans_dir / "decision-ledger.md", "# Decision Ledger\n")
    ensure(plans_dir / "risk-register.md", "# Risk Register\n")

    for filename, title in PROTOCOL_FILES.items():
        ensure(protocols_dir / filename, f"# {title}\n\n## Purpose\n")

    for module in args.modules:
        module_slug = module.strip().lower().replace(" ", "-")
        module_title = module.strip().replace("-", " ").title()
        ensure(modules_dir / f"{module_slug}.md", MODULE_TEMPLATE.format(module_title=module_title))


if __name__ == "__main__":
    main()
