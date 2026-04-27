from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..workflow import MythicWorkflow


@dataclass
class InvariantCheckResult:
    checked: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": list(self.checked),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "ok": self.ok,
        }


def check_invariants(root: Path) -> InvariantCheckResult:
    workflow = MythicWorkflow(root)
    errors, warnings = workflow.doctor(repo_boundary=True)
    checked = [
        "project state schema",
        "repo boundary docs",
        "forbidden runtime imports",
    ]
    return InvariantCheckResult(checked=checked, errors=errors, warnings=warnings)
