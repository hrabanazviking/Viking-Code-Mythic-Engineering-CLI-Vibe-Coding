# Spec for the Pi-derived exec primitive. Pi has no direct unit tests for
# exec.ts under tests/; these are Mythic-flavored unit tests against the
# Python port, exercising the timeout and cancel-event paths that pi
# verifies via integration with the agent-session runtime.
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# The Python implementation under test (mythic_vibe_cli.runtime.exec) is
# licensed under the Apache License, Version 2.0.
"""Tests for the Pi-derived exec primitive."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest

from mythic_vibe_cli.runtime.exec import ExecResult, exec_command


def _sleep_script(seconds: float) -> str:
    return f"import time; time.sleep({seconds})"


class ExecCommandTests(unittest.TestCase):
    def test_successful_command_captures_stdout_and_zero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = exec_command(
                sys.executable,
                ["-c", "print('hello world')"],
                tmp,
            )

            self.assertIsInstance(result, ExecResult)
            self.assertEqual(result.code, 0)
            self.assertFalse(result.killed)
            self.assertIn("hello world", result.stdout)
            self.assertEqual(result.stderr, "")

    def test_non_zero_exit_is_propagated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = exec_command(
                sys.executable,
                ["-c", "import sys; sys.exit(2)"],
                tmp,
            )

            self.assertEqual(result.code, 2)
            self.assertFalse(result.killed)

    def test_stderr_is_captured_separately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = exec_command(
                sys.executable,
                ["-c", "import sys; sys.stderr.write('boom\\n'); sys.exit(1)"],
                tmp,
            )

            self.assertEqual(result.code, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("boom", result.stderr)

    def test_timeout_kills_long_running_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            start = time.perf_counter()
            result = exec_command(
                sys.executable,
                ["-c", _sleep_script(10.0)],
                tmp,
                timeout=0.5,
            )
            elapsed = time.perf_counter() - start

            self.assertTrue(result.killed)
            self.assertLess(elapsed, 6.0, msg=f"timeout kill should be fast; took {elapsed:.2f}s")

    def test_cancel_event_kills_running_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cancel = threading.Event()

            def trigger() -> None:
                time.sleep(0.2)
                cancel.set()

            trigger_thread = threading.Thread(target=trigger, daemon=True)
            trigger_thread.start()

            start = time.perf_counter()
            result = exec_command(
                sys.executable,
                ["-c", _sleep_script(10.0)],
                tmp,
                cancel_event=cancel,
            )
            elapsed = time.perf_counter() - start
            trigger_thread.join(timeout=1.0)

            self.assertTrue(result.killed)
            self.assertLess(elapsed, 6.0)

    def test_already_set_cancel_event_kills_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cancel = threading.Event()
            cancel.set()

            start = time.perf_counter()
            result = exec_command(
                sys.executable,
                ["-c", _sleep_script(10.0)],
                tmp,
                cancel_event=cancel,
            )
            elapsed = time.perf_counter() - start

            self.assertTrue(result.killed)
            self.assertLess(elapsed, 6.0)

    def test_missing_command_returns_127(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = exec_command(
                "this_command_definitely_does_not_exist_anywhere",
                ["arg"],
                tmp,
            )

            self.assertEqual(result.code, 127)
            self.assertFalse(result.killed)
            self.assertEqual(result.stdout, "")
            self.assertNotEqual(result.stderr, "")

    def test_cwd_is_respected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = exec_command(
                sys.executable,
                ["-c", "import os; print(os.getcwd())"],
                tmp,
            )

            self.assertEqual(result.code, 0)
            self.assertIn(os.path.realpath(tmp), os.path.realpath(result.stdout.strip()))

    def test_to_dict_round_trip(self) -> None:
        result = ExecResult(stdout="out", stderr="err", code=0, killed=False)
        payload = result.to_dict()

        self.assertEqual(
            payload,
            {"stdout": "out", "stderr": "err", "code": 0, "killed": False},
        )


if __name__ == "__main__":
    unittest.main()
