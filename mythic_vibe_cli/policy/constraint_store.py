"""Constraint store (PH-14 Slice 14.1).

Reads typed :class:`Constraint` records from three sources:

1. ``mythic/oaths.md`` — operator-recorded oaths. One
   constraint per ``## `` heading; the heading text becomes the
   summary, the body bullets become the detail.
2. ``docs/ADRS/*.md`` — Architecture Decision Records. We treat
   each ADR as one constraint; the ``## Decision`` section's
   first paragraph becomes the constraint text, ``## Status``
   determines whether it's active (``Accepted``) or relaxed
   (``Superseded``, ``Deprecated``).
3. ``mythic/constraints.md`` — flat bullet list, one constraint
   per ``- `` bullet.

All three sources are optional. Missing files → empty list.
Malformed sections → skipped silently with notes attached to
the result for observability.

Cross-platform: pure stdlib (``re`` + ``pathlib``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# Severity vocabulary — kept narrow on purpose. Operators tag
# constraints with ``[blocking]`` / ``[warn]`` / ``[advisory]``
# suffixes inside the source text. Default is "warn" if no tag
# is present.
SEVERITY_BLOCKING = "blocking"
SEVERITY_WARN = "warn"
SEVERITY_ADVISORY = "advisory"
DEFAULT_SEVERITY = SEVERITY_WARN
SEVERITIES: tuple[str, ...] = (SEVERITY_BLOCKING, SEVERITY_WARN, SEVERITY_ADVISORY)

CONSTRAINT_KIND_OATH = "oath"
CONSTRAINT_KIND_ADR = "adr"
CONSTRAINT_KIND_RULE = "rule"


@dataclass(frozen=True)
class Constraint:
    """One operator-declared constraint."""

    id: str
    kind: str
    text: str
    severity: str = DEFAULT_SEVERITY
    source_path: str = ""
    source_section: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "text": self.text,
            "severity": self.severity,
            "source_path": self.source_path,
            "source_section": self.source_section,
        }


@dataclass
class ConstraintLoadResult:
    """Aggregated loader outcome. ``constraints`` is the
    canonical list; ``notes`` reports parse decisions for audit."""

    constraints: list[Constraint] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraints": [c.to_dict() for c in self.constraints],
            "notes": list(self.notes),
            "count": len(self.constraints),
        }


# ---- helpers ----------------------------------------------------------


_SEVERITY_TAG_RE = re.compile(
    r"\[(?P<sev>blocking|warn|advisory)\]\s*$",
    re.IGNORECASE,
)


def _slugify(text: str, *, limit: int = 60) -> str:
    """Stable id slug. Lowercase, non-alnum → hyphens, trimmed
    to ``limit`` chars. Empty → ``"unnamed"``."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text or "").strip("-").lower()
    if not cleaned:
        return "unnamed"
    if len(cleaned) > limit:
        cleaned = cleaned[:limit].rstrip("-")
    return cleaned


def _strip_severity_tag(text: str) -> tuple[str, str]:
    """Pull a ``[blocking]`` / ``[warn]`` / ``[advisory]`` tag
    off the end of ``text``. Returns ``(cleaned_text, severity)``;
    severity falls back to :data:`DEFAULT_SEVERITY` when no tag
    is present."""
    cleaned = (text or "").strip()
    match = _SEVERITY_TAG_RE.search(cleaned)
    if not match:
        return cleaned, DEFAULT_SEVERITY
    severity = match.group("sev").lower()
    cleaned = cleaned[: match.start()].rstrip()
    return cleaned, severity


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


# ---- per-source loaders ----------------------------------------------


def _load_oaths(root: Path, notes: list[str]) -> list[Constraint]:
    path = root / "mythic" / "oaths.md"
    if not path.is_file():
        return []
    body = _read_text(path)
    if not body:
        notes.append(f"oaths file unreadable or empty: {path}")
        return []

    rel = path.relative_to(root).as_posix()
    constraints: list[Constraint] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_heading, current_lines
        if current_heading is None:
            return
        # Strip severity tag from the heading first so the slug
        # is stable regardless of severity. Body lines may also
        # carry their own tag — body wins when both are tagged.
        heading_clean, heading_severity = _strip_severity_tag(
            current_heading.strip()
        )
        body_text = "\n".join(line.strip() for line in current_lines).strip()
        body_clean, body_severity = _strip_severity_tag(body_text)
        composed = (
            f"{heading_clean} — {body_clean}" if body_clean else heading_clean
        )
        if body_text and body_severity != DEFAULT_SEVERITY:
            severity = body_severity
        else:
            severity = heading_severity
        slug = _slugify(heading_clean)
        constraints.append(
            Constraint(
                id=f"oath:{slug}",
                kind=CONSTRAINT_KIND_OATH,
                text=composed,
                severity=severity,
                source_path=rel,
                source_section=heading_clean,
            )
        )
        current_heading = None
        current_lines = []

    for raw in body.splitlines():
        line = raw.rstrip("\r")
        if line.startswith("## "):
            flush()
            current_heading = line[3:].strip()
            current_lines = []
        elif current_heading is not None:
            stripped = line.strip()
            if stripped.startswith("- "):
                current_lines.append(stripped[2:].strip())
            elif stripped:
                current_lines.append(stripped)
    flush()
    return constraints


