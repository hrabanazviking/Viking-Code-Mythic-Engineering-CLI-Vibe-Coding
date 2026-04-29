# Spec for the Pi-derived timings primitive. Pi has no direct unit tests for
# timings.ts; these cases are Mythic-flavored unit tests written against the
# Python port.
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# The Python implementation under test (mythic_vibe_cli.runtime.timings) is
# licensed under the Apache License, Version 2.0.
"""Tests for the Pi-derived timings primitive."""

from __future__ import annotations

import importlib
import io
import os
import time
import unittest
from contextlib import redirect_stderr

from mythic_vibe_cli.runtime.timings import print_timings, record, reset_timings

timings_module = importlib.import_module("mythic_vibe_cli.runtime.timings")


class TimingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._prior_env = os.environ.get("MYTHIC_TIMING")
        os.environ.pop("MYTHIC_TIMING", None)
        timings_module._entries.clear()

    def tearDown(self) -> None:
        if self._prior_env is None:
            os.environ.pop("MYTHIC_TIMING", None)
        else:
            os.environ["MYTHIC_TIMING"] = self._prior_env
        timings_module._entries.clear()

    def test_record_is_noop_when_disabled(self) -> None:
        record("step-1")
        record("step-2")

        self.assertEqual(timings_module._entries, [])

    def test_record_collects_labelled_deltas_when_enabled(self) -> None:
        os.environ["MYTHIC_TIMING"] = "1"
        reset_timings()
        record("warm-up")
        time.sleep(0.005)
        record("middle-step")

        self.assertEqual(len(timings_module._entries), 2)
        labels = [entry.label for entry in timings_module._entries]
        self.assertEqual(labels, ["warm-up", "middle-step"])
        for entry in timings_module._entries:
            self.assertGreaterEqual(entry.ms, 0.0)

    def test_reset_timings_clears_state(self) -> None:
        os.environ["MYTHIC_TIMING"] = "1"
        record("a")
        record("b")
        self.assertEqual(len(timings_module._entries), 2)

        reset_timings()

        self.assertEqual(timings_module._entries, [])

    def test_print_timings_emits_pi_style_format_to_stderr(self) -> None:
        os.environ["MYTHIC_TIMING"] = "1"
        reset_timings()
        record("first")
        record("second")

        buffer = io.StringIO()
        with redirect_stderr(buffer):
            print_timings()
        rendered = buffer.getvalue()

        self.assertIn("--- Mythic Timings ---", rendered)
        self.assertIn("first:", rendered)
        self.assertIn("second:", rendered)
        self.assertIn("TOTAL:", rendered)
        self.assertIn("ms", rendered)

    def test_print_timings_is_noop_when_no_entries(self) -> None:
        os.environ["MYTHIC_TIMING"] = "1"
        reset_timings()

        buffer = io.StringIO()
        with redirect_stderr(buffer):
            print_timings()

        self.assertEqual(buffer.getvalue(), "")

    def test_print_timings_is_noop_when_disabled(self) -> None:
        # Populate while enabled, then disable and confirm output is suppressed
        os.environ["MYTHIC_TIMING"] = "1"
        record("populated")
        os.environ["MYTHIC_TIMING"] = "0"

        buffer = io.StringIO()
        with redirect_stderr(buffer):
            print_timings()

        self.assertEqual(buffer.getvalue(), "")

    def test_truthy_env_values_all_enable(self) -> None:
        for value in ("1", "true", "TRUE", "yes", "Yes", "on", "  on  "):
            os.environ["MYTHIC_TIMING"] = value
            timings_module._entries.clear()
            record("under-truthy")
            self.assertEqual(
                len(timings_module._entries), 1, msg=f"value={value!r} should enable"
            )

    def test_falsy_env_values_keep_disabled(self) -> None:
        for value in ("0", "false", "no", "off", ""):
            os.environ["MYTHIC_TIMING"] = value
            timings_module._entries.clear()
            record("under-falsy")
            self.assertEqual(
                timings_module._entries, [], msg=f"value={value!r} should disable"
            )


if __name__ == "__main__":
    unittest.main()
