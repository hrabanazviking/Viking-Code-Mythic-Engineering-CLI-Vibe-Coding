# Spec inspired by badlogic/pi-mono (packages/coding-agent/test/stdout-cleanliness.test.ts)
# adapted to a unit-test shape that exercises the output_guard primitive directly.
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# The Python implementation under test (mythic_vibe_cli.runtime.output_guard)
# is licensed under the Apache License, Version 2.0.
"""Tests for the Pi-derived stdout output guard, ported as a synchronous
Python primitive."""

from __future__ import annotations

import importlib
import io
import sys
import unittest

from mythic_vibe_cli.runtime.output_guard import (
    flush_raw_stdout,
    is_stdout_taken_over,
    json_output_guard,
    restore_stdout,
    take_over_stdout,
    write_raw_stdout,
)

og_module = importlib.import_module("mythic_vibe_cli.runtime.output_guard")


class OutputGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        self.fake_stdout = io.StringIO()
        self.fake_stderr = io.StringIO()
        sys.stdout = self.fake_stdout
        sys.stderr = self.fake_stderr

    def tearDown(self) -> None:
        if is_stdout_taken_over():
            restore_stdout()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

    def test_takeover_routes_stdout_writes_to_stderr(self) -> None:
        take_over_stdout()

        sys.stdout.write("polluted output\n")
        sys.stdout.flush()

        self.assertTrue(is_stdout_taken_over())
        self.assertEqual(self.fake_stdout.getvalue(), "")
        self.assertEqual(self.fake_stderr.getvalue(), "polluted output\n")

    def test_takeover_is_idempotent(self) -> None:
        take_over_stdout()
        proxy_after_first = sys.stdout

        take_over_stdout()

        self.assertIs(sys.stdout, proxy_after_first)
        self.assertTrue(is_stdout_taken_over())

    def test_restore_returns_original_stdout(self) -> None:
        take_over_stdout()
        self.assertTrue(is_stdout_taken_over())

        restore_stdout()

        self.assertFalse(is_stdout_taken_over())
        self.assertIs(sys.stdout, self.fake_stdout)

    def test_restore_is_noop_when_not_taken_over(self) -> None:
        self.assertFalse(is_stdout_taken_over())

        restore_stdout()

        self.assertFalse(is_stdout_taken_over())
        self.assertIs(sys.stdout, self.fake_stdout)

    def test_write_raw_stdout_targets_real_stdout_during_takeover(self) -> None:
        take_over_stdout()

        written = write_raw_stdout("protocol payload\n")

        self.assertEqual(written, len("protocol payload\n"))
        self.assertEqual(self.fake_stdout.getvalue(), "protocol payload\n")
        self.assertEqual(self.fake_stderr.getvalue(), "")

    def test_write_raw_stdout_targets_current_stdout_when_not_taken_over(self) -> None:
        write_raw_stdout("normal write\n")

        self.assertEqual(self.fake_stdout.getvalue(), "normal write\n")
        self.assertEqual(self.fake_stderr.getvalue(), "")

    def test_flush_raw_stdout_does_not_raise(self) -> None:
        take_over_stdout()
        write_raw_stdout("buffered\n")

        flush_raw_stdout()

        self.assertEqual(self.fake_stdout.getvalue(), "buffered\n")

    def test_print_routes_through_takeover(self) -> None:
        take_over_stdout()

        print("via print()")

        self.assertEqual(self.fake_stdout.getvalue(), "")
        self.assertIn("via print()", self.fake_stderr.getvalue())

    def test_proxy_reports_writable_and_not_readable(self) -> None:
        take_over_stdout()

        self.assertTrue(sys.stdout.writable())
        self.assertFalse(sys.stdout.readable())

    def test_module_state_is_cleared_after_restore(self) -> None:
        self.assertIsNone(og_module._state)
        take_over_stdout()
        self.assertIsNotNone(og_module._state)

        restore_stdout()

        self.assertIsNone(og_module._state)

    def test_json_output_guard_active_isolates_stdout(self) -> None:
        with json_output_guard(active=True):
            self.assertTrue(is_stdout_taken_over())
            print("noise")
            write_raw_stdout("payload\n")

        self.assertFalse(is_stdout_taken_over())
        self.assertEqual(self.fake_stdout.getvalue(), "payload\n")
        self.assertIn("noise", self.fake_stderr.getvalue())

    def test_json_output_guard_inactive_is_transparent(self) -> None:
        with json_output_guard(active=False):
            self.assertFalse(is_stdout_taken_over())
            print("hello")

        self.assertFalse(is_stdout_taken_over())
        self.assertIn("hello", self.fake_stdout.getvalue())
        self.assertEqual(self.fake_stderr.getvalue(), "")

    def test_json_output_guard_restores_on_exception(self) -> None:
        with self.assertRaises(RuntimeError):
            with json_output_guard(active=True):
                self.assertTrue(is_stdout_taken_over())
                raise RuntimeError("kaboom")

        self.assertFalse(is_stdout_taken_over())
        self.assertIs(sys.stdout, self.fake_stdout)


if __name__ == "__main__":
    unittest.main()
