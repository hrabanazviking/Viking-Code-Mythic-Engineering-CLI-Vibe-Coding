"""Phase 20.1 — packet lint.

Heuristic linter for stored packet markdown. Catches the most
common patterns that lead to bad provider output:

- **Missing required sections** (Role / Intent / Architecture
  Context / Files In Scope / Verification Commands). These are
  load-bearing per ``codex_bridge:_render_packet``.
- **Vague intent** — fewer than ``MIN_INTENT_CHARS`` characters,
  or contains hedging tokens like ``etc.``, ``stuff``, ``...``.
- **Empty architecture anchor** — section exists but body is
  blank / placeholder / shorter than ``MIN_ARCH_CHARS``.
- **No verification commands listed** — no enumerated commands
  inside the section.
- **No files in scope** — empty section blocks the agent from
  knowing what it's allowed to touch.
- **No acceptance criteria** — heuristic: neither an explicit
  ``## Acceptance`` heading nor any "test" / "assert" /
  "verify" keyword in the verification block.

Pure stdlib (``re``, ``dataclasses``). No filesystem / network
access — caller passes the text in. The CLI wrapper in
``commands.py:cmd_packet_lint`` handles loading the packet
from disk.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Config knobs — exposed at module level so the test suite can pin them
# (and so future operators can tune via override without code change).
# ---------------------------------------------------------------------------

MIN_INTENT_CHARS = 20
MIN_ARCH_CHARS = 50

VAGUE_INTENT_TOKENS: tuple[str, ...] = (
    "etc.",
    " stuff",
    " things",
    "...",
    "TBD",
    "TODO",
)

REQUIRED_SECTIONS: tuple[str, ...] = (
    "Role",
    "Intent",
    "Architecture Context",
    "Files In Scope",
    "Verification Commands",
)

LintSeverity = Literal["error", "warning", "info"]

SEVERITY_ORDER: dict[str, int] = {
    "error": 0,
    "warning": 1,
    "info": 2,
}


@dataclass(frozen=True)
class LintFinding:
    """One linter finding. ``rule_id`` is stable for downstream
    tooling; ``message`` is human-readable."""

    rule_id: str
    severity: LintSeverity
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass
class LintReport:
    """Aggregated results of one packet's lint pass."""

    findings: list[LintFinding] = field(default_factory=list)

    @property
    def errors(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def infos(self) -> list[LintFinding]:
        return [f for f in self.findings if f.severity == "info"]

    @property
    def ok(self) -> bool:
        """A packet is "ok" when no error-severity findings fired.
        Warnings and infos do NOT block; they're advisory."""
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "counts": {
                "error": len(self.errors),
                "warning": len(self.warnings),
                "info": len(self.infos),
            },
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Section parsing — the packet markdown uses ``## N. <Title>`` headings.
# We accept both numbered (``## 4. Architecture Context``) and bare
# (``## Architecture Context``) forms so ingested third-party packets
# without numbering still lint.
# ---------------------------------------------------------------------------

_SECTION_RE = re.compile(
    r"^##\s+(?:\d+\.\s*)?(?P<title>.+?)\s*$",
    re.MULTILINE,
)


def _split_sections(text: str) -> dict[str, str]:
    """Split packet markdown into ``{title: body}`` chunks. Body
    is the text from after the heading up to (not including) the
    next heading or end-of-text. Titles are stripped and
    case-preserved; lookups should normalize case."""
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        title = match.group("title").strip()
        body_start = match.end()
        body_end = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )
        body = text[body_start:body_end].strip()
        sections[title] = body
    return sections


def _norm_title(title: str) -> str:
    """Lowercase + collapse whitespace — matches REQUIRED_SECTIONS
    against ingested packets where capitalization may vary."""
    return re.sub(r"\s+", " ", title.strip().lower())


def _has_section(sections: dict[str, str], wanted: str) -> bool:
    target = _norm_title(wanted)
    return any(_norm_title(title) == target for title in sections)


def _section_body(sections: dict[str, str], wanted: str) -> str:
    target = _norm_title(wanted)
    for title, body in sections.items():
        if _norm_title(title) == target:
            return body
    return ""


def _enumerated_lines(body: str) -> list[str]:
    """Return non-empty list-style lines (``- foo`` or ``* foo``)
    inside a section body. Trims the bullet marker. Used to count
    items in Files-In-Scope / Verification Commands."""
    lines = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if stripped.startswith(("-", "*")) and len(stripped) > 1:
            content = stripped[1:].strip()
            if content:
                lines.append(content)
    return lines


# ---------------------------------------------------------------------------
# Rules — each is a small function that consumes parsed sections and
# returns 0 or 1 LintFinding. We keep them as simple functions (not
# classes) so adding a rule = appending one function below + one entry
# to RULES.
# ---------------------------------------------------------------------------


def rule_required_sections(
    sections: dict[str, str], _text: str
) -> list[LintFinding]:
    """PKL-001: every load-bearing packet section must be
    present. Missing sections are an **error** because the
    packet is incomplete by construction."""
    missing = [
        title
        for title in REQUIRED_SECTIONS
        if not _has_section(sections, title)
    ]
    if not missing:
        return []
    return [
        LintFinding(
            rule_id="PKL-001",
            severity="error",
            message=(
                "missing required section(s): "
                + ", ".join(missing)
            ),
        )
    ]


