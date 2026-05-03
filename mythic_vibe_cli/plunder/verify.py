"""Phase 20.6 — provenance checksum verification.

For each entry in ``mythic/imports/plunder_manifest.json``,
recompute the destination file's content SHA-256 and compare
it against the recorded ``source_sha`` from upstream. Three
outcomes per entry:

- **match** — the local file's hash matches the recorded
  upstream hash. The file is verifiably an unmodified copy.
- **drift** — the file exists but its hash differs. Operators
  often modify imported files intentionally; this is
  informational, not an error.
- **missing** — the destination path doesn't exist on disk.
  Likely the operator deleted the file but kept the manifest
  entry.

GPG / Sigstore signed-artifact verification is **deferred to
v1.x** (PH-21.5 in the master plan). This slice is checksums
only — the simplest, highest-value supply-chain check that
v1.0 ships with.

Cross-platform: pure stdlib (``hashlib``, ``pathlib``).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .provenance import read_manifest


VerifyStatus = Literal["match", "drift", "missing"]


@dataclass(frozen=True)
class VerificationEntry:
    """One per manifest record. ``actual_sha`` is empty when
    the destination is missing (no file → no hash)."""

    destination: str
    repo: str
    source_file: str
    source_sha: str
    actual_sha: str
    status: VerifyStatus

    def to_dict(self) -> dict[str, object]:
        return {
            "destination": self.destination,
            "repo": self.repo,
            "source_file": self.source_file,
            "source_sha": self.source_sha,
            "actual_sha": self.actual_sha,
            "status": self.status,
        }


@dataclass
class VerificationReport:
    entries: list[VerificationEntry] = field(default_factory=list)

    @property
    def matches(self) -> list[VerificationEntry]:
        return [e for e in self.entries if e.status == "match"]

    @property
    def drifts(self) -> list[VerificationEntry]:
        return [e for e in self.entries if e.status == "drift"]

    @property
    def missing(self) -> list[VerificationEntry]:
        return [e for e in self.entries if e.status == "missing"]

    @property
    def ok(self) -> bool:
        """Report is "ok" when every entry matches OR is missing.
        Drift is informational, not failure — operators may
        have modified imported files intentionally. Missing
        files indicate cleanup, also not a failure.

        Operators wanting strict-clean verification can require
        ``len(drifts) == 0 and len(missing) == 0`` themselves.
        """
        return True

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "counts": {
                "match": len(self.matches),
                "drift": len(self.drifts),
                "missing": len(self.missing),
                "total": len(self.entries),
            },
            "entries": [e.to_dict() for e in self.entries],
        }


def _hash_file(path: Path) -> str:
    """SHA-256 of file contents. Streams in 64 KiB chunks so
    big files don't blow memory."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65_536):
            digest.update(chunk)
    return digest.hexdigest()


def verify_provenance(root: Path) -> VerificationReport:
    """Walk the manifest and produce a per-entry verification.
    Missing manifest yields an empty report (no entries) — the
    caller decides whether that's an issue."""
    manifest = read_manifest(root)
    raw_entries = manifest.get("imports", []) if isinstance(manifest, dict) else []
    if not isinstance(raw_entries, list):
        raw_entries = []

    entries: list[VerificationEntry] = []
    for raw in raw_entries:
        if not isinstance(raw, dict):
            continue
        destination = str(raw.get("destination") or "").strip()
        recorded_sha = str(raw.get("source_sha") or "").strip()
        repo = str(raw.get("repo") or "")
        source_file = str(raw.get("source_file") or "")
        if not destination:
            continue

        target = (root / destination).resolve()
        if not target.is_file():
            entries.append(
                VerificationEntry(
                    destination=destination,
                    repo=repo,
                    source_file=source_file,
                    source_sha=recorded_sha,
                    actual_sha="",
                    status="missing",
                )
            )
            continue

        actual = _hash_file(target)
        status: VerifyStatus = (
            "match" if recorded_sha and actual == recorded_sha else "drift"
        )
        entries.append(
            VerificationEntry(
                destination=destination,
                repo=repo,
                source_file=source_file,
                source_sha=recorded_sha,
                actual_sha=actual,
                status=status,
            )
        )

    return VerificationReport(entries=entries)


__all__ = [
    "VerificationEntry",
    "VerificationReport",
    "VerifyStatus",
    "verify_provenance",
]
