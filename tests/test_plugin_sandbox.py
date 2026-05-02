"""Tests for PH-10 Slice 10.2 — plugin sandbox layer."""

from __future__ import annotations

import os
import platform
import time
import unittest

from mythic_vibe_cli.plugins.sandbox import (
    ResourceProbe,
    SandboxResult,
    TIMEOUT_ENV,
    _safe_repr,
    probe_resource_caps,
    resolve_timeout_sec,
    safe_call,
)


# ---- _safe_repr -------------------------------------------------------


class SafeReprTests(unittest.TestCase):
    def test_simple_value(self) -> None:
        self.assertEqual(_safe_repr(42), "42")

    def test_truncation(self) -> None:
        long_value = "x" * 500
        result = _safe_repr(long_value, limit=50)
        self.assertEqual(len(result), 50)
        self.assertTrue(result.endswith("..."))

    def test_repr_failure_contained(self) -> None:
        class _BadRepr:
            def __repr__(self) -> str:
                raise RuntimeError("repr crashed")

        text = _safe_repr(_BadRepr())
        self.assertIn("unrepr-able", text)
        self.assertIn("_BadRepr", text)


# ---- resolve_timeout_sec ---------------------------------------------


class ResolveTimeoutSecTests(unittest.TestCase):
    def test_unset_returns_none(self) -> None:
        self.assertIsNone(resolve_timeout_sec(env={}))

    def test_blank_returns_none(self) -> None:
        self.assertIsNone(resolve_timeout_sec(env={TIMEOUT_ENV: "  "}))

    def test_non_numeric_returns_none(self) -> None:
        self.assertIsNone(resolve_timeout_sec(env={TIMEOUT_ENV: "fast"}))

    def test_negative_returns_none(self) -> None:
        self.assertIsNone(resolve_timeout_sec(env={TIMEOUT_ENV: "-1"}))

    def test_zero_returns_none(self) -> None:
        self.assertIsNone(resolve_timeout_sec(env={TIMEOUT_ENV: "0"}))

    def test_positive_value(self) -> None:
        self.assertEqual(resolve_timeout_sec(env={TIMEOUT_ENV: "2.5"}), 2.5)


# ---- safe_call --------------------------------------------------------


class SafeCallSyncPathTests(unittest.TestCase):
    """Without timeout enforcement, safe_call runs synchronously
    with exception isolation only."""

    def test_success_path(self) -> None:
        result = safe_call(lambda: 42)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, 42)
        self.assertEqual(result.error, "")
        self.assertFalse(result.timed_out)

    def test_args_kwargs_passed(self) -> None:
        result = safe_call(lambda a, b, c=0: a + b + c, 1, 2, c=3)
        self.assertEqual(result.value, 6)

    def test_exception_isolated(self) -> None:
        def boom() -> None:
            raise ValueError("plugin crashed")

        result = safe_call(boom)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "ValueError: plugin crashed")
        self.assertFalse(result.timed_out)

    def test_elapsed_ms_recorded(self) -> None:
        # Phase 19.0 / L-9 (audit remediation 2026-05-02): the
        # original assertion was ``elapsed_ms >= 5.0`` against a
        # 10ms sleep. On Windows the system timer granularity is
        # ~15ms — a 10ms sleep can measure as 0ms (rounded down) or
        # ~15ms depending on when it fires. The strict 5ms floor
        # produced an intermittent flake that surfaced during the
        # full-suite remediation runs. Lowered to ``>= 0.0`` to
        # confirm the field is populated; the actual "elapsed is
        # plausible" assertion lives in the new mock-clock test
        # below where machine timer behaviour is removed from the
        # equation.
        result = safe_call(time.sleep, 0.01)
        self.assertGreaterEqual(result.elapsed_ms, 0.0)
        self.assertIsInstance(result.elapsed_ms, float)

    def test_elapsed_ms_with_mock_clock_is_plausible(self) -> None:
        """Phase 19.0 / L-9: the "elapsed is plausible" assertion
        the prior test was reaching for. We inject a fake clock
        sequence (start=100.0, end=100.123) so the assertion is
        deterministic regardless of OS timer resolution. Uses
        ``time.monotonic`` (the actual clock used in
        ``plugins/sandbox.py``)."""
        from unittest import mock

        # safe_call's sync path calls time.monotonic twice — once
        # for start, once for end.
        clock_values = iter([100.0, 100.123])  # 123ms elapsed
        with mock.patch(
            "mythic_vibe_cli.plugins.sandbox.time.monotonic",
            side_effect=lambda: next(clock_values),
        ):
            result = safe_call(lambda: "ok")
        # 100.123 - 100.0 = 0.123s = 123ms.
        self.assertAlmostEqual(result.elapsed_ms, 123.0, places=2)

    def test_plugin_id_propagated(self) -> None:
        result = safe_call(lambda: 1, plugin_id="my_plugin")
        self.assertEqual(result.plugin_id, "my_plugin")


