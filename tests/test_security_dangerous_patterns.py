"""Tests for PH-11 Slice 11.5 — dangerous-pattern detection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.security.dangerous_patterns import (
    DANGEROUS_PATTERNS,
    DangerFinding,
    DangerScanResult,
    DangerousPattern,
    scan_code,
    scan_paths,
)


# ---- catalogue invariants --------------------------------------------


class CatalogueTests(unittest.TestCase):
    def test_catalogue_has_patterns(self) -> None:
        self.assertGreater(len(DANGEROUS_PATTERNS), 0)

    def test_every_entry_has_remediation(self) -> None:
        for entry in DANGEROUS_PATTERNS:
            self.assertTrue(entry.remediation, f"missing on {entry.name}")

    def test_every_entry_has_severity(self) -> None:
        for entry in DANGEROUS_PATTERNS:
            self.assertIn(
                entry.severity,
                {"critical", "high", "medium", "advisory"},
                f"bad severity on {entry.name}: {entry.severity!r}",
            )


# ---- DangerousPattern.matches_language -------------------------------


class MatchesLanguageTests(unittest.TestCase):
    def test_no_languages_matches_all(self) -> None:
        import re

        entry = DangerousPattern(
            name="x", severity="high", regex=re.compile(r"x"), remediation="..."
        )
        self.assertTrue(entry.matches_language("python"))
        self.assertTrue(entry.matches_language("go"))
        self.assertTrue(entry.matches_language(None))

    def test_specific_language_only(self) -> None:
        import re

        entry = DangerousPattern(
            name="py.eval",
            severity="high",
            regex=re.compile(r"eval"),
            remediation="...",
            languages=("python",),
        )
        self.assertTrue(entry.matches_language("python"))
        self.assertTrue(entry.matches_language("PYTHON"))
        self.assertFalse(entry.matches_language("go"))

    def test_unknown_language_passes(self) -> None:
        """When language is None we accept everything (the caller
        scanner decides)."""
        import re

        entry = DangerousPattern(
            name="py.eval",
            severity="high",
            regex=re.compile(r"eval"),
            remediation="...",
            languages=("python",),
        )
        self.assertTrue(entry.matches_language(None))


# ---- scan_code -------------------------------------------------------


class ScanCodeTests(unittest.TestCase):
    def test_clean_code_no_findings(self) -> None:
        self.assertEqual(scan_code("x = 1 + 1"), [])

    def test_blank_text(self) -> None:
        self.assertEqual(scan_code(""), [])

    def test_eval_detected(self) -> None:
        findings = scan_code("result = eval(user_input)", language="python")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].pattern, "python.eval")
        self.assertEqual(findings[0].severity, "critical")
        self.assertIn("eval(", findings[0].snippet)

    def test_exec_detected(self) -> None:
        findings = scan_code("exec(payload)", language="python")
        self.assertTrue(any(f.pattern == "python.exec" for f in findings))

    def test_shell_true_detected(self) -> None:
        findings = scan_code(
            'subprocess.run(cmd, shell=True)', language="python"
        )
        self.assertTrue(any(f.pattern == "python.shell_true" for f in findings))

    def test_os_system_detected(self) -> None:
        findings = scan_code('os.system("ls")', language="python")
        self.assertTrue(any(f.pattern == "python.os_system" for f in findings))

    def test_pickle_loads_detected(self) -> None:
        findings = scan_code("pickle.loads(data)", language="python")
        self.assertTrue(
            any(f.pattern == "python.pickle_loads" for f in findings)
        )

    def test_remediation_attached(self) -> None:
        findings = scan_code("eval(x)", language="python")
        self.assertGreaterEqual(len(findings), 1)
        self.assertTrue(findings[0].remediation)
        self.assertIn("ast.literal_eval", findings[0].remediation)

    def test_language_filter_skips_non_python(self) -> None:
        # Same code, different language → python-specific patterns
        # don't fire.
        findings = scan_code('eval("x")', language="go")
        for f in findings:
            self.assertFalse(f.pattern.startswith("python."))

    def test_multiple_lines(self) -> None:
        text = "ok\neval(x)\nexec(y)\n"
        findings = scan_code(text, language="python")
        # eval on line 2, exec on line 3.
        eval_findings = [f for f in findings if f.pattern == "python.eval"]
        exec_findings = [f for f in findings if f.pattern == "python.exec"]
        self.assertEqual(eval_findings[0].line, 2)
        self.assertEqual(exec_findings[0].line, 3)

    def test_snippet_truncated(self) -> None:
        long_line = "x" * 200 + " eval(y)"
        findings = scan_code(long_line, language="python")
        self.assertGreaterEqual(len(findings), 1)
        self.assertLessEqual(len(findings[0].snippet), 80)


# ---- scan_paths ------------------------------------------------------


class ScanPathsTests(unittest.TestCase):
    def test_python_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "main.py"
            f.write_text("eval(user_input)\n", encoding="utf-8")
            result = scan_paths([f], root=root)
        self.assertGreaterEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].location, "main.py")

    def test_clean_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "ok.py"
            f.write_text("print('hi')\n", encoding="utf-8")
            result = scan_paths([f], root=root)
        self.assertTrue(result.ok)
        self.assertEqual(result.files_scanned, 1)

    def test_missing_file_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ghost = Path(tmp) / "ghost.py"
            result = scan_paths([ghost], root=tmp)
        self.assertEqual(result.files_scanned, 0)


# ---- DangerScanResult / DangerFinding --------------------------------


class DataclassTests(unittest.TestCase):
    def test_finding_to_dict(self) -> None:
        f = DangerFinding(
            pattern="python.eval",
            severity="critical",
            location="x.py",
            line=2,
            snippet="eval(x)",
            remediation="...",
        )
        payload = f.to_dict()
        for key in {"pattern", "severity", "location", "line", "snippet", "remediation"}:
            self.assertIn(key, payload)

    def test_scan_result_ok_when_empty(self) -> None:
        result = DangerScanResult()
        self.assertTrue(result.ok)
        self.assertTrue(result.to_dict()["ok"])


if __name__ == "__main__":
    unittest.main()
