"""Drift detection — divergence between docs, code, and decisions.

PH-13 slice 13.1. The master roadmap target was a graph-backed
query (depending on PH-05's knowledge graph), but PH-05 hasn't
shipped yet; this module is a pragmatic filesystem-heuristic v1
that detects the same drift categories without a graph. When the
graph arrives, individual detectors here can be re-implemented as
graph queries without changing the public surface.

Three detectors today:

1. ``undocumented_handler`` — every ``cmd_*`` function in
   ``commands.py`` without a docstring.
2. ``undocumented_module`` — Python module under
   ``mythic_vibe_cli/`` whose first non-blank, non-import,
   non-future line is not a string literal.
3. ``superseded_decision_referenced`` — markdown decision file
   marked ``status: superseded`` or ``status: deprecated`` that is
   still referenced (path-substring) from at least one other
   markdown file in the project.

All detectors are best-effort: file errors and parse errors are
swallowed, the offending file is skipped, and the scan continues.
A drift scan must never raise.

Cross-platform: pure stdlib (`pathlib`, `re`, `ast`, `tokenize`).
No platform branches.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal


DriftSeverity = Literal["info", "warning", "error"]
DriftCategory = Literal[
    "undocumented_handler",
    "undocumented_module",
    "superseded_decision_referenced",
]

_VALID_SEVERITIES: tuple[DriftSeverity, ...] = ("info", "warning", "error")


@dataclass(frozen=True)
class DriftFinding:
    """One unit of detected drift.

    ``path`` is always project-relative when the scanner can derive it,
    using forward slashes regardless of host OS so JSON output is
    stable across platforms.
    """

    category: DriftCategory
    severity: DriftSeverity
    path: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "category": self.category,
            "severity": self.severity,
            "path": self.path,
            "description": self.description,
        }


def _relpath(target: Path, root: Path) -> str:
    """Project-relative, forward-slash path for portable JSON output."""
    try:
        rel = target.resolve().relative_to(root.resolve())
    except ValueError:
        rel = target
    return str(rel).replace("\\", "/")


# ---- Detector 1: undocumented argparse handlers ------------------------


def detect_undocumented_handlers(root: Path) -> list[DriftFinding]:
    """Find every top-level ``cmd_*`` function in
    ``mythic_vibe_cli/commands.py`` that has no docstring.

    Handlers are the user-facing surface — a missing docstring means
    ``slash inspect`` and ``--help`` lose their description. Severity
    is ``warning`` because the CLI still works, but the operator
    can't introspect the command.
    """
    commands_file = root / "mythic_vibe_cli" / "commands.py"
    if not commands_file.is_file():
        return []
    try:
        source = commands_file.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    findings: list[DriftFinding] = []
    rel = _relpath(commands_file, root)
    for node in ast.iter_child_nodes(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if not node.name.startswith("cmd_"):
            continue
        if ast.get_docstring(node):
            continue
        findings.append(
            DriftFinding(
                category="undocumented_handler",
                severity="warning",
                path=f"{rel}:{node.lineno}",
                description=(
                    f"Handler '{node.name}' has no docstring; "
                    "`slash inspect` and `--help` will show no description."
                ),
            )
        )
    return findings


# ---- Detector 2: undocumented modules ----------------------------------


_INIT_NAMES = {"__init__.py", "__main__.py"}


def _is_doc_string_first(source: str) -> bool:
    """Return True if the first significant statement is a string literal
    (i.e., a module docstring). Empty / pure-import / pure-future modules
    return True (nothing to document)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return True  # don't flag broken modules
    for stmt in tree.body:
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(
            stmt.value.value, str
        ):
            return True
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            continue  # skip imports; check next stmt
        return False
    return True  # no statements


def detect_undocumented_modules(root: Path) -> list[DriftFinding]:
    """Walk ``mythic_vibe_cli/`` for Python modules whose first
    real statement is not a docstring. ``__init__.py`` and
    ``__main__.py`` are exempt (they're legitimately bare).

    Severity ``info`` — undocumented internals don't break the CLI,
    but the project's documentation discipline benefits from the
    nudge.
    """
    package_root = root / "mythic_vibe_cli"
    if not package_root.is_dir():
        return []
    findings: list[DriftFinding] = []
    for py_file in sorted(package_root.rglob("*.py")):
        if py_file.name in _INIT_NAMES:
            continue
        try:
            source = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        if _is_doc_string_first(source):
            continue
        findings.append(
            DriftFinding(
                category="undocumented_module",
                severity="info",
                path=_relpath(py_file, root),
                description=(
                    "Module has no top-level docstring — "
                    "first real statement is not a string literal."
                ),
            )
        )
    return findings