def _load_constraints_file(root: Path, notes: list[str]) -> list[Constraint]:
    path = root / "mythic" / "constraints.md"
    if not path.is_file():
        return []
    body = _read_text(path)
    if not body:
        notes.append(f"constraints file unreadable or empty: {path}")
        return []

    rel = path.relative_to(root).as_posix()
    constraints: list[Constraint] = []
    for line_idx, raw in enumerate(body.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped.startswith("- "):
            continue
        rule = stripped[2:].strip()
        if not rule:
            continue
        cleaned, severity = _strip_severity_tag(rule)
        slug = _slugify(cleaned)
        constraints.append(
            Constraint(
                id=f"rule:{slug}",
                kind=CONSTRAINT_KIND_RULE,
                text=cleaned,
                severity=severity,
                source_path=rel,
                source_section=f"line {line_idx}",
            )
        )
    return constraints


_ADR_TITLE_RE = re.compile(r"^#\s+(?P<title>.+)$")
_ADR_STATUS_RE = re.compile(r"^##\s+Status\s*$", re.IGNORECASE)
_ADR_DECISION_RE = re.compile(r"^##\s+Decision\s*$", re.IGNORECASE)
_ADR_OTHER_HEADING_RE = re.compile(r"^##\s+\S")


def _load_adrs(root: Path, notes: list[str]) -> list[Constraint]:
    adrs_dir = root / "docs" / "ADRS"
    if not adrs_dir.is_dir():
        return []

    constraints: list[Constraint] = []
    for path in sorted(adrs_dir.glob("*.md")):
        body = _read_text(path)
        if not body:
            continue
        rel = path.relative_to(root).as_posix()

        title = ""
        status = ""
        decision_lines: list[str] = []
        section: str | None = None

        for raw in body.splitlines():
            line = raw.rstrip("\r")
            if not title:
                m = _ADR_TITLE_RE.match(line.strip())
                if m:
                    title = m.group("title").strip()
                    continue
            if _ADR_STATUS_RE.match(line.strip()):
                section = "status"
                continue
            if _ADR_DECISION_RE.match(line.strip()):
                section = "decision"
                continue
            if _ADR_OTHER_HEADING_RE.match(line.strip()) and section is not None:
                section = None
                continue
            if section == "status":
                stripped = line.strip()
                if stripped and not status:
                    status = stripped
            elif section == "decision":
                if line.strip():
                    decision_lines.append(line.strip())

        if not title:
            notes.append(f"ADR has no title heading: {rel}")
            continue

        # Skip ADRs that aren't currently active.
        status_lower = status.lower()
        if status_lower and status_lower not in {"accepted", "active"}:
            notes.append(f"ADR not active ({status!r}): {rel}")
            continue

        # First paragraph of the Decision section becomes the
        # constraint text. Stop at first blank line.
        decision_text = ""
        for piece in decision_lines:
            if not piece:
                if decision_text:
                    break
                continue
            decision_text = (decision_text + " " + piece).strip()
            if len(decision_text) > 240:
                decision_text = decision_text[:237] + "..."
                break

        if not decision_text:
            notes.append(f"ADR has no Decision section text: {rel}")
            continue

        slug = _slugify(title)
        constraints.append(
            Constraint(
                id=f"adr:{slug}",
                kind=CONSTRAINT_KIND_ADR,
                text=f"{title}: {decision_text}",
                severity=DEFAULT_SEVERITY,
                source_path=rel,
                source_section="Decision",
            )
        )
    return constraints


# ---- public API -------------------------------------------------------


def load_constraints(root: Path | str) -> ConstraintLoadResult:
    """Aggregate constraints from all three sources. Missing
    sources contribute zero constraints; malformed sections add
    a note but never raise."""
    root_path = Path(root)
    notes: list[str] = []
    constraints: list[Constraint] = []
    constraints.extend(_load_oaths(root_path, notes))
    constraints.extend(_load_constraints_file(root_path, notes))
    constraints.extend(_load_adrs(root_path, notes))
    # Dedupe by id, last write wins (later sources override).
    by_id: dict[str, Constraint] = {}
    for constraint in constraints:
        by_id[constraint.id] = constraint
    return ConstraintLoadResult(
        constraints=list(by_id.values()),
        notes=notes,
    )


def filter_by_severity(
    constraints: Iterable[Constraint], *, severity: str
) -> list[Constraint]:
    cleaned = (severity or "").strip().lower()
    return [c for c in constraints if c.severity == cleaned]


__all__ = [
    "CONSTRAINT_KIND_ADR",
    "CONSTRAINT_KIND_OATH",
    "CONSTRAINT_KIND_RULE",
    "Constraint",
    "ConstraintLoadResult",
    "DEFAULT_SEVERITY",
    "SEVERITIES",
    "SEVERITY_ADVISORY",
    "SEVERITY_BLOCKING",
    "SEVERITY_WARN",
    "filter_by_severity",
    "load_constraints",
]
