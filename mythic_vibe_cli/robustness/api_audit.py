"""Internal API surface audit (PH-18 Slice 18.3 — Round 3).

Round-3 invariants from the master roadmap:
- Each subpackage exposes a typed module-level API.
- Cross-subpackage calls go through public APIs only (mypy
  enforced — this module adds a static lint that doesn't need
  mypy).

The audit walks the runtime tree and flags imports that reach
into another subpackage's private modules instead of importing
from that subpackage's ``__init__.py``.

A "subpackage" here is a top-level directory under
``mythic_vibe_cli/`` that contains an ``__init__.py``. Imports
from `subpackage.private_module` count as private when the
subpackage's `__init__.py` is non-trivial (re-exports
something), and the importing module lives outside that same
subpackage.

This is intentionally **conservative**: we only flag imports
that *cross* subpackage boundaries AND target a non-init
submodule when the subpackage's init re-exports anything.
Subpackages with empty inits (placeholders) are not gated —
operators are free to refactor them later.

Reporting only.

Cross-platform: pure stdlib (``ast`` + ``pathlib``).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ApiFinding:
    """One Round-3 API-surface smell."""

    location: str
    line: int
    column: int
    snippet: str
    importer_subpackage: str
    target_subpackage: str
    target_module: str
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "line": self.line,
            "column": self.column,
            "snippet": self.snippet,
            "importer_subpackage": self.importer_subpackage,
            "target_subpackage": self.target_subpackage,
            "target_module": self.target_module,
            "detail": self.detail,
        }


@dataclass
class ApiAuditResult:
    findings: list[ApiFinding] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    subpackages_with_public_api: list[str] = field(default_factory=list)
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
            "subpackages_with_public_api": list(
                self.subpackages_with_public_api
            ),
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


def _runtime_root(root: Path) -> Path:
    return Path(root) / "mythic_vibe_cli"


def _enumerate_subpackages_with_public_api(target_root: Path) -> set[str]:
    """A subpackage qualifies as having a public API when its
    ``__init__.py`` is non-trivial (>5 lines of non-blank,
    non-comment content). Empty / placeholder inits are not
    gated — operators can flesh them out later without breaking
    every cross-import."""
    qualifying: set[str] = set()
    for path in target_root.iterdir():
        if not path.is_dir():
            continue
        init_path = path / "__init__.py"
        if not init_path.is_file():
            continue
        try:
            body = init_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        non_trivial = sum(
            1
            for line in body.splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
        if non_trivial > 5:
            qualifying.add(path.name)
    return qualifying


def _importer_subpackage(relative: str) -> str:
    """Top-level subpackage of the importing module relative to
    the runtime root. e.g. ``"ai/providers/yggdrasil.py"`` →
    ``"ai"``. Top-level files (``app.py``, ``commands.py``)
    return ``""``."""
    parts = relative.split("/")
    if len(parts) <= 1:
        return ""
    return parts[0]


def _module_dot_to_subpackage(
    module_name: str,
    *,
    importer_relative: str,
    runtime_package: str = "mythic_vibe_cli",
) -> tuple[str, str] | None:
    """Resolve an ``import X`` / ``from X import Y`` target into
    ``(subpackage, module_after_subpackage)`` when X is inside
    the runtime package. Returns None for stdlib / third-party /
    same-subpackage imports (relative imports starting with ``.``).
    """
    if not module_name:
        return None
    cleaned = module_name.lstrip(".")
    if not cleaned:
        return None  # bare relative import — same package
    parts = cleaned.split(".")
    if parts[0] == runtime_package and len(parts) >= 2:
        sub = parts[1]
        rest = ".".join(parts[2:])
        return sub, rest
    # Imports without the runtime prefix: only meaningful for
    # in-tree relative imports, which Python resolves by the
    # current package. We treat unprefixed names as third-party
    # (no finding).
    return None


def _scan_module(
    source: str,
    *,
    relative: str,
    qualifying_subpackages: set[str],
) -> list[ApiFinding]:
    importer_sub = _importer_subpackage(relative)

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    lines = source.splitlines()
    findings: list[ApiFinding] = []

    def _maybe_flag(
        target_sub: str,
        target_module: str,
        node: ast.AST,
    ) -> None:
        if target_sub not in qualifying_subpackages:
            return
        if importer_sub == target_sub:
            return  # in-subpackage import
        if not target_module:
            return  # `from mythic_vibe_cli.X import ...` — public API
        # Reaching into a private submodule from outside.
        findings.append(
            ApiFinding(
                location=relative,
                line=getattr(node, "lineno", 0),
                column=getattr(node, "col_offset", 0),
                snippet=_line_snippet(lines, getattr(node, "lineno", 0)),
                importer_subpackage=importer_sub or "<top-level>",
                target_subpackage=target_sub,
                target_module=target_module,
                detail=(
                    f"crosses subpackage boundary into private module "
                    f"{target_sub}.{target_module} — import from "
                    f"{target_sub}/__init__.py instead"
                ),
            )
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            level = node.level or 0
            if level > 0:
                # Relative import (`from .x import y`) — same
                # subpackage; not gated.
                continue
            resolution = _module_dot_to_subpackage(
                module_name, importer_relative=relative
            )
            if resolution is None:
                continue
            target_sub, target_module = resolution
            _maybe_flag(target_sub, target_module, node)

    return findings


def audit_api_surfaces(
    root: Path,
    *,
    runtime_root: Path | None = None,
) -> ApiAuditResult:
    target_root = (runtime_root or _runtime_root(root)).resolve()
    result = ApiAuditResult()

    if not target_root.is_dir():
        result.notes.append(
            f"runtime root not found: {target_root} — nothing to audit"
        )
        return result

    qualifying = _enumerate_subpackages_with_public_api(target_root)
    result.subpackages_with_public_api = sorted(qualifying)

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
            _scan_module(
                source,
                relative=relative,
                qualifying_subpackages=qualifying,
            )
        )

    return result


__all__ = [
    "ApiAuditResult",
    "ApiFinding",
    "audit_api_surfaces",
]
