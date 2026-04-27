from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DocCheckResult:
    checked: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": list(self.checked),
            "missing": list(self.missing),
            "warnings": list(self.warnings),
            "ok": self.ok,
        }


def check_docs(root: Path) -> DocCheckResult:
    expected = [
        "README.md",
        "CHANGELOG.md",
        "DEVLOG.md",
        "docs/ARCHITECTURE.md",
        "docs/DOMAIN_MAP.md",
        "docs/DATA_FLOW.md",
        "docs/PHILOSOPHY.md",
        "docs/COMMAND_CONTRACTS.md",
        "docs/INDEX.md",
    ]
    missing = [path for path in expected if not (root / path).exists()]
    warnings: list[str] = []
    if missing:
        warnings.append("Some documentation files are missing; verification will stay conservative.")
    return DocCheckResult(checked=expected, missing=missing, warnings=warnings)
