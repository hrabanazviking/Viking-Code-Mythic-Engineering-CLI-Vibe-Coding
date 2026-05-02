from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class VerificationArtifact:
    schema_version: int
    verification_id: str
    timestamp: str
    task_id: str | None
    commands: list[dict[str, Any]] = field(default_factory=list)
    diff_reviewed: bool = False
    docs_updated: bool = False
    invariants_checked: list[str] = field(default_factory=list)
    result: str = "blocked"
    level: str = "none"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    blocked_reasons: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    docs_checked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "verification_id": self.verification_id,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "commands": list(self.commands),
            "diff_reviewed": self.diff_reviewed,
            "docs_updated": self.docs_updated,
            "invariants_checked": list(self.invariants_checked),
            "result": self.result,
            "level": self.level,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "blocked_reasons": list(self.blocked_reasons),
            "changed_files": list(self.changed_files),
            "docs_checked": list(self.docs_checked),
        }


def verification_dir(root: Path) -> Path:
    return root / "mythic" / "verifications"


def verification_path(root: Path, verification_id: str) -> Path:
    return verification_dir(root) / f"{verification_id}.json"


def latest_verification_path(root: Path) -> Path:
    return verification_dir(root) / "latest.json"


def load_latest_verification(root: Path) -> dict[str, Any] | None:
    path = latest_verification_path(root)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def new_verification_id() -> str:
    return f"VER-{uuid4().hex[:12].upper()}"


def write_verification_artifact(root: Path, artifact: VerificationArtifact, *, promote_latest: bool = True) -> Path:
    # Phase 19.0 / L-10 (additive 2026-05-02 audit remediation):
    # route artifact writes through atomic_write_text so a process
    # kill mid-write leaves either the prior good artifact or the
    # new one — never a half-written truncated file.
    from ..runtime.atomic_write import atomic_write_text

    ver_dir = verification_dir(root)
    ver_dir.mkdir(parents=True, exist_ok=True)
    path = verification_path(root, artifact.verification_id)
    payload = json.dumps(artifact.to_dict(), indent=2) + "\n"
    atomic_write_text(path, payload)
    if promote_latest:
        atomic_write_text(latest_verification_path(root), payload)
    return path
