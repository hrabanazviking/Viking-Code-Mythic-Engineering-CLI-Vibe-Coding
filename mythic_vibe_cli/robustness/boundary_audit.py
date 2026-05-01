"""Boundary audit (PH-18 Slice 18.1 — Round 1).

Walks the active runtime tree (``mythic_vibe_cli/``) via Python's
:mod:`ast` module and surfaces typed :class:`BoundaryFinding`
records for:

- Direct ``subprocess.run`` / ``subprocess.Popen`` /
  ``subprocess.call`` / ``os.system`` / ``os.popen`` calls that
  live outside :mod:`mythic_vibe_cli.runtime.exec` (the canonical
  subprocess wrapper).
- Bare ``except:`` clauses (catch-everything that swallows
  KeyboardInterrupt, SystemExit, etc.).

Reporting only — the audit never mutates source code. Findings
feed the slice 18.4 simulate command and (optionally) future CI
gates.

Cross-platform: pure stdlib (``ast`` + ``pathlib``).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# Files the audit deliberately allows to bypass the runtime.exec
# wrapper. These are the canonical subprocess sites — the audit
# would flag them as findings otherwise.
SUBPROCESS_ALLOWED_RELATIVE_PATHS: frozenset[str] = frozenset(
    {
        "runtime/exec.py",
    }
)


@dataclass(frozen=True)
class BoundaryFinding:
    """One Round-1 boundary smell."""

    kind: str  # "direct_subprocess" | "bare_except" | "os_system"
    location: str  # relative posix path
    line: int
    column: int
    snippet: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "location": self.location,
            "line": self.line,
            "column": self.column,
            "snippet": self.snippet,
            "detail": self.detail,
        }


@dataclass
class BoundaryAuditResult:
    findings: list[BoundaryFinding] = field(default_factory=list)
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


# ---- AST helpers ------------------------------------------------------


_DIRECT_SUBPROCESS_FUNCS: frozenset[str] = frozenset(
    {"run", "Popen", "call", "check_call", "check_output"}
)
_OS_SHELL_FUNCS: frozenset[str] = frozenset({"system", "popen"})


def _node_attr_chain(node: ast.AST) -> list[str]:
    """Reduce an Attribute chain to a list of names. e.g.
    ``subprocess.run`` → ``["subprocess", "run"]``. Other shapes
    return ``[]``."""
    parts: list[str] = []
    current: Any = node
    while isinstance(current, ast.Attribute):
        parts.insert(0, current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.insert(0, current.id)
        return parts
    return []


def _line_snippet(source_lines: list[str], line: int, *, limit: int = 120) -> str:
    """Best-effort one-liner snippet at ``line`` (1-based)."""
    if line < 1 or line > len(source_lines):
        return ""
    raw = source_lines[line - 1].rstrip()
    if len(raw) > limit:
        raw = raw[: limit - 3] + "..."
    return raw


def _scan_module(
    module_path: Path,
    source: str,
    *,
    relative: str,
) -> list[BoundaryFinding]:
    """Run the AST visitors and return findings for one module."""
    try:
        tree = ast.parse(source, filename=str(module_path))
    except SyntaxError:
        return []

    lines = source.splitlines()
    findings: list[BoundaryFinding] = []

    is_canonical_subprocess_site = relative in SUBPROCESS_ALLOWED_RELATIVE_PATHS

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            chain = _node_attr_chain(node.func)
            if len(chain) >= 2:
                head = chain[0]
                tail = chain[-1]
                # subprocess.run / Popen / etc.
                if (
                    head == "subprocess"
                    and tail in _DIRECT_SUBPROCESS_FUNCS
                    and not is_canonical_subprocess_site
                ):
                    findings.append(
                        BoundaryFinding(
                            kind="direct_subprocess",
                            location=relative,
                            line=node.lineno,
                            column=node.col_offset,
                            snippet=_line_snippet(lines, node.lineno),
                            detail=(
                                f"direct {'.'.join(chain)} bypasses "
                                "runtime.exec_command's timeout + cancel + "
                                "exception-isolation contract"
                            ),
                        )
                    )
                # os.system / os.popen
                elif (
                    head == "os"
                    and tail in _OS_SHELL_FUNCS
                    and not is_canonical_subprocess_site
                ):
                    findings.append(
                        BoundaryFinding(
                            kind="os_system",
                            location=relative,
                            line=node.lineno,
                            column=node.col_offset,
                            snippet=_line_snippet(lines, node.lineno),
                            detail=(
                                f"{'.'.join(chain)} invokes the shell — "
                                "replace with subprocess via runtime.exec_command"
                            ),
                        )
                    )
        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                # bare `except:` clause.
                findings.append(
                    BoundaryFinding(
                        kind="bare_except",
                        location=relative,
                        line=node.lineno,
                        column=node.col_offset,
                        snippet=_line_snippet(lines, node.lineno),
                        detail=(
                            "bare `except:` swallows KeyboardInterrupt and "
                            "SystemExit; replace with `except Exception:` or "
                            "a typed exception"
                        ),
                    )
                )

    return findings


# ---- Top-level walker ------------------------------------------------


def _runtime_root(root: Path) -> Path:
    """Resolve the active-runtime root we audit. Defaults to the
    in-repo ``mythic_vibe_cli/`` package; tests pass a temp tree."""
    return Path(root) / "mythic_vibe_cli"


def audit_boundary(
    root: Path,
    *,
    runtime_root: Path | None = None,
) -> BoundaryAuditResult:
    """Walk the active runtime tree and return a typed audit
    result. Skip files that fail to read / parse silently."""
    target_root = (runtime_root or _runtime_root(root)).resolve()
    result = BoundaryAuditResult()

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
        result.findings.extend(
            _scan_module(path, source, relative=relative)
        )

    return result


def filter_findings_by_kind(
    findings: Iterable[BoundaryFinding], *, kind: str
) -> list[BoundaryFinding]:
    return [f for f in findings if f.kind == kind]


__all__ = [
    "BoundaryAuditResult",
    "BoundaryFinding",
    "SUBPROCESS_ALLOWED_RELATIVE_PATHS",
    "audit_boundary",
    "filter_findings_by_kind",
]
