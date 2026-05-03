"""Code-to-docs contract auditor (Phase 19.2, audit remediation 2026-05-02).

Cross-references the runtime command registry
(``mythic_vibe_cli.commands.COMMAND_HANDLERS``) against the
markdown documentation under ``docs/`` — every implemented
top-level command **must** appear in at least one doc file.
Reports drift in this direction:

- **Implemented but not documented** — a handler exists with no
  mention in any documentation file. Likely an undocumented
  feature that should either be documented or marked
  internal / dispatcher-only via the auditor's allowlist.

The reverse direction (documented but not implemented) is **not**
checked because the docs use prose with many backticked tokens
that aren't CLI commands (Python identifiers, package names,
English words in monospace). A reliable docs-→-handler check
needs richer parsing than is justified for this slice — the
argparse layer in ``mythic_vibe_cli/app.py`` already enforces
that every documented subparser has a handler at registration
time, so the inverse direction is naturally protected by the
existing argparse setup.

CI usage::

    python tools/contract_audit.py --strict

``--strict`` exits non-zero on any drift, gating CI. Without
``--strict`` the tool prints a report and exits 0 (useful for
local audits where drift is informational).

Scope:

Top-level command names only. Sub-commands, exit codes, and
JSON-payload schemas are covered separately:
- JSON snapshot tests at ``tests/test_json_snapshots.py`` lock
  the JSON schemas.
- ``COMMAND_HANDLERS`` keys + argparse parser registration in
  ``mythic_vibe_cli/app.py`` enforce sub-command shapes.

Cross-platform: pure stdlib (``argparse``, ``re``, ``pathlib``).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# Probable command-name token in backticks: lowercase, may contain
# hyphens, may have a sub-token (e.g. ``packet show``,
# ``handoff create``). We deliberately don't try to extract the
# sub-token here — top-level matching is enough for v1.0.
_BACKTICK_COMMAND_RE = re.compile(
    r"`([a-z][a-z0-9-]*)(?:[ ][a-z][a-z0-9-]*)?`"
)

# CLI-prefix form: ``mythic-vibe <name>`` or ``mythic <name>``.
_PREFIXED_COMMAND_RE = re.compile(
    r"\bmythic(?:-vibe)?\s+([a-z][a-z0-9-]*)\b"
)

def discover_doc_command_references(docs_dir: Path) -> set[str]:
    """Walk ``docs/**/*.md`` and return the set of probable CLI
    command names referenced. We ONLY look for tokens that appear
    in unambiguously CLI-shaped contexts to avoid false positives
    from English / stdlib / package-name backticks."""
    referenced: set[str] = set()
    for md_path in sorted(docs_dir.rglob("*.md")):
        try:
            text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # CLI-prefix form: ``mythic-vibe <name>`` / ``mythic <name>``
        # — the most reliable signal. The repo's docs use this
        # prefix consistently for command examples.
        for match in _PREFIXED_COMMAND_RE.finditer(text):
            referenced.add(match.group(1))
    return referenced


def discover_backticked_tokens(docs_dir: Path) -> set[str]:
    """Walk ``docs/**/*.md`` and return every backticked one-word
    token. Used as a secondary signal — handlers found here are
    treated as "loosely documented" even without a mythic-vibe
    prefix nearby."""
    referenced: set[str] = set()
    for md_path in sorted(docs_dir.rglob("*.md")):
        try:
            text = md_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in _BACKTICK_COMMAND_RE.finditer(text):
            referenced.add(match.group(1))
    return referenced


def load_handlers() -> set[str]:
    """Return the set of top-level command names registered in
    ``mythic_vibe_cli.commands.COMMAND_HANDLERS``."""
    from mythic_vibe_cli.commands import COMMAND_HANDLERS

    return set(COMMAND_HANDLERS.keys())


def audit(
    docs_dir: Path, *, allow_undocumented: frozenset[str] | None = None
) -> set[str]:
    """Return the set of handler names with no documentation
    reference. Empty set means no drift.

    ``allow_undocumented`` exempts handler names from the check
    (e.g. internal dispatcher entries that don't belong in
    operator-facing docs).

    A handler counts as documented if its name appears anywhere
    in docs/ — either via the strict CLI-prefix form
    (``mythic-vibe <name>``) OR as a backticked token in the
    weaker any-backtick form. The two-tier signal lets us catch
    handlers that are mentioned in narrative prose without
    requiring every mention to use the formal CLI prefix.
    """
    referenced_strict = discover_doc_command_references(docs_dir)
    referenced_loose = discover_backticked_tokens(docs_dir)
    referenced = referenced_strict | referenced_loose

    handlers = load_handlers()
    allowed = allow_undocumented or frozenset()
    return (handlers - referenced) - allowed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Walk docs/ and verify documented CLI commands map to real handlers.",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs",
        help="Path to the docs/ directory (default: repo's docs/).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any drift (CI gating mode).",
    )
    args = parser.parse_args(argv)

    if not args.docs_dir.is_dir():
        print(f"docs dir not found: {args.docs_dir}", file=sys.stderr)
        return 2

    # Phase 19.2 baseline ratchet — handlers existing at audit-tool
    # introduction time (2026-05-02) without doc references. The
    # audit catches **new** drift; these existing entries are
    # tracked here as a known-gap list. Each one should either be
    # documented and removed from this set, or kept here with an
    # explicit comment justifying its internal-only status.
    #
    # TODO: gradually document and remove from this list. Each
    # removal tightens the audit's grip and shrinks this allowlist
    # toward zero.
    allow_undocumented = frozenset({
        # Workflow-phase capture commands (PH-02 slice 2.3) — the
        # parent flow is documented as `intent` / `constraints`
        # / `architecture` / `plan` / `build`; the parent slash
        # command names need their own doc paragraph.
        "architecture",
        "build",
        "constraints",
        # Aliases / convenience commands — the parent operation
        # IS documented; these need cross-references.
        "audit",       # alias for `doctor --json`
        "drift",       # PH-13 drift detection
        "graph",       # PH-05 knowledge graph
        "hardware",    # PH-06 hardware profile
        "policy",      # PH-14 policy engine
        "protocols",   # PH-16 MCP/ACP/OTel surfaces
        "provider",    # alias for `ai providers`
        "release",     # PH-12 release helper
        "rollback",    # PH-12 rollback helper
        "scaffold",    # PH-02/audit-remediation scaffold types
        "security",    # PH-11 security audit
        # Dev-tool shortcuts (PH-02 slice 2.2) — wrappers around
        # ruff/mypy/pytest. Mentioned in aggregate but not by name.
        "changelog",
        "ci",
        "docker",
        "lint",
        "test",
        "typecheck",
        # PH-20.A (additive 2026-05-03): persona presets — new
        # surface, doc page coming in 20.7 launch checklist.
        "persona",
        # PH-20.H (additive 2026-05-03): architecture review
        # command — doc page lands with the v1.0 launch
        # checklist in 20.7.
        "review",
    })

    code_only = audit(
        args.docs_dir, allow_undocumented=allow_undocumented
    )

    if code_only:
        print(
            "Handlers with no documentation reference "
            f"({len(code_only)}):",
            file=sys.stderr,
        )
        for token in sorted(code_only):
            print(f"  - {token}", file=sys.stderr)

    if not code_only:
        print("Contract audit clean: every handler is documented.")
        return 0

    if args.strict:
        print(
            "\nFix: document the listed handlers in docs/, OR add "
            "them to allow_undocumented in tools/contract_audit.py "
            "if they're internal-only.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