def rule_intent_length(
    sections: dict[str, str], _text: str
) -> list[LintFinding]:
    """PKL-002: Intent body must clear MIN_INTENT_CHARS. Short
    intents typically resolve to "do the thing" prose that
    confuses the agent."""
    body = _section_body(sections, "Intent")
    if not body:
        # PKL-001 already covers the missing-section case; don't
        # double-report.
        return []
    if len(body) < MIN_INTENT_CHARS:
        return [
            LintFinding(
                rule_id="PKL-002",
                severity="warning",
                message=(
                    f"intent body has {len(body)} chars "
                    f"(< {MIN_INTENT_CHARS}); add detail so the "
                    "agent has unambiguous input"
                ),
            )
        ]
    return []


def rule_architecture_anchor(
    sections: dict[str, str], _text: str
) -> list[LintFinding]:
    """PKL-003: Architecture Context body must contain real
    architectural anchors, not a placeholder."""
    body = _section_body(sections, "Architecture Context")
    if not body:
        return []
    if len(body) < MIN_ARCH_CHARS:
        return [
            LintFinding(
                rule_id="PKL-003",
                severity="warning",
                message=(
                    f"architecture context is {len(body)} chars "
                    f"(< {MIN_ARCH_CHARS}); add file:line anchors "
                    "or domain references"
                ),
            )
        ]
    return []


def rule_verification_commands_listed(
    sections: dict[str, str], _text: str
) -> list[LintFinding]:
    """PKL-004: Verification Commands must enumerate at least
    one command — agents skip verification when none is named."""
    body = _section_body(sections, "Verification Commands")
    if not body:
        return []
    if not _enumerated_lines(body):
        return [
            LintFinding(
                rule_id="PKL-004",
                severity="warning",
                message=(
                    "Verification Commands section has no listed "
                    "items; add `- pytest -q` or similar"
                ),
            )
        ]
    return []


def rule_files_in_scope_listed(
    sections: dict[str, str], _text: str
) -> list[LintFinding]:
    """PKL-005: Files In Scope must list at least one file —
    otherwise the agent has implicit license to touch
    everything."""
    body = _section_body(sections, "Files In Scope")
    if not body:
        return []
    if not _enumerated_lines(body):
        return [
            LintFinding(
                rule_id="PKL-005",
                severity="warning",
                message=(
                    "Files In Scope is empty; the agent will not "
                    "know which files it may modify"
                ),
            )
        ]
    return []


def rule_intent_vague_tokens(
    sections: dict[str, str], _text: str
) -> list[LintFinding]:
    """PKL-006: Intent body shouldn't contain hedging tokens
    that signal under-specification (etc., stuff, ..., TODO)."""
    body = _section_body(sections, "Intent")
    if not body:
        return []
    body_lc = body.lower()
    hits = [
        token
        for token in VAGUE_INTENT_TOKENS
        if token.lower() in body_lc
    ]
    if not hits:
        return []
    return [
        LintFinding(
            rule_id="PKL-006",
            severity="info",
            message=(
                "intent contains hedging token(s): "
                + ", ".join(repr(t.strip()) for t in hits)
                + "; consider tightening"
            ),
        )
    ]


def rule_acceptance_criteria_present(
    sections: dict[str, str], text: str
) -> list[LintFinding]:
    """PKL-007: heuristic — either the packet has an
    ``## Acceptance`` heading OR the Verification Commands
    section mentions test/assert/verify. Otherwise the agent
    can't tell when it's "done"."""
    if any(
        _norm_title(title).startswith("acceptance")
        for title in sections
    ):
        return []
    verification = _section_body(sections, "Verification Commands")
    body_lc = (verification or "").lower()
    if any(token in body_lc for token in ("test", "assert", "verify")):
        return []
    return [
        LintFinding(
            rule_id="PKL-007",
            severity="info",
            message=(
                "no explicit acceptance criteria — add an "
                "`## Acceptance` section or include a test/"
                "assert/verify command in Verification Commands"
            ),
        )
    ]


RULES = (
    rule_required_sections,
    rule_intent_length,
    rule_architecture_anchor,
    rule_verification_commands_listed,
    rule_files_in_scope_listed,
    rule_intent_vague_tokens,
    rule_acceptance_criteria_present,
)


def lint_packet_text(text: str) -> LintReport:
    """Run every rule against the supplied packet markdown.
    Findings are returned in (severity, rule_id) order so output
    is stable across runs."""
    sections = _split_sections(text)
    findings: list[LintFinding] = []
    for rule in RULES:
        findings.extend(rule(sections, text))
    findings.sort(
        key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.rule_id)
    )
    return LintReport(findings=findings)


__all__ = [
    "MIN_ARCH_CHARS",
    "MIN_INTENT_CHARS",
    "REQUIRED_SECTIONS",
    "RULES",
    "VAGUE_INTENT_TOKENS",
    "LintFinding",
    "LintReport",
    "LintSeverity",
    "lint_packet_text",
]
