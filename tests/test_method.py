from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.mythic_data import DEFAULT_METHOD_NOTES, MethodStore


class MethodCommandTests(unittest.TestCase):
    def test_method_status_reports_fallback_profile_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with patch.dict(os.environ, {"MYTHIC_HOME": tmp}), redirect_stdout(output):
                code = app.main(["method", "status", "--json"])

            payload = json.loads(output.getvalue())

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["command"], "method status")
            self.assertEqual(payload["method"]["source"], "fallback")
            self.assertEqual(payload["method"]["profile"], "fallback")
            self.assertFalse(payload["method"]["cached"])
            self.assertIn("workflow", payload["method"]["sections"])
            self.assertIn("verification method", payload["method"]["sections"])

    def test_fallback_method_profile_keeps_the_full_seven_phase_loop(self) -> None:
        expected = ["1) Intent", "2) Constraints", "3) Architecture", "4) Plan", "5) Build", "6) Verify", "7) Reflect"]

        for phase_heading in expected:
            with self.subTest(phase_heading=phase_heading):
                self.assertIn(phase_heading, DEFAULT_METHOD_NOTES)

    def test_method_status_uses_cached_corpus_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_file = Path(tmp) / "method_cache.json"
            cache_file.write_text(
                json.dumps({"source": "https://example.test/method", "content": "# Canonical Method\n\nUse the work loop."}),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"MYTHIC_HOME": tmp}):
                status = MethodStore().status()

            self.assertEqual(status.source, "https://example.test/method")
            self.assertEqual(status.profile, "canonical-cache")
            self.assertTrue(status.cached)
            self.assertEqual(status.freshness, "cached")


if __name__ == "__main__":
    unittest.main()
