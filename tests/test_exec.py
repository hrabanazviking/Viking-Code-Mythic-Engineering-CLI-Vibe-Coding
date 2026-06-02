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

from mythic_vibe_cli.runtime.exec import ExecResult, exec_command, spawn_process


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


class SpawnProcessTests(unittest.TestCase):
    def test_spawn_process_returns_live_handle_with_captured_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = spawn_process(
                [sys.executable, "-c", "print('spawned')"],
                cwd=tmp,
                stdin="devnull",
                stdout="pipe",
                stderr="pipe",
                text=True,
            )
            stdout, stderr = proc.communicate(timeout=5.0)

        self.assertEqual(proc.returncode, 0)
        self.assertIn("spawned", stdout)
        self.assertEqual(stderr, "")

    def test_spawn_process_rejects_empty_argv(self) -> None:
        with self.assertRaises(ValueError):
            spawn_process([])

    def test_spawn_process_missing_executable_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                spawn_process(
                    ["this_command_definitely_does_not_exist_anywhere"],
                    cwd=tmp,
                )


# ---- Phase 19.0 / BS-3 (audit remediation 2026-05-02) ----------------
#
# Regression: callers that pass the new DEFAULT_EXEC_TIMEOUT_SECONDS
# constant (or any positive float) must see ``killed=True`` and a
# clean ExecResult — not a hang — when the subprocess outlives the
# timeout. The 4 audit-flagged call-sites (scanner._run_git,
# handoff._git, verify/git_diff._git, verify/test_runner.run_command)
# now pass the default 300s timeout; this test proves the bound
# actually engages.


class DefaultExecTimeoutTests(unittest.TestCase):
    """The DEFAULT_EXEC_TIMEOUT_SECONDS constant exists and the
    underlying timeout path engages when a subprocess outlives it."""

    def test_default_constant_is_300_seconds(self) -> None:
        from mythic_vibe_cli.runtime.exec import DEFAULT_EXEC_TIMEOUT_SECONDS

        self.assertEqual(DEFAULT_EXEC_TIMEOUT_SECONDS, 300.0)

    def test_short_timeout_kills_a_long_running_subprocess(self) -> None:
        """Use a very short timeout (0.5s) on a subprocess that
        sleeps 5s. ExecResult must come back with killed=True and
        non-zero exit code, not block until the sleep finishes."""
        with tempfile.TemporaryDirectory() as tmp:
            start = time.perf_counter()
            result = exec_command(
                sys.executable,
                ["-c", _sleep_script(5.0)],
                cwd=tmp,
                timeout=0.5,
            )
            elapsed = time.perf_counter() - start
        self.assertTrue(result.killed)
        self.assertNotEqual(result.code, 0)
        # The kill must have happened well before the 5s sleep would
        # naturally complete. Generous upper bound to absorb CI noise.
        self.assertLess(elapsed, 4.0)

    def test_callsites_inherit_default_via_constant(self) -> None:
        """The 4 audit-flagged call-sites import the same
        DEFAULT_EXEC_TIMEOUT_SECONDS constant. Spot-check their
        modules expose the import without raising."""
        from mythic_vibe_cli.context.scanner import (
            DEFAULT_EXEC_TIMEOUT_SECONDS as scanner_default,
        )
        from mythic_vibe_cli.handoff import (
            DEFAULT_EXEC_TIMEOUT_SECONDS as handoff_default,
        )
        from mythic_vibe_cli.verify.git_diff import (
            DEFAULT_EXEC_TIMEOUT_SECONDS as git_diff_default,
        )
        from mythic_vibe_cli.verify.test_runner import (
            DEFAULT_EXEC_TIMEOUT_SECONDS as test_runner_default,
        )

        self.assertEqual(scanner_default, 300.0)
        self.assertEqual(handoff_default, 300.0)
        self.assertEqual(git_diff_default, 300.0)
        self.assertEqual(test_runner_default, 300.0)


if __name__ == "__main__":
    unittest.main()
