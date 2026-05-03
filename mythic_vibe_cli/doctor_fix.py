"""Phase 20.2 — ``doctor --fix`` auto-remediation (tightly scoped).

Two automatic, safe, reversible fixes:

- **MFX-001 — missing standard ``mythic/`` subdirectories.**
  Re-creates the canonical layout (``mythic/``, ``mythic/packets/``,
  ``mythic/verifications/``, ``mythic/handoffs/``,
  ``mythic/checkins/``, ``mythic/forge/``, ``mythic/reflections/``,
  ``mythic/backups/``). Pure ``mkdir(parents=True, exist_ok=True)`` —
  reversible by ``rmdir`` on empty directories.
- **MFX-002 — missing CHANGELOG ``[Unreleased]`` section.**
  Inserts an empty ``## [Unreleased]`` section after the file's
  H1 title. Never edits existing version sections; never
  removes anything.

**Hard rule (per the PH-19/20 plan):** ``doctor --fix`` MUST
NOT touch user-authored content — constraints, oaths, ADRs,
packets, decisions. Only structural/scaffolding gaps that the
operator clearly intends to exist are remediated.

Cross-platform: pure stdlib. The CLI integration in
``commands.py:cmd_doctor`` reads ``--fix`` and surfaces the
results in both text and JSON output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


# Canonical mythic/ subdirectories. Order matters for the report
# (depth-first reads better in operator output).
STANDARD_SUBDIRS: tuple[str, ...] = (
    "",                  # mythic/ itself
    "packets",
    "verifications",
    "handoffs",
    "checkins",
    "forge",
    "reflections",
    "backups",
)

UNRELEASED_HEADER = "## [Unreleased]"
UNRELEASED_TEMPLATE = (
    f"{UNRELEASED_HEADER}\n"
    "\n"
    "### Added\n"
    "\n"
    "- (no entries yet — auto-inserted by `doctor --fix` MFX-002)\n"
    "\n"
)

FixSeverity = Literal["fixed", "would_fix", "skipped"]


@dataclass(frozen=True)
class FixAction:
    """One fix attempt. ``status`` reflects what actually
    happened: ``fixed`` (real action taken), ``would_fix``
    (dry-run mode), ``skipped`` (precondition missing — e.g.
    no CHANGELOG.md to fix)."""

    rule_id: str
    status: FixSeverity
    target: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "status": self.status,
            "target": self.target,
            "message": self.message,
        }


@dataclass
class FixReport:
    """Aggregate of all fix attempts in one ``doctor --fix`` run."""

    actions: list[FixAction] = field(default_factory=list)
    dry_run: bool = False

    @property
    def fixed(self) -> list[FixAction]:
        return [a for a in self.actions if a.status == "fixed"]

    @property
    def would_fix(self) -> list[FixAction]:
        return [a for a in self.actions if a.status == "would_fix"]

    @property
    def skipped(self) -> list[FixAction]:
        return [a for a in self.actions if a.status == "skipped"]

    def to_dict(self) -> dict[str, object]:
        return {
            "dry_run": self.dry_run,
            "counts": {
                "fixed": len(self.fixed),
                "would_fix": len(self.would_fix),
                "skipped": len(self.skipped),
            },
            "actions": [a.to_dict() for a in self.actions],
        }


def _ensure_mythic_subdirs(
    root: Path, *, dry_run: bool
) -> list[FixAction]:
    """MFX-001 — create any missing standard mythic/ subdirs.
    No-ops on subdirs that already exist."""
    actions: list[FixAction] = []
    mythic = root / "mythic"
    for relative in STANDARD_SUBDIRS:
        target = mythic / relative if relative else mythic
        if target.is_dir():
            continue
        if dry_run:
            actions.append(
                FixAction(
                    rule_id="MFX-001",
                    status="would_fix",
                    target=str(target),
                    message="would create missing mythic subdirectory",
                )
            )
            continue
        target.mkdir(parents=True, exist_ok=True)
        actions.append(
            FixAction(
                rule_id="MFX-001",
                status="fixed",
                target=str(target),
                message="created missing mythic subdirectory",
            )
        )
    return actions


_H1_HEADING_RE = re.compile(r"^#\s+\S", re.MULTILINE)
_VERSION_HEADING_RE = re.compile(r"^##\s+\[", re.MULTILINE)


def _insert_unreleased_block(text: str) -> str:
    """Pure helper: produce the modified CHANGELOG text with
    the Unreleased block inserted after the H1 title (or at the
    file head if no H1 exists). Never modifies existing version
    sections; the new block lands BEFORE the first ``## [...]``
    heading."""
    if UNRELEASED_HEADER in text:
        # Defensive — caller should check first, but we never
        # add a duplicate.
        return text

    h1_match = _H1_HEADING_RE.search(text)
    insert_at = 0
    if h1_match is not None:
        # Insert right after the H1 line — find the next newline.
        next_newline = text.find("\n", h1_match.end())
        if next_newline == -1:
            insert_at = len(text)
        else:
            insert_at = next_newline + 1

    # Skip past blank lines or pre-existing intro paragraphs to
    # land just before the first version heading. Operators
    # often have an "All notable changes…" preamble; the
    # Unreleased block belongs AFTER that preamble but BEFORE
    # the first version section.
    version_match = _VERSION_HEADING_RE.search(text, insert_at)
    if version_match is not None:
        insert_at = version_match.start()

    # Ensure the inserted block is sandwiched by blank lines so
    # it parses cleanly on every Markdown renderer.
    prefix = text[:insert_at]
    suffix = text[insert_at:]
    if prefix and not prefix.endswith("\n\n"):
        if prefix.endswith("\n"):
            prefix = prefix + "\n"
        else:
            prefix = prefix + "\n\n"
    return prefix + UNRELEASED_TEMPLATE + suffix


def _ensure_changelog_unreleased(
    root: Path, *, dry_run: bool
) -> list[FixAction]:
    """MFX-002 — insert ``## [Unreleased]`` if absent.
    Skipped (with a clear message) when no CHANGELOG.md exists —
    we don't auto-create the file; that's an operator decision.
    """
    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        return [
            FixAction(
                rule_id="MFX-002",
                status="skipped",
                target=str(changelog),
                message=(
                    "CHANGELOG.md not present — fix skipped "
                    "(this rule never auto-creates the file)"
                ),
            )
        ]

    try:
        text = changelog.read_text(encoding="utf-8")
    except OSError as exc:
        return [
            FixAction(
                rule_id="MFX-002",
                status="skipped",
                target=str(changelog),
                message=f"could not read CHANGELOG.md: {exc}",
            )
        ]

    if UNRELEASED_HEADER in text:
        # Already has it — no action.
        return []

    if dry_run:
        return [
            FixAction(
                rule_id="MFX-002",
                status="would_fix",
                target=str(changelog),
                message="would insert missing ## [Unreleased] section",
            )
        ]

    new_text = _insert_unreleased_block(text)
    # Atomic write via PH-19 helper to defend against partial
    # write on power loss / signal.
    from .runtime.atomic_write import atomic_write_text

    atomic_write_text(changelog, new_text)
    return [
        FixAction(
            rule_id="MFX-002",
            status="fixed",
            target=str(changelog),
            message="inserted missing ## [Unreleased] section",
        )
    ]


def run_doctor_fix(root: Path, *, dry_run: bool = False) -> FixReport:
    """Run all auto-fix rules against the project root and
    return a :class:`FixReport`. Pure orchestration — each rule
    handler does its own filesystem work.

    ``dry_run=True`` makes every rule report what it WOULD do
    without performing the action. Useful for previewing.
    """
    actions: list[FixAction] = []
    actions.extend(_ensure_mythic_subdirs(root, dry_run=dry_run))
    actions.extend(_ensure_changelog_unreleased(root, dry_run=dry_run))
    return FixReport(actions=actions, dry_run=dry_run)


__all__ = [
    "STANDARD_SUBDIRS",
    "UNRELEASED_HEADER",
    "FixAction",
    "FixReport",
    "FixSeverity",
    "run_doctor_fix",
]
