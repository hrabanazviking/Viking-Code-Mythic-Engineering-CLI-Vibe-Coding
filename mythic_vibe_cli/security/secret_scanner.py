"""Secret scanner (PH-11 Slice 11.3).

Pre-packet check that scans candidate text + file paths for
hardcoded API keys, credentials, and tokens. Surfaces typed
:class:`SecretFinding` records before a packet ships to a
provider.

Reuses the slice-11.2 :class:`RedactionEngine`'s pattern set as
its source of truth — one regex catalogue shared by redaction
(replaces secrets in payloads) and detection (warns about
secrets in source).

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .redaction import RedactionEngine


SecretSeverity = str  # "critical" | "high" | "medium" | "advisory"


@dataclass(frozen=True)
class SecretFinding:
    """One detected secret. ``location`` is a file path (when
    scanning files) or ``"<inline>"`` (when scanning a text
    payload). ``line`` is 1-based for file scans, 0 for inline."""

    pattern: str
    severity: SecretSeverity
    location: str
    line: int = 0
    snippet: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "severity": self.severity,
            "location": self.location,
            "line": self.line,
            "snippet": self.snippet,
        }


@dataclass
class ScanResult:
    """Aggregated outcome of a scan call. ``findings`` is the
    canonical sequence; ``forbidden_paths`` lists files skipped
    because they matched a default-deny glob."""

    findings: list[SecretFinding] = field(default_factory=list)
    forbidden_paths: list[str] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "forbidden_paths": list(self.forbidden_paths),
            "files_scanned": self.files_scanned,
            "ok": self.ok,
            "count": len(self.findings),
        }


def _classify_severity(pattern_source: str) -> SecretSeverity:
    """Heuristic severity tagger — high-confidence patterns
    (specific provider key prefixes) get ``"critical"``; broad
    keyword matches get ``"medium"``."""
    src = pattern_source.lower()
    if "sk-" in src or "aiza" in src:
        return "critical"
    if "bearer" in src or "api[_-]?key" in src:
        return "high"
    if "secret" in src or "token" in src or "password" in src:
        return "medium"
    return "advisory"


def _truncate(text: str, *, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def scan_text(
    text: str,
    *,
    engine: RedactionEngine | None = None,
    location: str = "<inline>",
) -> list[SecretFinding]:
    """Scan a text payload (e.g. a packet body) for secrets.
    Returns one finding per pattern hit per line. Pattern hits
    on the same line by the same regex are deduplicated."""
    eng = engine or RedactionEngine()
    if not text:
        return []

    findings: list[SecretFinding] = []
    seen: set[tuple[str, int, str]] = set()

    lines = text.splitlines() if "\n" in text else [text]
    for line_idx, line in enumerate(lines, start=1):
        for pattern in eng.patterns:
            match = pattern.search(line)
            if not match:
                continue
            key = (pattern.pattern, line_idx, match.group(0))
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                SecretFinding(
                    pattern=pattern.pattern,
                    severity=_classify_severity(pattern.pattern),
                    location=location,
                    line=line_idx if "\n" in text else 0,
                    snippet=_truncate(line.strip()),
                )
            )
    return findings


def scan_paths(
    paths: Iterable[str | Path],
    *,
    root: str | Path | None = None,
    engine: RedactionEngine | None = None,
) -> ScanResult:
    """Scan a collection of file paths for secrets.

    Files matching any forbidden-path glob are **not** opened;
    they're listed in ``ScanResult.forbidden_paths`` so callers
    know to redact at the filename level. Other read failures
    (binary file, decode error, missing file) are skipped
    silently — the scanner is best-effort.

    ``root`` is used to render ``location`` as a project-relative
    posix path so findings are stable across platforms.
    """
    eng = engine or RedactionEngine()
    root_path = Path(root) if root else None

    result = ScanResult()
    for path in paths:
        path_obj = Path(str(path))
        rel = (
            path_obj.resolve().relative_to(root_path.resolve()).as_posix()
            if root_path is not None and path_obj.exists()
            else str(path_obj).replace("\\", "/")
        )

        if eng.is_path_forbidden(path_obj):
            result.forbidden_paths.append(rel)
            continue

        if not path_obj.is_file():
            continue

        try:
            body = path_obj.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        result.files_scanned += 1
        result.findings.extend(scan_text(body, engine=eng, location=rel))

    return result


__all__ = [
    "ScanResult",
    "SecretFinding",
    "SecretSeverity",
    "scan_paths",
    "scan_text",
]