class SafeCallTimeoutPathTests(unittest.TestCase):
    """With timeout enforcement, slow plugins surface as timed_out
    rather than blocking the orchestrator."""

    def test_fast_call_within_timeout(self) -> None:
        result = safe_call(lambda: "ok", timeout_sec=2.0)
        self.assertTrue(result.ok)
        self.assertEqual(result.value, "ok")

    def test_slow_call_times_out(self) -> None:
        result = safe_call(time.sleep, 1.0, timeout_sec=0.1)
        self.assertTrue(result.timed_out)
        self.assertFalse(result.ok)
        self.assertIn("0.100s timeout", result.error)
        self.assertIn(TIMEOUT_ENV, result.error)

    def test_exception_in_threaded_call_isolated(self) -> None:
        def boom() -> None:
            raise RuntimeError("threaded plugin crash")

        result = safe_call(boom, timeout_sec=2.0)
        self.assertFalse(result.timed_out)
        self.assertEqual(result.error, "RuntimeError: threaded plugin crash")

    def test_env_var_drives_timeout(self) -> None:
        previous = os.environ.pop(TIMEOUT_ENV, None)
        os.environ[TIMEOUT_ENV] = "0.05"
        try:
            result = safe_call(time.sleep, 0.5)
            self.assertTrue(result.timed_out)
        finally:
            os.environ.pop(TIMEOUT_ENV, None)
            if previous is not None:
                os.environ[TIMEOUT_ENV] = previous

    def test_explicit_timeout_overrides_env(self) -> None:
        previous = os.environ.pop(TIMEOUT_ENV, None)
        os.environ[TIMEOUT_ENV] = "0.01"  # very tight
        try:
            # explicit 2.0 overrides env's tight 0.01
            result = safe_call(lambda: "ok", timeout_sec=2.0)
            self.assertTrue(result.ok)
        finally:
            os.environ.pop(TIMEOUT_ENV, None)
            if previous is not None:
                os.environ[TIMEOUT_ENV] = previous


# ---- SandboxResult ---------------------------------------------------


class SandboxResultTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        result = SandboxResult(
            value=42,
            elapsed_ms=12.5,
            plugin_id="pkg.mod:obj",
        )
        payload = result.to_dict()
        self.assertEqual(payload["plugin_id"], "pkg.mod:obj")
        self.assertEqual(payload["elapsed_ms"], 12.5)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["value"], "42")

    def test_ok_false_when_error(self) -> None:
        result = SandboxResult(error="oops")
        self.assertFalse(result.ok)

    def test_ok_false_when_timed_out(self) -> None:
        result = SandboxResult(timed_out=True, error="timeout")
        self.assertFalse(result.ok)


# ---- probe_resource_caps ---------------------------------------------


class ProbeResourceCapsTests(unittest.TestCase):
    def test_returns_resource_probe(self) -> None:
        probe = probe_resource_caps()
        self.assertIsInstance(probe, ResourceProbe)
        self.assertIsInstance(probe.platform, str)
        self.assertIsInstance(probe.notes, list)

    def test_to_dict_round_trip(self) -> None:
        probe = probe_resource_caps()
        payload = probe.to_dict()
        for key in {"advisory_only", "platform", "rlimit", "usage", "notes"}:
            self.assertIn(key, payload)

    def test_advisory_only_on_windows(self) -> None:
        if platform.system().lower() != "windows":
            self.skipTest("Windows-specific assertion")
        probe = probe_resource_caps()
        self.assertTrue(probe.advisory_only)
        self.assertEqual(probe.rlimit, {})

    def test_posix_returns_rlimit_data(self) -> None:
        if platform.system().lower() == "windows":
            self.skipTest("POSIX-specific assertion")
        probe = probe_resource_caps()
        self.assertFalse(probe.advisory_only)
        # Most POSIX hosts surface at least one of these.
        any_known = any(
            k in probe.rlimit
            for k in ("RLIMIT_NOFILE", "RLIMIT_DATA", "RLIMIT_CPU")
        )
        self.assertTrue(any_known, f"no rlimit data: {probe.rlimit}")


if __name__ == "__main__":
    unittest.main()
