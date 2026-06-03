"""Dangerous-pattern detection (PH-11 Slice 11.5).

Scans code for patterns that frequently lead to security
incidents:

- ``eval(...)`` / ``exec(...)`` calls
- ``subprocess`` with ``shell=True``
- ``os.system(...)`` / ``os.popen(...)``
- string-formatted SQL (``f"SELECT ... {user_input}"``)
- ``pickle.loads`` of network input
- ``yaml.load`` (without ``Loader=SafeLoader``)
- raw HTML rendering (``mark_safe`` / ``Markup`` direct user input)

Findings are surfaced as **warnings**, not failures — the
scanner is informational. The slice 11.7 ``security audit``
command aggregates them with severity tags so operators can
triage.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Pattern


PatternSeverity = str  # "critical" | "high" | "medium" | "advisory"


@dataclass(frozen=True)
class DangerousPattern:
    """Catalogue entry. Each pattern declares the regex, the
    severity, the human-readable name, and a short remediation
    hint surfaced in audit output."""

    name: str
    severity: PatternSeverity
    regex: Pattern[str]
    remediation: str
    languages: tuple[str, ...] = ()  # empty = all

    def matches_language(self, language: str | None) -> bool:
        if not self.languages:
            return True
        if not language:
            return True
        return language.lower() in {lang.lower() for lang in self.languages}


@dataclass(frozen=True)
class DangerFinding:
    """One detected dangerous pattern occurrence."""

    pattern: str
    severity: PatternSeverity
    location: str
    line: int
    snippet: str
    remediation: str
    baseline_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "severity": self.severity,
            "location": self.location,
            "line": self.line,
            "snippet": self.snippet,
            "remediation": self.remediation,
            "baseline_reason": self.baseline_reason,
        }


@dataclass
class DangerScanResult:
    findings: list[DangerFinding] = field(default_factory=list)
    baselined_findings: list[DangerFinding] = field(default_factory=list)
    files_scanned: int = 0

    @property
    def ok(self) -> bool:
        return not self.findings

    def to_dict(self) -> dict[str, Any]:
        return {
            "findings": [f.to_dict() for f in self.findings],
            "baselined_findings": [f.to_dict() for f in self.baselined_findings],
            "files_scanned": self.files_scanned,
            "count": len(self.findings),
            "baselined_count": len(self.baselined_findings),
            "ok": self.ok,
        }


# ---- Pattern catalogue ----------------------------------------------


DANGEROUS_PATTERNS: tuple[DangerousPattern, ...] = (
    DangerousPattern(
        name="python.eval",
        severity="critical",
        regex=re.compile(r"(?<!\.)\beval\s*\("),
        remediation=(
            "eval() executes arbitrary code. Replace with ast.literal_eval "
            "for trusted literal data, or a strict parser for untrusted input."
        ),
        languages=("python",),
    ),
    DangerousPattern(
        name="python.exec",
        severity="critical",
        regex=re.compile(r"\bexec\s*\("),
        remediation=(
            "exec() executes arbitrary code. Replace with explicit functions "
            "or a sandboxed evaluator if dynamic execution is required."
        ),
        languages=("python",),
    ),
    DangerousPattern(
        name="python.shell_true",
        severity="high",
        regex=re.compile(r"shell\s*=\s*True"),
        remediation=(
            "subprocess with shell=True is shell-injection-prone. Pass argv "
            "as a list and use shell=False (the default)."
        ),
        languages=("python",),
    ),
    DangerousPattern(
        name="python.os_system",
        severity="high",
        regex=re.compile(r"\bos\.(system|popen)\s*\("),
        remediation=(
            "os.system / os.popen invoke the shell. Replace with subprocess.run "
            "with shell=False and an argv list."
        ),
        languages=("python",),
    ),
    DangerousPattern(
        name="python.pickle_loads",
        severity="high",
        regex=re.compile(r"\bpickle\.loads?\s*\("),
        remediation=(
            "pickle.loads on untrusted data executes arbitrary code. Replace "
            "with json / msgpack / a typed schema for inter-process payloads."
        ),
        languages=("python",),
    ),
    DangerousPattern(
        name="python.yaml_load",
        severity="medium",
        regex=re.compile(r"\byaml\.load\s*\([^)]*(?<!Loader=SafeLoader)\)"),
        remediation=(
            "yaml.load without Loader=SafeLoader can execute arbitrary "
            "Python objects. Use yaml.safe_load or pass Loader=SafeLoader."
        ),
        languages=("python",),
    ),
    DangerousPattern(
        name="sql.string_format",
        severity="high",
        regex=re.compile(
            r"""(?xi)
                (execute|cursor|query)\s*\(\s*
                (f["']|["'][^"']*\{[^}]*\})
            """
        ),
        remediation=(
            "f-string SQL is injection-prone. Use parameterised queries: "
            "execute('SELECT ... WHERE x = ?', (value,))"
        ),
    ),
    DangerousPattern(
        name="html.mark_safe_user_input",
        severity="medium",
        regex=re.compile(r"\bmark_safe\s*\(\s*[a-zA-Z_][\w\.\[\]]*\s*\)"),
        remediation=(
            "mark_safe() bypasses HTML escaping. Validate / sanitise the "
            "input first (e.g. bleach.clean) or use Django's escape()."
        ),
    ),
)

DANGEROUS_PATTERN_BASELINES: tuple[tuple[str, str, str], ...] = (
    (
        "mythic_vibe_cli/security/dangerous_patterns.py",
        "*",
        "rule catalogue intentionally contains literal dangerous-pattern examples",
    ),
)


def _truncate(text: str, *, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def scan_code(
    text: str,
    *,
    language: str | None = None,
    location: str = "<inline>",
    patterns: Iterable[DangerousPattern] | None = None,
) -> list[DangerFinding]:
    """Walk the catalogue and return one finding per match. The
    optional ``language`` arg narrows the patterns to language-
    specific ones (e.g. python.* gates skip when language='go')."""
    catalogue = list(patterns) if patterns is not None else list(DANGEROUS_PATTERNS)
    if not text:
        return []

    findings: list[DangerFinding] = []
    lines = text.splitlines() if "\n" in text else [text]

    for line_idx, line in enumerate(lines, start=1):
        for entry in catalogue:
            if not entry.matches_language(language):
                continue
            if not entry.regex.search(line):
                continue
            findings.append(
                DangerFinding(
                    pattern=entry.name,
                    severity=entry.severity,
                    location=location,
                    line=line_idx if "\n" in text else 0,
                    snippet=_truncate(line.strip()),
                    remediation=entry.remediation,
                )
            )
    return findings


def scan_paths(
    paths: Iterable[str | Path],
    *,
    root: str | Path | None = None,
) -> DangerScanResult:
    """Scan files for dangerous patterns. Skip non-text files /
    decode errors silently. Language inference is by extension."""
    extension_to_language = {
        ".py": "python",
        ".sql": "sql",
        ".html": "html",
        ".js": "javascript",
        ".ts": "typescript",
    }
    root_path = Path(root) if root else None

    result = DangerScanResult()
    for path in paths:
        path_obj = Path(str(path))
        if not path_obj.is_file():
            continue
        rel = (
            path_obj.resolve().relative_to(root_path.resolve()).as_posix()
            if root_path is not None
            else str(path_obj).replace("\\", "/")
        )
        try:
            body = path_obj.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        result.files_scanned += 1
        language = extension_to_language.get(path_obj.suffix.lower())
        for finding in scan_code(body, language=language, location=rel):
            baseline_reason = _baseline_reason(finding)
            if baseline_reason:
                result.baselined_findings.append(
                    DangerFinding(
                        pattern=finding.pattern,
                        severity=finding.severity,
                        location=finding.location,
                        line=finding.line,
                        snippet=finding.snippet,
                        remediation=finding.remediation,
                        baseline_reason=baseline_reason,
                    )
                )
            else:
                result.findings.append(finding)
    return result


def _baseline_reason(finding: DangerFinding) -> str:
    for location, pattern, reason in DANGEROUS_PATTERN_BASELINES:
        if finding.location == location and (pattern == "*" or pattern == finding.pattern):
            return reason
    return ""


__all__ = [
    "DANGEROUS_PATTERNS",
    "DANGEROUS_PATTERN_BASELINES",
    "DangerFinding",
    "DangerScanResult",
    "DangerousPattern",
    "PatternSeverity",
    "scan_code",
    "scan_paths",
]
