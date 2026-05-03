"""Phase 20.1 (audit remediation 2026-05-02) — packet lint tests.

Covers the seven lint rules in
``mythic_vibe_cli/packet_lint.py`` plus the CLI integration in
``cmd_packet_lint``.

Strategy:
- For the rules layer, hand-craft minimal markdown that
  exercises one rule at a time. Avoids coupling tests to the
  full packet template (which churns more often than the lint
  rules).
- For the CLI layer, write a real packet file under a temp dir
  and invoke ``cmd_packet_lint`` with a faked argparse
  Namespace.

Pure stdlib; no provider calls.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.exit_codes import (
    OPERATIONAL_FAILURE,
    SUCCESS,
    USER_INPUT_ERROR,
)
from mythic_vibe_cli.packet_lint import (
    MIN_ARCH_CHARS,
    MIN_INTENT_CHARS,
    REQUIRED_SECTIONS,
    LintFinding,
    lint_packet_text,
)


# Minimal-but-valid packet fixture that passes every rule. Tests
# mutate copies of this string to fail one rule at a time.
GOOD_PACKET = """\
# Packet PKT-000001

## 1. Role
Forge Worker

## 2. Intent
Implement the new login audit handler with PEP 8 compliance and
deterministic output ordering.

## 3. Constraints
- Audience: advanced
- Phase: build

## 4. Architecture Context
The auth subsystem lives in `src/auth/login.py`. The audit
handler must hook into `AuditMiddleware._record` and emit one
JSON-line per successful auth event.

## 5. Files In Scope
- `src/auth/login.py`
- `tests/test_login_audit.py`

## 6. Files Out of Scope
- `src/billing/`

## 9. Verification Commands
- `pytest tests/test_login_audit.py -q`
- `ruff check src/auth`

