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
    suspend_stdout_guard,
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

    def test_suspend_stdout_guard_captures_raw_writes_then_restores(self) -> None:
        take_over_stdout()
        nested = io.StringIO()

        with suspend_stdout_guard():
            self.assertFalse(is_stdout_taken_over())
            sys.stdout = nested
            write_raw_stdout("nested payload\n")
            sys.stdout = self.fake_stdout

        self.assertTrue(is_stdout_taken_over())
        self.assertEqual(nested.getvalue(), "nested payload\n")
        self.assertEqual(self.fake_stdout.getvalue(), "")


# PH-23.8 — coverage push for output_guard's _ProxyStream
# property getters + isatty error branches. The existing tests
# above cover the routing behavior; these exercise the file-like
# attribute accessors directly (lines 52, 56, 60, 69-72, 81).


class ProxyStreamAccessorTests(unittest.TestCase):
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

    def test_proxy_encoding_falls_back_to_utf8(self) -> None:
        # The proxy's encoding property returns sys.stderr.encoding
        # if set, otherwise utf-8. StringIO has no encoding attr,
        # so this exercises the fallback path.
        take_over_stdout()
        encoding = sys.stdout.encoding
        self.assertIsInstance(encoding, str)
        # Must be a non-empty truthy string per the implementation.
        self.assertTrue(encoding)

    def test_proxy_name_is_descriptive(self) -> None:
        take_over_stdout()
        name = sys.stdout.name
        self.assertEqual(name, "<stdout-routed-to-stderr>")

    def test_proxy_closed_reflects_underlying_stderr(self) -> None:
        take_over_stdout()
        # StringIO's closed attribute is False by default.
        self.assertFalse(sys.stdout.closed)
        # Force-close the underlying stderr and verify the proxy
        # reports it.
        self.fake_stderr.close()
        self.assertTrue(sys.stdout.closed)

    def test_proxy_isatty_returns_false_for_stringio(self) -> None:
        # StringIO.isatty returns False; the proxy must surface
        # the same value.
        take_over_stdout()
        self.assertFalse(sys.stdout.isatty())

    def test_proxy_isatty_swallows_attribute_error(self) -> None:
        # If the underlying stderr lacks isatty (or raises), the
        # proxy returns False rather than propagating.
        take_over_stdout()

        class BrokenStderr:
            def isatty(self) -> bool:
                raise AttributeError("no isatty")

            def write(self, text: str) -> int:
                return len(text)

            def flush(self) -> None:
                pass

        sys.stderr = BrokenStderr()  # type: ignore[assignment]
        try:
            self.assertFalse(sys.stdout.isatty())
        finally:
            sys.stderr = self.fake_stderr

    def test_proxy_isatty_swallows_value_error(self) -> None:
        # ValueError is raised by closed io.IOBase streams when
        # isatty is called. The proxy must downgrade to False.
        take_over_stdout()
        self.fake_stderr.close()
        self.assertFalse(sys.stdout.isatty())

    def test_proxy_fileno_delegates_to_stderr(self) -> None:
        # fileno is delegated; StringIO raises UnsupportedOperation
        # which is fine — we just verify the call reaches stderr.
        take_over_stdout()
        with self.assertRaises((io.UnsupportedOperation, OSError)):
            sys.stdout.fileno()


if __name__ == "__main__":
    unittest.main()
