from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..runtime.exec import ExecResult, exec_command


@dataclass
class GitDiffResult:
    changed_files: list[str] = field(default_factory=list)
    diffs: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_files": list(self.changed_files),
            "diffs": dict(self.diffs),
            "warnings": list(self.warnings),
        }


def _git(root: Path, *args: str) -> ExecResult:
    return exec_command("git", ["-C", str(root), *args], cwd=root)


def collect_changed_files(root: Path) -> list[str]:
    status = _git(root, "status", "--porcelain")
    if status.code != 0:
        return []
    files: list[str] = []
    for line in status.stdout.splitlines():
        if len(line) >= 4:
            files.append(line[3:].strip())
    return files


def review_changed_files(root: Path, *, limit: int = 8) -> GitDiffResult:
    changed_files = collect_changed_files(root)
    if not changed_files:
        return GitDiffResult(warnings=["No changed files detected."])

    result = GitDiffResult(changed_files=changed_files[:limit])
    for path in result.changed_files:
        diff = _git(root, "diff", "--", path)
        if diff.code == 0:
            result.diffs[path] = diff.stdout.strip()
        else:
            result.warnings.append(f"Could not diff {path}")
    if len(changed_files) > limit:
        result.warnings.append(f"Diff review truncated to first {limit} files.")
    return result
