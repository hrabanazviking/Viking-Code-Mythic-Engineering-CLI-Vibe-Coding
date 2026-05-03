"""Phase 20.E (audit remediation 2026-05-03) — drift dashboard
tests.

Two layers:

- **Pure rendering** — fabricate `DriftFinding` lists and call
  `build_dashboard_payload` / `render_dashboard_markdown`.
- **CLI integration** — `mythic-vibe drift dashboard` text +
  JSON paths.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest

from mythic_vibe_cli.drift import (
    DriftFinding,
    build_dashboard_payload,
    render_dashboard_markdown,
)
from mythic_vibe_cli.exit_codes import SUCCESS


def _f(category: str, severity: str, path: str = "x") -> DriftFinding:
    return DriftFinding(
        category=category,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        path=path,
        description=f"{category}/{severity} finding",
    )


class BuildDashboardPayloadTests(unittest.TestCase):
    def test_empty_findings_yields_zero_totals(self) -> None:
        payload = build_dashboard_payload([])
        self.assertEqual(payload["total_findings"], 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["by_category"], {})
        self.assertEqual(
            payload["by_severity"],
            {"info": 0, "warning": 0, "error": 0},
        )

    def test_groups_by_category(self) -> None:
        findings = [
            _f("undocumented_handler", "warning"),
            _f("undocumented_handler", "warning"),
            _f("undocumented_module", "info"),
            _f("superseded_decision", "warning"),
        ]
        payload = build_dashboard_payload(findings)
        self.assertEqual(payload["total_findings"], 4)
        cats = payload["by_category"]
        self.assertEqual(cats["undocumented_handler"]["total"], 2)
        self.assertEqual(cats["undocumented_module"]["total"], 1)
        self.assertEqual(cats["superseded_decision"]["total"], 1)

    def test_ok_false_when_error_severity_present(self) -> None:
        findings = [_f("undocumented_handler", "error")]
        payload = build_dashboard_payload(findings)
        self.assertFalse(payload["ok"])

    def test_ok_true_with_only_warnings_and_info(self) -> None:
        findings = [
            _f("a", "warning"),
            _f("b", "info"),
        ]
        payload = build_dashboard_payload(findings)
        self.assertTrue(payload["ok"])

    def test_per_category_severity_breakdown(self) -> None:
        findings = [
            _f("a", "warning"),
            _f("a", "info"),
            _f("a", "warning"),
        ]
        payload = build_dashboard_payload(findings)
        a = payload["by_category"]["a"]
        self.assertEqual(a["by_severity"]["warning"], 2)
        self.assertEqual(a["by_severity"]["info"], 1)
        self.assertEqual(a["by_severity"]["error"], 0)


class RenderDashboardMarkdownTests(unittest.TestCase):
    def test_empty_renders_no_drift_block(self) -> None:
        output = render_dashboard_markdown([])
        self.assertIn("# Drift Dashboard", output)
        self.assertIn("Total findings:** 0", output)
        self.assertIn("OK", output)
        self.assertIn("No drift detected", output)

    def test_non_empty_renders_severity_and_category_tables(self) -> None:
        findings = [
            _f("undocumented_handler", "warning"),
            _f("undocumented_module", "info"),
        ]
        output = render_dashboard_markdown(findings)
        self.assertIn("| Severity | Count |", output)
        self.assertIn("| Category | Total | info | warning | error |", output)
        self.assertIn("undocumented_handler", output)
        self.assertIn("undocumented_module", output)

    def test_error_severity_marks_status_fail(self) -> None:
        findings = [_f("c", "error")]
        output = render_dashboard_markdown(findings)
        self.assertIn("FAIL", output)


class CmdDriftDashboardIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_drift

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_drift(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_flat_drift_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                path=tmp, subcommand="", json=False,
            ))
        self.assertEqual(code, SUCCESS)
        # Flat invocation uses the original render path.
        self.assertIn("Drift scan", output)

    def test_dashboard_subcommand_text_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                path=tmp, subcommand="dashboard", json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("# Drift Dashboard", output)

    def test_dashboard_subcommand_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                path=tmp, subcommand="dashboard", json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["command"], "drift dashboard")
        self.assertIn("by_category", payload)
        self.assertIn("by_severity", payload)


if __name__ == "__main__":
    unittest.main()
