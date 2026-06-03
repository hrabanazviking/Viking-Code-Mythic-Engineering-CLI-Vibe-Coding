"""Tests for PH-11 Slice 11.7 — `mythic-vibe security audit`."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from mythic_vibe_cli.commands import cmd_security_audit, cmd_security_dispatch
from mythic_vibe_cli.exit_codes import OPERATIONAL_FAILURE, SUCCESS, USER_INPUT_ERROR


def _ns(path: str, **overrides: object) -> argparse.Namespace:
    base = dict(
        path=path,
        approval=None,
        json=True,
        sarif=False,
        scope="active",
    )
    base.update(overrides)
    return argparse.Namespace(**base)


class CmdSecurityAuditCleanRepoTests(unittest.TestCase):
    def test_clean_repo_returns_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text(
                "def hello():\n    print('hi')\n", encoding="utf-8"
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_security_audit(_ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertFalse(payload["blocking"])
        self.assertGreaterEqual(payload["files_audited"], 1)
        self.assertEqual(payload["secret_scan"]["count"], 0)
        self.assertEqual(payload["dangerous_pattern_scan"]["count"], 0)


class CmdSecurityAuditFindingsTests(unittest.TestCase):
    def test_secret_finding_blocks_and_returns_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text(
                "API_KEY = 'sk-AAAABBBBCCCCDDDD'\n", encoding="utf-8"
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_security_audit(_ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)
        self.assertTrue(payload["blocking"])
        self.assertGreater(payload["secret_scan"]["count"], 0)
        # Critical severity from sk- prefix.
        self.assertGreater(payload["severity_counts"].get("critical", 0), 0)

    def test_dangerous_pattern_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "danger.py").write_text(
                "import os\nos.system(user_input)\n", encoding="utf-8"
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_security_audit(_ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)
        self.assertGreater(payload["dangerous_pattern_scan"]["count"], 0)

    def test_dotenv_listed_as_forbidden_not_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(
                "API_KEY=sk-AAAABBBBCCCCDDDD\n", encoding="utf-8"
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_security_audit(_ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertIn(".env", payload["secret_scan"]["forbidden_paths"])
        # The .env file should not have been opened/scanned for findings.
        for finding in payload["secret_scan"]["findings"]:
            self.assertNotEqual(finding["location"], ".env")

    def test_default_active_scope_excludes_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic_vibe_cli").mkdir()
            (root / "mythic_vibe_cli" / "ok.py").write_text("x = 1\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "danger.py").write_text("eval(user_input)\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_security_audit(_ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["scope"], "active")
        self.assertFalse(payload["blocking"])
        self.assertEqual(payload["dangerous_pattern_scan"]["count"], 0)

    def test_tests_scope_scans_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mythic_vibe_cli").mkdir()
            (root / "mythic_vibe_cli" / "ok.py").write_text("x = 1\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "danger.py").write_text("eval(user_input)\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_security_audit(_ns(str(root), scope="tests"))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)
        self.assertEqual(payload["scope"], "tests")
        self.assertGreater(payload["dangerous_pattern_scan"]["count"], 0)

    def test_sarif_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("eval(user_input)\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_security_audit(_ns(str(root), sarif=True))
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, OPERATIONAL_FAILURE)
        self.assertEqual(payload["version"], "2.1.0")
        self.assertEqual(payload["runs"][0]["tool"]["driver"]["name"], "mythic-vibe security audit")
        self.assertGreater(len(payload["runs"][0]["results"]), 0)


class CmdSecurityAuditPolicyReportingTests(unittest.TestCase):
    def test_default_policies_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("x = 1\n", encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_security_audit(_ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertFalse(payload["privacy"]["enabled"])
        self.assertFalse(payload["sandbox"]["enabled"])
        # Approval mode comes from TTY heuristic — could be either.
        self.assertIn(payload["approval_mode"], {"suggest", "auto", "partial"})

    def test_security_toml_policy_surfaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("x = 1\n", encoding="utf-8")
            (root / "mythic").mkdir()
            (root / "mythic" / "security.toml").write_text(
                "[approval]\nmode = \"auto\"\n"
                "[sandbox]\nenabled = true\ndirectory_restriction = true\n"
                "[privacy]\nenabled = true\nallow_paths = [\"src/\"]\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_security_audit(_ns(str(root)))
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["approval_mode"], "auto")
        self.assertTrue(payload["sandbox"]["enabled"])
        self.assertTrue(payload["sandbox"]["directory_restriction"])
        self.assertTrue(payload["privacy"]["enabled"])
        self.assertEqual(payload["privacy"]["allow_paths"], ["src/"])

    def test_cli_approval_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("x = 1\n", encoding="utf-8")
            (root / "mythic").mkdir()
            (root / "mythic" / "security.toml").write_text(
                "[approval]\nmode = \"auto\"\n", encoding="utf-8"
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_security_audit(_ns(str(root), approval="suggest"))
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["approval_mode"], "suggest")


class CmdSecurityDispatchTests(unittest.TestCase):
    def test_audit_dispatches_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                security_command="audit",
                path=tmp,
                approval=None,
                json=True,
            )
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_security_dispatch(ns)
        self.assertEqual(exit_code, SUCCESS)

    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        ns = argparse.Namespace(security_command="ghost")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_security_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("Unknown security subcommand", stderr.getvalue())


class SecurityArgparseTests(unittest.TestCase):
    def test_audit_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["security", "audit", "--path", ".", "--scope", "tests", "--sarif", "--json"])
        self.assertEqual(ns.command, "security")
        self.assertEqual(ns.security_command, "audit")
        self.assertEqual(ns.path, ".")
        self.assertEqual(ns.scope, "tests")
        self.assertTrue(ns.sarif)

    def test_approval_choices_enforced(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(
                    ["security", "audit", "--approval", "ghost"]
                )


if __name__ == "__main__":
    unittest.main()