# ---- Detector 3: superseded decisions still referenced -----------------


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE | re.IGNORECASE)


def _read_status(text: str) -> str:
    """Return the lowercase ``status:`` value from the front-matter
    block (if any). Empty string if not present / malformed."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return ""
    status_match = _STATUS_RE.search(match.group(1))
    if not status_match:
        return ""
    return status_match.group(1).strip().lower()


def detect_superseded_decisions(root: Path) -> list[DriftFinding]:
    """Find decision markdown files (under ``docs/decisions/`` or
    ``mythic/decisions/``) marked ``status: superseded`` or
    ``status: deprecated`` whose **filename** still appears as a
    substring in any other markdown file in the project. The
    referenced filename hints that something else hasn't been
    updated yet — that's drift.

    Severity ``warning`` — a referenced superseded decision can
    mislead a reader, but the build still works.
    """
    findings: list[DriftFinding] = []
    decision_roots: list[Path] = []
    for candidate in (root / "docs" / "decisions", root / "mythic" / "decisions"):
        if candidate.is_dir():
            decision_roots.append(candidate)
    if not decision_roots:
        return []

    superseded: list[Path] = []
    for decision_root in decision_roots:
        for md_file in decision_root.rglob("*.md"):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            status = _read_status(text)
            if status in {"superseded", "deprecated"}:
                superseded.append(md_file)

    if not superseded:
        return []

    # Build a one-time pool of all *other* markdown files in the project,
    # excluding the decision roots themselves (so a sibling ADR mentioning
    # the superseded one doesn't count as drift — that's normal ADR
    # cross-reference behaviour).
    decision_root_resolved = {dr.resolve() for dr in decision_roots}
    other_md: list[Path] = []
    for md_file in root.rglob("*.md"):
        try:
            md_resolved = md_file.resolve()
        except OSError:
            continue
        if any(
            decision_root in md_resolved.parents or decision_root == md_resolved.parent
            for decision_root in decision_root_resolved
        ):
            continue
        other_md.append(md_file)

    for super_file in superseded:
        super_name = super_file.name
        for md_file in other_md:
            try:
                content = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            if super_name in content:
                findings.append(
                    DriftFinding(
                        category="superseded_decision_referenced",
                        severity="warning",
                        path=_relpath(super_file, root),
                        description=(
                            f"Decision '{super_name}' is marked superseded/"
                            f"deprecated but still referenced from "
                            f"'{_relpath(md_file, root)}'."
                        ),
                    )
                )
                break  # one finding per superseded decision is enough
    return findings


# ---- Aggregator --------------------------------------------------------


def scan_for_drift(root: Path) -> list[DriftFinding]:
    """Run every drift detector against ``root`` and return the union
    of their findings.

    Detector ordering is stable so JSON output and tests can pin on
    it. Findings within a detector preserve the detector's natural
    order (file-walk order for modules, AST order for handlers).
    """
    findings: list[DriftFinding] = []
    findings.extend(detect_undocumented_handlers(root))
    findings.extend(detect_undocumented_modules(root))
    findings.extend(detect_superseded_decisions(root))
    return findings


def summarize_findings(findings: Iterable[DriftFinding]) -> dict[str, int]:
    """Return a count by severity (any severity not present is 0)."""
    counts = {sev: 0 for sev in _VALID_SEVERITIES}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    return counts


def render_findings_text(findings: list[DriftFinding]) -> str:
    """Human-readable text rendering — used by the CLI subcommand and
    the doctor integration when JSON is not requested."""
    if not findings:
        return "Drift scan: no findings."
    lines = [f"Drift scan: {len(findings)} finding(s)."]
    for finding in findings:
        lines.append(
            f"  [{finding.severity}] {finding.category}: "
            f"{finding.path}\n      {finding.description}"
        )
    return "\n".join(lines)


def to_payload(findings: list[DriftFinding]) -> dict[str, Any]:
    """JSON-friendly envelope for the doctor integration and the
    standalone ``mythic-vibe drift --json`` output."""
    return {
        "command": "drift",
        "findings": [f.to_dict() for f in findings],
        "summary": summarize_findings(findings),
        "ok": all(f.severity != "error" for f in findings),
    }


__all__ = [
    "DriftCategory",
    "DriftFinding",
    "DriftSeverity",
    "detect_superseded_decisions",
    "detect_undocumented_handlers",
    "detect_undocumented_modules",
    "render_findings_text",
    "scan_for_drift",
    "summarize_findings",
    "to_payload",
]
