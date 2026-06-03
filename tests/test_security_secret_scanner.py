"""Tests for PH-11 Slice 11.3 — secret scanner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.security.secret_scanner import (
    ScanResult,
    SecretFinding,
    scan_paths,
    scan_text,
)


# ---- scan_text -------------------------------------------------------


class ScanTextTests(unittest.TestCase):
    def test_clean_text_no_findings(self) -> None:
        self.assertEqual(scan_text("hello world"), [])

    def test_blank_text_no_findings(self) -> None:
        self.assertEqual(scan_text(""), [])

    def test_single_line_secret(self) -> None:
        """One secret may match multiple overlapping patterns; we
        accept >= 1 finding and assert the metadata is consistent."""
        findings = scan_text("api_key=sk-AAAABBBBCCCCDDDD")
        self.assertGreaterEqual(len(findings), 1)
        for finding in findings:
            self.assertEqual(finding.location, "<inline>")
            self.assertEqual(finding.line, 0)  # single line → 0
            self.assertIn("sk-", finding.snippet)

    def test_multi_line_attributes_correct_line(self) -> None:
        """The text has one secret on line 2 that hits multiple
        regexes (sk- prefix AND api_key= keyword); each pattern
        match is a separate finding, but all attribute to line 2."""
        text = "ok line\napi_key=sk-AAAABBBBCCCCDDDD\nmore\n"
        findings = scan_text(text)
        self.assertGreaterEqual(len(findings), 1)
        for finding in findings:
            self.assertEqual(finding.line, 2)

    def test_multiple_secrets_on_different_lines(self) -> None:
        text = (
            "first secret: sk-AAAABBBBCCCCDDDD\n"
            "second secret: AIzaSyABCDEFGHIJ\n"
        )
        findings = scan_text(text)
        # Each line has at least one finding.
        lines_with_findings = {f.line for f in findings}
        self.assertEqual(lines_with_findings, {1, 2})

    def test_severity_critical_for_sk_prefix(self) -> None:
        findings = scan_text("sk-AAAABBBBCCCCDDDD")
        self.assertEqual(findings[0].severity, "critical")

    def test_severity_critical_for_aiza_prefix(self) -> None:
        findings = scan_text("AIzaSyABCDEFGHIJ")
        self.assertEqual(findings[0].severity, "critical")

    def test_severity_medium_for_password_keyword(self) -> None:
        findings = scan_text('password = "hunter2"')
        # At least one finding should be medium severity.
        severities = {f.severity for f in findings}
        self.assertIn("medium", severities)

    def test_snippet_truncated(self) -> None:
        long_line = "x" * 200 + "sk-AAAABBBBCCCCDDDD"
        findings = scan_text(long_line)
        self.assertLessEqual(len(findings[0].snippet), 80)

    def test_dedup_same_pattern_same_line(self) -> None:
        # Same line, same regex pattern → one finding.
        findings = scan_text("sk-AAAABBBBCCCCDDDD")
        self.assertEqual(len(findings), 1)

    def test_custom_location(self) -> None:
        findings = scan_text("sk-AAAABBBBCCCCDDDD", location="custom.py")
        self.assertEqual(findings[0].location, "custom.py")

    def test_token_variable_assignment_is_not_a_secret(self) -> None:
        self.assertEqual(scan_text('token = str(getattr(args, "token", "") or "").strip()'), [])
        self.assertEqual(scan_text("token = token"), [])
        self.assertEqual(scan_text("api_key: str"), [])

    def test_broad_keyword_requires_secret_shaped_literal(self) -> None:
        findings = scan_text('password = "hunter2"')
        self.assertGreaterEqual(len(findings), 1)


# ---- scan_paths ------------------------------------------------------


class ScanPathsTests(unittest.TestCase):
    def test_clean_files_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "clean.py"
            f.write_text("print('hi')\n", encoding="utf-8")
            result = scan_paths([f], root=root)
        self.assertTrue(result.ok)
        self.assertEqual(result.files_scanned, 1)

    def test_secret_in_file_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "main.py"
            f.write_text("api_key='sk-AAAABBBBCCCCDDDD'\n", encoding="utf-8")
            result = scan_paths([f], root=root)
        self.assertFalse(result.ok)
        self.assertGreaterEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].location, "main.py")

    def test_forbidden_path_listed_not_scanned(self) -> None:
        """Files matching a forbidden glob (.env etc) must be flagged
        without being opened — the scanner refuses to read secrets
        out of explicitly secret-bearing files."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env_file = root / ".env"
            env_file.write_text(
                "API_KEY=sk-AAAABBBBCCCCDDDD\n", encoding="utf-8"
            )
            result = scan_paths([env_file], root=root)
        self.assertEqual(result.files_scanned, 0)
        self.assertEqual(result.forbidden_paths, [".env"])
        self.assertEqual(result.findings, [])

    def test_missing_file_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ghost = root / "ghost.py"
            result = scan_paths([ghost], root=root)
        self.assertEqual(result.files_scanned, 0)
        self.assertEqual(result.findings, [])

    def test_decode_error_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "weird.bin"
            binary.write_bytes(b"\x80\x81\x82\x83")
            result = scan_paths([binary], root=root)
        self.assertEqual(result.files_scanned, 0)

    def test_root_relative_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            f = root / "src" / "auth.py"
            f.write_text("token='sk-AAAABBBBCCCCDDDD'\n", encoding="utf-8")
            result = scan_paths([f], root=root)
        self.assertGreaterEqual(len(result.findings), 1)
        # Forward-slash path regardless of OS.
        self.assertEqual(result.findings[0].location, "src/auth.py")


# ---- ScanResult / SecretFinding --------------------------------------


class DataclassTests(unittest.TestCase):
    def test_finding_to_dict(self) -> None:
        f = SecretFinding(
            pattern="sk-",
            severity="critical",
            location="x.py",
            line=3,
            snippet="key=...",
        )
        payload = f.to_dict()
        for key in {"pattern", "severity", "location", "line", "snippet"}:
            self.assertIn(key, payload)

    def test_scan_result_to_dict(self) -> None:
        result = ScanResult(
            findings=[
                SecretFinding(pattern="x", severity="high", location="y.py")
            ],
            forbidden_paths=[".env"],
            files_scanned=2,
        )
        payload = result.to_dict()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["files_scanned"], 2)
        self.assertEqual(payload["forbidden_paths"], [".env"])
        self.assertFalse(payload["ok"])

    def test_scan_result_ok_when_empty(self) -> None:
        result = ScanResult()
        self.assertTrue(result.ok)
        self.assertTrue(result.to_dict()["ok"])


if __name__ == "__main__":
    unittest.main()
