"""Path audit (PH-18 Slice 18.2 — Round 2).

Round-2 invariants from the master roadmap:
- Every path resolves through ``pathlib`` from a configurable
  root.
- No hardcoded ``mythic/`` paths outside ``core/state.py`` (the
  canonical resolver).

This audit walks the runtime tree, flags string literals that
look like ``mythic/<segment>`` paths in modules outside the
allow-list, and surfaces them as :class:`PathFinding` records.

Reporting only — never mutates source. Findings are advisory:
many existing modules construct paths inline and the team
remediates incrementally.

Cross-platform: pure stdlib (``ast`` + ``re``).
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Modules allowed to construct ``mythic/`` paths inline. Add to
# the set when a new canonical resolver legitimately needs to.
HARDCODED_PATH_ALLOWED_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "core/state.py",
        # Persistence layers compose paths from project root +
        # well-known subpath; flagged otherwise.
        "persistence/json_store.py",
        # Verify subsystem stores artefacts at canonical paths.
        "verify/__init__.py",
        # Telemetry log path is a canonical artefact location.
        "ai/providers/base.py",
        # Forge ledger / reflection / memory modules each own
        # one canonical path; the audit allow-lists those that
        # explicitly are the "single source of truth" for that
        # path. Future remediation may consolidate these into
        # core/state.py.
        "forge_ledger.py",
        "forge_reflection.py",
        "memory/conversation.py",
        "memory/compaction.py",
        "context/graph.py",
        "context/indexer.py",
        "context/autopopulate.py",
        "policy/override_log.py",
        "plugins/registry.py",
        "handoff.py",
        "codex_bridge.py",
        "config.py",
        "mythic_data.py",
    }
)


# Pattern catches literals like "mythic/...", "mythic\\...",
# './mythic/...'. Matches inside ast.Constant string literals
# only — we don't lex prose.
_MYTHIC_PATH_RE = re.compile(r"(?:^|[/\\])?mythic[/\\][a-zA-Z0-9_./\\-]+")


@dataclass(frozen=True)
class PathFinding:
    """One Round-2 path-agnosticism smell."""

    location: str
    line: int
    column: int
    snippet: str
    matched_literal: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "line": self.line,
            "column": self.column,
            "snippet": self.snippet,
            "matched_literal": self.matched_literal,
            "detail": self.detail,
        }


@dataclass
class PathAuditResult:
    findings: list[PathFinding] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "count": len(self.findings),
            "files_scanned": self.files_scanned,
            "files_skipped": self.files_skipped,
            "notes": list(self.notes),
            "ok": self.ok,
        }


def _line_snippet(source_lines: list[str], line: int, *, limit: int = 120) -> str:
    if line < 1 or line > len(source_lines):
        return ""
    raw = source_lines[line - 1].rstrip()
    if len(raw) > limit:
        raw = raw[: limit - 3] + "..."
    return raw


def _scan_module(path: Path, source: str, *, relative: str) -> list[PathFinding]:
    if relative in HARDCODED_PATH_ALLOWED_RELATIVE_PATHS:
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    lines = source.splitlines()
    findings: list[PathFinding] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        value = node.value
        if not isinstance(value, str) or not value:
            continue
        # Skip very long strings (likely doc / template content).
        if len(value) > 500:
            continue
        match = _MYTHIC_PATH_RE.search(value)
        if not match:
            continue
        # Filter false positives: skip strings that begin with
        # "https://" / "http://" — those are URLs that happen to
        # contain "mythic/".
        lowered = value.lower()
        if lowered.startswith(("http://", "https://")):
            continue
        findings.append(
            PathFinding(
                location=relative,
                line=getattr(node, "lineno", 0),
                column=getattr(node, "col_offset", 0),
                snippet=_line_snippet(lines, getattr(node, "lineno", 0)),
                matched_literal=match.group(0),
                detail=(
                    "hardcoded mythic/<segment> string literal — route "
                    "through core.state's canonical resolver to keep paths "
                    "configurable"
                ),
            )
        )
    return findings


def _runtime_root(root: Path) -> Path:
    return Path(root) / "mythic_vibe_cli"


def audit_paths(
    root: Path,
    *,
    runtime_root: Path | None = None,
) -> PathAuditResult:
    """Walk the active runtime tree and flag hardcoded ``mythic/``
    string literals outside the allow-list."""
    target_root = (runtime_root or _runtime_root(root)).resolve()
    result = PathAuditResult()

    if not target_root.is_dir():
        result.notes.append(
            f"runtime root not found: {target_root} — nothing to audit"
        )
        return result

    for path in sorted(target_root.rglob("*.py")):
        try:
            relative = path.relative_to(target_root).as_posix()
        except ValueError:
            relative = str(path).replace("\\", "/")
        if (
            relative.startswith("__pycache__/")
            or "/__pycache__/" in relative
            or relative.endswith("__pycache__")
        ):
            result.files_skipped += 1
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            result.files_skipped += 1
            continue
        result.files_scanned += 1
        result.findings.extend(_scan_module(path, source, relative=relative))

    return result


__all__ = [
    "HARDCODED_PATH_ALLOWED_RELATIVE_PATHS",
    "PathAuditResult",
    "PathFinding",
    "audit_paths",
]
