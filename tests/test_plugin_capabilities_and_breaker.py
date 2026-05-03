"""Phase 20.3 (audit remediation 2026-05-02) — capabilities,
circuit-breaker, and ``plugin doctor`` tests.

Three layers:

1. **Capabilities** — ``parse_capabilities`` tolerates a wide
   range of inputs; ``audit_capabilities`` flags unknown tokens
   as typos; default-deny is detected correctly.
2. **Circuit breaker** — threshold resolution (constructor →
   env → default); per-plugin failure counting trips the
   breaker; success resets; manual reset works; snapshots are
   stable; thread-safety smoke test.
3. **Sandbox + breaker integration** — ``safe_call`` reports
   results into an injected breaker; the legacy ``breaker=None``
   path is byte-identical to pre-20.3 behavior.
4. **`plugin doctor` CLI** — JSON payload contains expected
   keys; text output renders capability and warning lines;
   unknown capability surfaces as a warning.

Pure stdlib; no real plugin code is loaded.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.plugins.capabilities import (
    DEFAULT_CAPABILITIES,
    KNOWN_CAPABILITIES,
    audit_capabilities,
    parse_capabilities,
)
from mythic_vibe_cli.plugins.circuit_breaker import (
    DEFAULT_THRESHOLD,
    THRESHOLD_ENV,
    BreakerStatus,
    CircuitBreaker,
)
from mythic_vibe_cli.plugins.sandbox import safe_call


# ---------------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------------


class ParseCapabilitiesTests(unittest.TestCase):
    def test_none_yields_empty(self) -> None:
        self.assertEqual(parse_capabilities(None), ())

    def test_string_shorthand(self) -> None:
        self.assertEqual(parse_capabilities("network"), ("network",))

    def test_list_preserves_order(self) -> None:
        self.assertEqual(
            parse_capabilities(["network", "subprocess"]),
            ("network", "subprocess"),
        )

    def test_non_iterable_yields_empty(self) -> None:
        self.assertEqual(parse_capabilities(42), ())

    def test_blank_strings_dropped(self) -> None:
        self.assertEqual(
            parse_capabilities(["network", "", "  "]),
            ("network",),
        )


class AuditCapabilitiesTests(unittest.TestCase):
    def test_default_deny_when_empty(self) -> None:
        audit = audit_capabilities(())
        self.assertTrue(audit.is_default_deny)
        self.assertEqual(audit.unknown, ())

    def test_known_tokens_no_warnings(self) -> None:
        audit = audit_capabilities(("network", "subprocess"))
        self.assertFalse(audit.is_default_deny)
        self.assertEqual(audit.unknown, ())

    def test_unknown_tokens_flagged(self) -> None:
        audit = audit_capabilities(("network", "moonshine"))
        self.assertEqual(audit.unknown, ("moonshine",))

    def test_default_capabilities_constant_is_empty(self) -> None:
        # The PH-20 plan calls for default-deny; if this changes,
        # the threat-model + plugin-doctor wording must follow.
        self.assertEqual(DEFAULT_CAPABILITIES, ())

    def test_known_capabilities_vocabulary_locked(self) -> None:
        # Adding a capability should also extend the JSON
        # schema enum (plugin_manifest.schema.json). Lock the
        # vocabulary here to force a coordinated change.
        self.assertEqual(
            KNOWN_CAPABILITIES,
            ("read", "network", "subprocess", "file-write"),
        )


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitBreakerThresholdTests(unittest.TestCase):
    def test_default_threshold(self) -> None:
        breaker = CircuitBreaker(env={})
        self.assertEqual(breaker.threshold, DEFAULT_THRESHOLD)

    def test_env_override(self) -> None:
        breaker = CircuitBreaker(env={THRESHOLD_ENV: "5"})
        self.assertEqual(breaker.threshold, 5)

    def test_constructor_wins(self) -> None:
        breaker = CircuitBreaker(threshold=7, env={THRESHOLD_ENV: "5"})
        self.assertEqual(breaker.threshold, 7)

    def test_invalid_env_falls_back(self) -> None:
        breaker = CircuitBreaker(env={THRESHOLD_ENV: "notanumber"})
        self.assertEqual(breaker.threshold, DEFAULT_THRESHOLD)

    def test_zero_or_negative_env_falls_back(self) -> None:
        breaker = CircuitBreaker(env={THRESHOLD_ENV: "0"})
        self.assertEqual(breaker.threshold, DEFAULT_THRESHOLD)
        breaker = CircuitBreaker(env={THRESHOLD_ENV: "-2"})
        self.assertEqual(breaker.threshold, DEFAULT_THRESHOLD)


class CircuitBreakerStateTests(unittest.TestCase):
    def test_trips_at_threshold(self) -> None:
        breaker = CircuitBreaker(threshold=3)
        self.assertEqual(breaker.record_failure("p1"), "closed")
        self.assertEqual(breaker.record_failure("p1"), "closed")
        self.assertEqual(breaker.record_failure("p1"), "tripped")
        self.assertTrue(breaker.is_tripped("p1"))

    def test_success_resets_counter(self) -> None:
        breaker = CircuitBreaker(threshold=3)
        breaker.record_failure("p1")
        breaker.record_failure("p1")
        breaker.record_success("p1")
        self.assertFalse(breaker.is_tripped("p1"))
        # Two more failures shouldn't trip — counter reset.
        breaker.record_failure("p1")
        breaker.record_failure("p1")
        self.assertFalse(breaker.is_tripped("p1"))

    def test_per_plugin_isolation(self) -> None:
        breaker = CircuitBreaker(threshold=2)
        breaker.record_failure("p1")
        breaker.record_failure("p1")
        self.assertTrue(breaker.is_tripped("p1"))
        self.assertFalse(breaker.is_tripped("p2"))

    def test_manual_reset(self) -> None:
        breaker = CircuitBreaker(threshold=2)
        breaker.record_failure("p1")
        breaker.record_failure("p1")
        self.assertTrue(breaker.is_tripped("p1"))
        breaker.reset("p1")
        self.assertFalse(breaker.is_tripped("p1"))

    def test_snapshot_is_stable_alphabetical(self) -> None:
        breaker = CircuitBreaker(threshold=2)
        breaker.record_failure("zeta")
        breaker.record_failure("alpha")
        breaker.record_failure("alpha")
        snapshot = breaker.snapshot()
        self.assertEqual([s.plugin_id for s in snapshot], ["alpha", "zeta"])
        self.assertEqual(snapshot[0].state, "tripped")
        self.assertEqual(snapshot[1].state, "closed")

    def test_thread_safety_smoke(self) -> None:
        """Hammer the breaker from many threads — no exceptions
        means the lock is doing its job."""
        breaker = CircuitBreaker(threshold=100)

        def worker() -> None:
            for _ in range(50):
                breaker.record_failure("p1")
                breaker.record_success("p1")

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # End state should be closed (every failure followed by success).
        self.assertFalse(breaker.is_tripped("p1"))


class BreakerStatusSerializationTests(unittest.TestCase):
    def test_to_dict_contains_expected_keys(self) -> None:
        status = BreakerStatus(
            plugin_id="p1",
            state="tripped",
            consecutive_failures=5,
            threshold=3,
        )
        payload = status.to_dict()
        self.assertEqual(payload["plugin_id"], "p1")
        self.assertEqual(payload["state"], "tripped")
        # JSON-serializable.
        json.dumps(payload)


# ---------------------------------------------------------------------------
# Sandbox + breaker integration
# ---------------------------------------------------------------------------


class SafeCallBreakerIntegrationTests(unittest.TestCase):
    def test_breaker_none_path_unchanged(self) -> None:
        """Default breaker=None must produce the same
        SandboxResult as before 20.3 — backwards-compat
        guard."""
        result = safe_call(lambda: 42, plugin_id="p1")
        self.assertEqual(result.value, 42)
        self.assertTrue(result.ok)

    def test_breaker_records_success(self) -> None:
        breaker = CircuitBreaker(threshold=3)
        safe_call(lambda: 1, plugin_id="p1", breaker=breaker)
        snapshot = breaker.snapshot()
        self.assertEqual(snapshot[0].consecutive_failures, 0)
        self.assertEqual(snapshot[0].state, "closed")

    def test_breaker_records_failure_and_trips(self) -> None:
        breaker = CircuitBreaker(threshold=2)

        def crashing() -> None:
            raise RuntimeError("boom")

        safe_call(crashing, plugin_id="p1", breaker=breaker)
        safe_call(crashing, plugin_id="p1", breaker=breaker)
        self.assertTrue(breaker.is_tripped("p1"))

    def test_breaker_skipped_for_empty_plugin_id(self) -> None:
        """Without a plugin_id the breaker has nothing to key
        on; the call should succeed but no state is recorded."""
        breaker = CircuitBreaker(threshold=2)
        safe_call(lambda: 1, breaker=breaker)
        self.assertEqual(breaker.snapshot(), [])


# ---------------------------------------------------------------------------
# plugin doctor CLI
# ---------------------------------------------------------------------------


class CmdPluginDoctorIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_plugin_doctor

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_plugin_doctor(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def _ns(self, tmp: str, **overrides) -> argparse.Namespace:
        kwargs = {"path": tmp, "json": False}
        kwargs.update(overrides)
        return argparse.Namespace(**kwargs)

    def _write_registry(
        self, root: Path, plugin_records: list[dict[str, object]]
    ) -> None:
        manifest = {
            "schema_version": 2,
            "hooks_version": 1,
            "available_hooks": [],
            "plugins": [r["entrypoint"] for r in plugin_records],
            "plugin_records": plugin_records,
        }
        path = root / "mythic" / "plugins.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

    def test_no_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(self._ns(tmp))
        self.assertEqual(code, SUCCESS)
        self.assertIn("No plugins registered", output)

    def test_renders_plugin_with_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_registry(
                Path(tmp),
                [
                    {
                        "entrypoint": "mypkg.AuditPlugin",
                        "enabled": True,
                        "hooks": ["before_scan"],
                        "version": "1.0.0",
                        "added_at": "2026-01-01T00:00:00Z",
                        "capabilities": ["read", "network"],
                    }
                ],
            )
            code, output = self._run(self._ns(tmp))
        self.assertEqual(code, SUCCESS)
        self.assertIn("mypkg.AuditPlugin", output)
        self.assertIn("read, network", output)

    def test_unknown_capability_surfaces_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_registry(
                Path(tmp),
                [
                    {
                        "entrypoint": "mypkg.WeirdPlugin",
                        "enabled": True,
                        "hooks": [],
                        "version": "0.1",
                        "added_at": "2026-01-01T00:00:00Z",
                        "capabilities": ["network", "moonshine"],
                    }
                ],
            )
            code, output = self._run(self._ns(tmp))
        self.assertEqual(code, SUCCESS)
        self.assertIn("UNKNOWN: moonshine", output)
        self.assertIn("Warnings:", output)

    def test_default_deny_label_for_empty_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_registry(
                Path(tmp),
                [
                    {
                        "entrypoint": "mypkg.QuietPlugin",
                        "enabled": True,
                        "hooks": [],
                        "version": "0.1",
                        "added_at": "2026-01-01T00:00:00Z",
                        "capabilities": [],
                    }
                ],
            )
            code, output = self._run(self._ns(tmp))
        self.assertEqual(code, SUCCESS)
        self.assertIn("default-deny", output)

    def test_json_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_registry(
                Path(tmp),
                [
                    {
                        "entrypoint": "mypkg.AuditPlugin",
                        "enabled": True,
                        "hooks": [],
                        "version": "1.0.0",
                        "added_at": "2026-01-01T00:00:00Z",
                        "capabilities": ["read"],
                    }
                ],
            )
            code, output = self._run(self._ns(tmp, json=True))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        for key in (
            "command",
            "registry",
            "default_capabilities",
            "breaker_threshold",
            "warnings",
            "plugins",
        ):
            self.assertIn(key, payload)
        self.assertEqual(len(payload["plugins"]), 1)
        plugin = payload["plugins"][0]
        self.assertEqual(plugin["entrypoint"], "mypkg.AuditPlugin")
        self.assertEqual(plugin["capabilities"]["declared"], ["read"])

    def test_breaker_threshold_env_propagates_to_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._write_registry(Path(tmp), [])
            with mock.patch.dict(
                "os.environ",
                {THRESHOLD_ENV: "9"},
                clear=False,
            ):
                code, output = self._run(self._ns(tmp, json=True))
                payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["breaker_threshold"], "9")


if __name__ == "__main__":
    unittest.main()