## Acceptance
- Test passes on Linux + Windows + macOS.
- No new mypy errors.
"""


class GoodPacketBaselineTests(unittest.TestCase):
    """The reference packet must lint clean (or at most surface
    info-level findings). If this test starts failing, either
    the fixture or the rules need re-aligning before any other
    test in this file can be trusted."""

    def test_baseline_has_no_errors_or_warnings(self) -> None:
        report = lint_packet_text(GOOD_PACKET)
        self.assertTrue(report.ok, msg=str(report.findings))
        self.assertEqual(report.warnings, [])


class RequiredSectionsRuleTests(unittest.TestCase):
    def test_missing_intent_section_is_error(self) -> None:
        text = GOOD_PACKET.replace(
            "## 2. Intent\nImplement", "## 2. Other\nImplement"
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.errors]
        self.assertIn("PKL-001", ids)
        self.assertFalse(report.ok)

    def test_all_missing_listed_in_message(self) -> None:
        # Strip every required heading.
        text = "# Packet\nNo sections here.\n"
        report = lint_packet_text(text)
        pkl001 = [f for f in report.findings if f.rule_id == "PKL-001"]
        self.assertEqual(len(pkl001), 1)
        for required in REQUIRED_SECTIONS:
            self.assertIn(required, pkl001[0].message)


class IntentLengthRuleTests(unittest.TestCase):
    def test_short_intent_warns(self) -> None:
        text = GOOD_PACKET.replace(
            "Implement the new login audit handler with PEP 8 "
            "compliance and\ndeterministic output ordering.",
            "Do it.",
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.warnings]
        self.assertIn("PKL-002", ids)

    def test_threshold_constant_documented(self) -> None:
        """If the threshold changes, the threat-model doc and
        the changelog should reflect it."""
        self.assertEqual(MIN_INTENT_CHARS, 20)


class ArchitectureAnchorRuleTests(unittest.TestCase):
    def test_short_architecture_warns(self) -> None:
        text = GOOD_PACKET.replace(
            "The auth subsystem lives in `src/auth/login.py`. The audit\n"
            "handler must hook into `AuditMiddleware._record` and emit one\n"
            "JSON-line per successful auth event.",
            "TODO",
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.warnings]
        self.assertIn("PKL-003", ids)

    def test_threshold_constant_documented(self) -> None:
        self.assertEqual(MIN_ARCH_CHARS, 50)


class VerificationCommandsRuleTests(unittest.TestCase):
    def test_empty_verification_warns(self) -> None:
        text = GOOD_PACKET.replace(
            "## 9. Verification Commands\n"
            "- `pytest tests/test_login_audit.py -q`\n"
            "- `ruff check src/auth`",
            "## 9. Verification Commands\n(no commands listed)",
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.warnings]
        self.assertIn("PKL-004", ids)


class FilesInScopeRuleTests(unittest.TestCase):
    def test_empty_files_warns(self) -> None:
        text = GOOD_PACKET.replace(
            "## 5. Files In Scope\n"
            "- `src/auth/login.py`\n"
            "- `tests/test_login_audit.py`",
            "## 5. Files In Scope\n(scope intentionally not listed)",
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.warnings]
        self.assertIn("PKL-005", ids)


class VagueTokensRuleTests(unittest.TestCase):
    def test_etc_in_intent_emits_info(self) -> None:
        text = GOOD_PACKET.replace(
            "Implement the new login audit handler with PEP 8 "
            "compliance and\ndeterministic output ordering.",
            "Implement audit logging and other things, etc.",
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.infos]
        self.assertIn("PKL-006", ids)

    def test_clean_intent_does_not_fire(self) -> None:
        report = lint_packet_text(GOOD_PACKET)
        ids = [f.rule_id for f in report.findings]
        self.assertNotIn("PKL-006", ids)


class AcceptanceCriteriaRuleTests(unittest.TestCase):
    def test_no_acceptance_no_test_keyword_emits_info(self) -> None:
        # Replace the verification block with commands that contain
        # zero test/assert/verify substrings so the heuristic
        # genuinely fires.
        text = GOOD_PACKET.replace(
            "- `pytest tests/test_login_audit.py -q`\n"
            "- `ruff check src/auth`",
            "- `python build.py`\n"
            "- `ruff check src/auth`",
        )
        text = text.replace(
            "## Acceptance\n"
            "- Test passes on Linux + Windows + macOS.\n"
            "- No new mypy errors.\n",
            "",
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.infos]
        self.assertIn("PKL-007", ids)

    def test_test_keyword_in_verification_satisfies_rule(self) -> None:
        """A `pytest` invocation in the verification block counts
        as acceptance criteria for the heuristic, even without an
        explicit `## Acceptance` heading."""
        text = GOOD_PACKET.replace(
            "## Acceptance\n"
            "- Test passes on Linux + Windows + macOS.\n"
            "- No new mypy errors.\n",
            "",
        )
        report = lint_packet_text(text)
        ids = [f.rule_id for f in report.infos]
        self.assertNotIn("PKL-007", ids)


class FindingOrderTests(unittest.TestCase):
    def test_findings_sorted_by_severity_then_rule_id(self) -> None:
        # Build a packet that fires error + warning + info.
        bad = "# Packet\n## 2. Intent\nshort\n"  # no required sections except Intent → error + short intent
        report = lint_packet_text(bad)
        severities = [f.severity for f in report.findings]
        # Errors first, then warnings, then infos.
        for current, nxt in zip(severities, severities[1:]):
            self.assertLessEqual(
                {"error": 0, "warning": 1, "info": 2}[current],
                {"error": 0, "warning": 1, "info": 2}[nxt],
            )


class LintReportSerializationTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        report = lint_packet_text(GOOD_PACKET)
        payload = report.to_dict()
        self.assertIn("ok", payload)
        self.assertIn("counts", payload)
        self.assertIn("findings", payload)
        # JSON-serialisable.
        json.dumps(payload)

    def test_finding_to_dict(self) -> None:
        finding = LintFinding(
            rule_id="PKL-001", severity="error", message="msg"
        )
        self.assertEqual(
            finding.to_dict(),
            {"rule_id": "PKL-001", "severity": "error", "message": "msg"},
        )


class CmdPacketLintIntegrationTests(unittest.TestCase):
    """Hit the CLI handler through faked argparse Namespaces.
    The handler resolves a packet file from disk; we set up a
    real temp dir each time."""

    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_packet_lint

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_packet_lint(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_lints_explicit_file_and_returns_success_when_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkt = Path(tmp) / "draft.md"
            pkt.write_text(GOOD_PACKET, encoding="utf-8")
            ns = argparse.Namespace(
                path=tmp,
                file=str(pkt),
                packet_id="",
                json=False,
            )
            code, output = self._run(ns)
        self.assertEqual(code, SUCCESS)
        self.assertIn("Packet lint", output)

    def test_returns_operational_failure_on_error_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkt = Path(tmp) / "draft.md"
            pkt.write_text("# bad packet\n", encoding="utf-8")
            ns = argparse.Namespace(
                path=tmp,
                file=str(pkt),
                packet_id="",
                json=False,
            )
            code, _ = self._run(ns)
        self.assertEqual(code, OPERATIONAL_FAILURE)

    def test_missing_file_returns_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp,
                file=str(Path(tmp) / "no-such.md"),
                packet_id="",
                json=False,
            )
            code, _ = self._run(ns)
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_json_mode_returns_serialisable_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkt = Path(tmp) / "draft.md"
            pkt.write_text(GOOD_PACKET, encoding="utf-8")
            ns = argparse.Namespace(
                path=tmp,
                file=str(pkt),
                packet_id="",
                json=True,
            )
            code, output = self._run(ns)
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertIn("findings", payload)
        self.assertIn("counts", payload)
        self.assertIn("source", payload)


if __name__ == "__main__":
    unittest.main()
