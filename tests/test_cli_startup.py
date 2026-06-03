from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli import cli


class CliStartupBoundaryTests(unittest.TestCase):
    def test_crash_is_reported_as_json_without_traceback_escape(self) -> None:
        old_state = os.environ.get("MYTHIC_STATE_HOME")
        old_restarts = os.environ.get("MYTHIC_STARTUP_RESTARTS")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.environ["MYTHIC_STATE_HOME"] = tmp
                os.environ["MYTHIC_STARTUP_RESTARTS"] = "0"
                stdout = io.StringIO()
                stderr = io.StringIO()
                with mock.patch(
                    "mythic_vibe_cli.app.main",
                    side_effect=RuntimeError("startup broke"),
                ):
                    with redirect_stdout(stdout), redirect_stderr(stderr):
                        code = cli.main(["status", "--json"])

                payload = json.loads(stdout.getvalue())
                report_path = Path(payload["crash_report"])

                self.assertEqual(code, 1)
                self.assertEqual(payload["error"], "RuntimeError")
                self.assertEqual(payload["message"], "startup broke")
                self.assertTrue(report_path.is_file())
                self.assertIn("RuntimeError: startup broke", report_path.read_text(encoding="utf-8"))
                self.assertEqual(stderr.getvalue(), "")
        finally:
            if old_state is None:
                os.environ.pop("MYTHIC_STATE_HOME", None)
            else:
                os.environ["MYTHIC_STATE_HOME"] = old_state
            if old_restarts is None:
                os.environ.pop("MYTHIC_STARTUP_RESTARTS", None)
            else:
                os.environ["MYTHIC_STARTUP_RESTARTS"] = old_restarts

    def test_empty_argv_retries_once_by_default(self) -> None:
        old_state = os.environ.get("MYTHIC_STATE_HOME")
        old_restarts = os.environ.get("MYTHIC_STARTUP_RESTARTS")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.environ["MYTHIC_STATE_HOME"] = tmp
                os.environ.pop("MYTHIC_STARTUP_RESTARTS", None)
                stderr = io.StringIO()
                mocked_main = mock.Mock(side_effect=[RuntimeError("transient"), 0])
                with mock.patch("mythic_vibe_cli.app.main", mocked_main):
                    with redirect_stderr(stderr):
                        code = cli.main([])

                self.assertEqual(code, 0)
                self.assertEqual(mocked_main.call_count, 2)
                self.assertIn("retrying once", stderr.getvalue())
        finally:
            if old_state is None:
                os.environ.pop("MYTHIC_STATE_HOME", None)
            else:
                os.environ["MYTHIC_STATE_HOME"] = old_state
            if old_restarts is None:
                os.environ.pop("MYTHIC_STARTUP_RESTARTS", None)
            else:
                os.environ["MYTHIC_STARTUP_RESTARTS"] = old_restarts

    def test_keyboard_interrupt_returns_shell_interrupt_code(self) -> None:
        stderr = io.StringIO()
        with mock.patch("mythic_vibe_cli.app.main", side_effect=KeyboardInterrupt):
            with redirect_stderr(stderr):
                code = cli.main(["status"])

        self.assertEqual(code, 130)
        self.assertIn("Interrupted", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
