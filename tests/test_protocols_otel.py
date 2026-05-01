"""Tests for PH-16 Slice 16.4 — OpenTelemetry exporter."""

from __future__ import annotations

import argparse
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from mythic_vibe_cli.commands import cmd_protocols_dispatch, cmd_protocols_otel_status
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.protocols.otel import (
    INSTALL_HINT,
    OTEL_ENABLED_ENV,
    OtelStatus,
    command_span,
    is_otel_enabled,
    status,
)


class IsOtelEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(OTEL_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(OTEL_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[OTEL_ENABLED_ENV] = self._previous

    def test_default_off(self) -> None:
        self.assertFalse(is_otel_enabled())

    def test_truthy_values(self) -> None:
        for raw in ("1", "true", "yes", "on", "TRUE"):
            os.environ[OTEL_ENABLED_ENV] = raw
            self.assertTrue(is_otel_enabled(), f"failed for {raw!r}")

    def test_falsy_values(self) -> None:
        for raw in ("0", "false", "no", "off", "garbage"):
            os.environ[OTEL_ENABLED_ENV] = raw
            self.assertFalse(is_otel_enabled(), f"failed for {raw!r}")


class OtelStatusTests(unittest.TestCase):
    def test_status_default_disabled(self) -> None:
        previous = os.environ.pop(OTEL_ENABLED_ENV, None)
        try:
            snapshot = status()
        finally:
            if previous is not None:
                os.environ[OTEL_ENABLED_ENV] = previous
        self.assertFalse(snapshot.enabled_env)
        self.assertFalse(snapshot.active)
        self.assertIsInstance(snapshot.notes, list)

    def test_to_dict_round_trip(self) -> None:
        snapshot = OtelStatus(
            enabled_env=True,
            sdk_available=False,
            notes=["x"],
        )
        payload = snapshot.to_dict()
        for key in {"enabled_env", "sdk_available", "active", "notes"}:
            self.assertIn(key, payload)
        # active is a derived property — should be False here.
        self.assertFalse(payload["active"])

    def test_active_when_enabled_and_sdk_present(self) -> None:
        snapshot = OtelStatus(enabled_env=True, sdk_available=True)
        self.assertTrue(snapshot.active)

    def test_install_hint_constant(self) -> None:
        self.assertIn("opentelemetry", INSTALL_HINT)


# ---- command_span ----------------------------------------------------


class CommandSpanDisabledTests(unittest.TestCase):
    """When the env flag is off OR the SDK is missing, the
    context manager is a zero-cost no-op."""

    def setUp(self) -> None:
        self._previous = os.environ.pop(OTEL_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(OTEL_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[OTEL_ENABLED_ENV] = self._previous

    def test_no_op_when_env_disabled(self) -> None:
        with command_span("status"):
            pass  # nothing should happen

    def test_no_op_when_sdk_missing(self) -> None:
        os.environ[OTEL_ENABLED_ENV] = "1"
        with mock.patch(
            "mythic_vibe_cli.protocols.otel._try_import_otel",
            return_value=None,
        ):
            with command_span("status"):
                pass


class CommandSpanActiveTests(unittest.TestCase):
    """When env on + SDK available, command_span constructs a
    span via the trace module's tracer + start_as_current_span."""

    def setUp(self) -> None:
        self._previous = os.environ.pop(OTEL_ENABLED_ENV, None)
        os.environ[OTEL_ENABLED_ENV] = "1"

    def tearDown(self) -> None:
        os.environ.pop(OTEL_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[OTEL_ENABLED_ENV] = self._previous

    def test_span_constructed_with_attributes(self) -> None:
        # Build a fake trace module that records what gets called.
        class _FakeSpan:
            def __init__(self) -> None:
                self.exceptions: list = []
                self.statuses: list = []

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def record_exception(self, exc):
                self.exceptions.append(exc)

            def set_status(self, status):
                self.statuses.append(status)

        class _FakeTracer:
            def __init__(self) -> None:
                self.spans: list[_FakeSpan] = []
                self.last_attributes: dict | None = None
                self.last_name: str | None = None

            def start_as_current_span(self, name, *, attributes=None):
                self.last_name = name
                self.last_attributes = dict(attributes or {})
                span = _FakeSpan()
                self.spans.append(span)
                return span

        fake_tracer = _FakeTracer()

        class _FakeStatusCode:
            ERROR = "ERROR"

        class _FakeStatus:
            def __init__(self, code):
                self.code = code

        class _FakeTraceModule:
            Status = _FakeStatus
            StatusCode = _FakeStatusCode

            def get_tracer(self, name, version):
                return fake_tracer

        with mock.patch(
            "mythic_vibe_cli.protocols.otel._try_import_otel",
            return_value=_FakeTraceModule(),
        ):
            with command_span("status", attributes={"path": "/tmp"}):
                pass

        self.assertEqual(fake_tracer.last_name, "mythic_vibe.status")
        self.assertEqual(
            fake_tracer.last_attributes["mythic.command"], "status"
        )
        self.assertEqual(fake_tracer.last_attributes["path"], "/tmp")

    def test_exception_recorded_then_reraised(self) -> None:
        class _FakeSpan:
            def __init__(self) -> None:
                self.exceptions: list = []
                self.statuses: list = []

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def record_exception(self, exc):
                self.exceptions.append(exc)

            def set_status(self, status):
                self.statuses.append(status)

        the_span = _FakeSpan()

        class _FakeTracer:
            def start_as_current_span(self, name, *, attributes=None):
                return the_span

        class _FakeStatusCode:
            ERROR = "ERROR"

        class _FakeStatus:
            def __init__(self, code):
                self.code = code

        class _FakeTraceModule:
            Status = _FakeStatus
            StatusCode = _FakeStatusCode

            def get_tracer(self, name, version):
                return _FakeTracer()

        with mock.patch(
            "mythic_vibe_cli.protocols.otel._try_import_otel",
            return_value=_FakeTraceModule(),
        ):
            with self.assertRaises(RuntimeError):
                with command_span("status"):
                    raise RuntimeError("boom")

        self.assertEqual(len(the_span.exceptions), 1)
        self.assertIsInstance(the_span.exceptions[0], RuntimeError)
        # status.set_status was called with ERROR code.
        self.assertEqual(len(the_span.statuses), 1)


# ---- cmd_protocols_otel_status ---------------------------------------


class CmdProtocolsOtelStatusTests(unittest.TestCase):
    def test_json_mode(self) -> None:
        ns = argparse.Namespace(json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_protocols_otel_status(ns)
        payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("status", payload)
        self.assertIn("active", payload["status"])

    def test_text_mode(self) -> None:
        ns = argparse.Namespace(json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_protocols_otel_status(ns)
        output = buf.getvalue()
        self.assertIn("OpenTelemetry status", output)


class CmdProtocolsDispatchTests(unittest.TestCase):
    def test_unknown_subcommand(self) -> None:
        from contextlib import redirect_stderr

        ns = argparse.Namespace(protocols_command="ghost")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_protocols_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("Unknown protocols subcommand", stderr.getvalue())


class ProtocolsArgparseTests(unittest.TestCase):
    def test_otel_status_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["protocols", "otel-status", "--json"])
        self.assertEqual(ns.command, "protocols")
        self.assertEqual(ns.protocols_command, "otel-status")
        self.assertTrue(ns.json)

    def test_mcp_server_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["protocols", "mcp-server"])
        self.assertEqual(ns.protocols_command, "mcp-server")

    def test_acp_bridge_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["protocols", "acp-bridge"])
        self.assertEqual(ns.protocols_command, "acp-bridge")


if __name__ == "__main__":
    unittest.main()
