"""Phase 20.G — plunder modified-lines attestation.

Per-line accounting of operator modifications to a plundered
file. Pairs with the PH-20.6 SHA-256 verify (which catches
binary equality vs upstream): when the file's hash drifts,
this module says **which lines** drifted.

Output is a structured :class:`ModificationAttestation` with
counts (added / removed / unchanged) plus per-line hashes for
both sides. Suitable for downstream tooling that wants to
diff with stable, reproducible identifiers.

Pure stdlib (``difflib``, ``hashlib``).
"""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


LineKind = Literal["added", "removed", "unchanged"]


@dataclass(frozen=True)
class LineAttestation:
    """One line in the attested diff. ``kind`` tells whether the
    line was added (only in local), removed (only in original),
    or unchanged."""

    line_number: int
    kind: LineKind
    text: str
    sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "line_number": self.line_number,
            "kind": self.kind,
            "text": self.text,
            "sha256": self.sha256,
        }


@dataclass
class ModificationAttestation:
    """Aggregate per-line attestation between the operator's
    local copy and the upstream original."""

    destination: str
    original_sha256: str
    local_sha256: str
    added: int = 0
    removed: int = 0
    unchanged: int = 0
    lines: list[LineAttestation] = field(default_factory=list)

    @property
    def modified(self) -> bool:
        """True when any line was added or removed."""
        return self.added > 0 or self.removed > 0

    def to_dict(self) -> dict[str, object]:
        return {
            "destination": self.destination,
            "original_sha256": self.original_sha256,
            "local_sha256": self.local_sha256,
            "modified": self.modified,
            "counts": {
                "added": self.added,
                "removed": self.removed,
                "unchanged": self.unchanged,
            },
            "lines": [line.to_dict() for line in self.lines],
        }


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_hash(line: str) -> str:
    """SHA-256 of one line, encoded as bytes. Trailing newline
    stripped first so platform-specific line endings don't
    shift the hash."""
    cleaned = line.rstrip("\r\n")
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def attest_modifications(
    *,
    destination: str,
    local_text: str,
    original_text: str,
) -> ModificationAttestation:
    """Compute a per-line attestation between local and
    original. Uses ``difflib.SequenceMatcher`` for stable
    classification regardless of which lines moved."""
    local_lines = local_text.splitlines(keepends=False)
    original_lines = original_text.splitlines(keepends=False)
    matcher = difflib.SequenceMatcher(
        None, original_lines, local_lines, autojunk=False
    )

    lines: list[LineAttestation] = []
    added = 0
    removed = 0
    unchanged = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset, line in enumerate(local_lines[j1:j2]):
                lines.append(
                    LineAttestation(
                        line_number=j1 + offset + 1,
                        kind="unchanged",
                        text=line,
                        sha256=_line_hash(line),
                    )
                )
                unchanged += 1
        elif tag == "delete":
            # Lines present in original, absent in local.
            for offset, line in enumerate(original_lines[i1:i2]):
                lines.append(
                    LineAttestation(
                        line_number=i1 + offset + 1,
                        kind="removed",
                        text=line,
                        sha256=_line_hash(line),
                    )
                )
                removed += 1
        elif tag == "insert":
            # Lines absent in original, present in local.
            for offset, line in enumerate(local_lines[j1:j2]):
                lines.append(
                    LineAttestation(
                        line_number=j1 + offset + 1,
                        kind="added",
                        text=line,
                        sha256=_line_hash(line),
                    )
                )
                added += 1
        elif tag == "replace":
            # Treat as remove + add to keep the per-line model
            # simple. A future iteration could surface "modified"
            # as a paired kind, but operators consuming the
            # report can already join the two via line_number
            # ordering.
            for offset, line in enumerate(original_lines[i1:i2]):
                lines.append(
                    LineAttestation(
                        line_number=i1 + offset + 1,
                        kind="removed",
                        text=line,
                        sha256=_line_hash(line),
                    )
                )
                removed += 1
            for offset, line in enumerate(local_lines[j1:j2]):
                lines.append(
                    LineAttestation(
                        line_number=j1 + offset + 1,
                        kind="added",
                        text=line,
                        sha256=_line_hash(line),
                    )
                )
                added += 1

    return ModificationAttestation(
        destination=destination,
        original_sha256=_sha256_text(original_text),
        local_sha256=_sha256_text(local_text),
        added=added,
        removed=removed,
        unchanged=unchanged,
        lines=lines,
    )


def attest_file(
    *,
    destination: Path,
    original_text: str,
    project_root: Path | None = None,
) -> ModificationAttestation:
    """Convenience: read the local file at ``destination`` and
    call :func:`attest_modifications`. ``destination`` may be
    project-relative when ``project_root`` is provided.
    """
    if project_root is not None and not destination.is_absolute():
        target = (project_root / destination).resolve()
    else:
        target = destination.resolve()
    local_text = target.read_text(encoding="utf-8")
    rel = (
        str(destination)
        if project_root is None
        else str(target.relative_to(project_root.resolve()))
        if target.is_relative_to(project_root.resolve())
        else str(target)
    )
    return attest_modifications(
        destination=rel.replace("\\", "/"),
        local_text=local_text,
        original_text=original_text,
    )


__all__ = [
    "LineAttestation",
    "LineKind",
    "ModificationAttestation",
    "attest_file",
    "attest_modifications",
]
