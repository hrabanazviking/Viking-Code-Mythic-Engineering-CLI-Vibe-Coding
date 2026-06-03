"""Phase 20.F (audit remediation 2026-05-03) — changelog
classification.

Original behaviour preserved: ``python scripts/check_changelog.py``
runs the release-gate check (CHANGELOG present, required markers,
[Unreleased] mentions current packaging work).

Phase 20.F additions:

- ``--classify`` flag — parse the ``[Unreleased]`` section and
  bucket each bullet line by its conventional-commit-style prefix
  (``feat:`` / ``fix:`` / ``docs:`` / ``refactor:`` / ``test:`` /
  ``chore:`` / ``build:`` / ``perf:`` / ``ci:``). Maps to
  Keep-a-Changelog buckets so the operator can spot mis-categorised
  entries before tagging.
- ``--json`` flag (when used with ``--classify``) — emit the
  classification report as JSON for downstream tooling.

Pure stdlib. No new dependencies. Runs fine in CI as a script.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mythic_vibe_cli.runtime.script_guard import guarded_main


REQUIRED_MARKERS = [
    "## [Unreleased]",
    "### Added",
    "### Changed",
]

# Conventional-commit-style prefixes the classifier recognises.
# Each maps to a Keep-a-Changelog bucket. Adding a new prefix
# requires updating this table AND the docs/RELEASE_CHECKLIST.md
# label table.
LABEL_TO_BUCKET: dict[str, str] = {
    "feat":     "Added",
    "fix":      "Fixed",
    "docs":     "Documentation",
    "refactor": "Changed",
    "test":     "Tests",
    "chore":    "Chore",
    "build":    "Build",
    "perf":     "Changed",
    "ci":       "CI",
    "deps":     "Changed",
    "revert":   "Removed",
    "remove":   "Removed",
}

KNOWN_LABELS: tuple[str, ...] = tuple(sorted(LABEL_TO_BUCKET))

UNCLASSIFIED_BUCKET = "Unclassified"

# Bullet recogniser: leading "- " or "* " plus the entry body.
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
# Prefix recogniser: ``feat: ...`` / ``fix(scope): ...``.
_LABEL_RE = re.compile(
    r"^([a-z]+)(?:\([^)]+\))?:\s+",
    flags=re.IGNORECASE,
)


def _read_changelog(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _release_gate(text: str) -> tuple[int, list[str]]:
    """Original behaviour. Returns (exit_code, error_lines)."""
    missing = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing:
        return 1, [
            "CHANGELOG.md is missing required release marker(s):",
            *(f"- {marker}" for marker in missing),
        ]
    unreleased = text.split("## [Unreleased]", 1)[1]
    if "Stage 13" not in unreleased and "Packaging" not in unreleased:
        return 1, [
            "CHANGELOG.md [Unreleased] should mention the current "
            "packaging/release work before release.",
        ]
    return 0, []


def extract_unreleased_block(text: str) -> str:
    """Return the body between ``## [Unreleased]`` and the next
    top-level ``## [`` heading. Empty string when the marker is
    missing — callers handle that case explicitly."""
    if "## [Unreleased]" not in text:
        return ""
    after = text.split("## [Unreleased]", 1)[1]
    next_release_idx = re.search(r"^##\s+\[", after, flags=re.MULTILINE)
    if next_release_idx is None:
        return after
    return after[: next_release_idx.start()]


def parse_unreleased_entries(unreleased_text: str) -> list[str]:
    """Pull every bullet-list entry out of the [Unreleased] block.
    Returns the raw entry text (everything after ``- ``/``* ``)
    in original order."""
    entries: list[str] = []
    for line in unreleased_text.splitlines():
        match = _BULLET_RE.match(line)
        if match:
            entries.append(match.group(1).strip())
    return entries


def classify_entry(entry: str) -> tuple[str, str]:
    """Return ``(label, bucket)`` for one entry. Unrecognised
    labels return ``("", UNCLASSIFIED_BUCKET)``."""
    match = _LABEL_RE.match(entry)
    if match is None:
        return "", UNCLASSIFIED_BUCKET
    label = match.group(1).lower()
    bucket = LABEL_TO_BUCKET.get(label, UNCLASSIFIED_BUCKET)
    return label, bucket


def classify_unreleased(text: str) -> dict[str, object]:
    """Classify every [Unreleased] entry. Returns a structured
    report with per-bucket counts + per-entry classifications."""
    block = extract_unreleased_block(text)
    entries = parse_unreleased_entries(block)
    classifications: list[dict[str, str]] = []
    bucket_counts: dict[str, int] = {}
    label_counts: dict[str, int] = {}
    for entry in entries:
        label, bucket = classify_entry(entry)
        classifications.append({
            "label": label,
            "bucket": bucket,
            "entry": entry,
        })
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if label:
            label_counts[label] = label_counts.get(label, 0) + 1
    return {
        "total_entries": len(entries),
        "by_bucket": dict(sorted(bucket_counts.items())),
        "by_label": dict(sorted(label_counts.items())),
        "unclassified_count": bucket_counts.get(UNCLASSIFIED_BUCKET, 0),
        "entries": classifications,
    }


def render_classification_text(report: dict[str, object]) -> str:
    lines: list[str] = []
    lines.append("CHANGELOG [Unreleased] classification")
    lines.append(f"  Total entries: {report['total_entries']}")
    lines.append(
        f"  Unclassified: {report['unclassified_count']} "
        "(prefix with feat: / fix: / docs: / etc. to fix)"
    )
    by_bucket = report.get("by_bucket")
    if isinstance(by_bucket, dict) and by_bucket:
        lines.append("  By bucket:")
        for bucket, count in by_bucket.items():
            lines.append(f"    - {bucket}: {count}")
    by_label = report.get("by_label")
    if isinstance(by_label, dict) and by_label:
        lines.append("  By label:")
        for label, count in by_label.items():
            lines.append(f"    - {label}: {count}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Classify [Unreleased] entries by conventional-commit-style label.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="(--classify only) emit the classification as JSON.",
    )
    parser.add_argument(
        "--path",
        default="CHANGELOG.md",
        help="Path to CHANGELOG.md (default: ./CHANGELOG.md).",
    )
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print("Missing CHANGELOG.md")
        return 1

    text = _read_changelog(path)

    if args.classify:
        report = classify_unreleased(text)
        if args.json:
            print(json.dumps(report, indent=2))
            return 0
        print(render_classification_text(report))
        return 0

    code, errors = _release_gate(text)
    if errors:
        for line in errors:
            print(line)
        return code
    print("CHANGELOG.md release gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(
        guarded_main(
            lambda: main(),
            script_name=Path(__file__).name,
            json_mode="--json" in sys.argv,
        )
    )
