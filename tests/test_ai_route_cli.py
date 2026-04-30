"""Tests for `mythic-vibe ai route` (PH-08 slice 8.4)."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.exit_codes import SUCCESS
from mythic_vibe_cli.hardware import HardwareProfile


class AiRouteArgparseTests(unittest.TestCase):
    def test_defaults(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["ai", "route"])
        self.assertEqual(ns.command, "ai")
        self.assertEqual(ns.ai_command, "route")
        self.assertEqual(ns.role, "Forge Worker")
        self.assertEqual(ns.task, "*")
        self.assertFalse(ns.explain)
        self.assertFalse(ns.no_hardware)

    def test_all_flags(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            [
                "ai",
                "route",
                "--role",
                "Skald",
                "--task",
                "intent",
                "--explain",
                "--no-hardware",
                "--json",
            ]
        )
        self.assertEqual(ns.role, "Skald")
        self.assertEqual(ns.task, "intent")
        self.assertTrue(ns.explain)
        self.assertTrue(ns.no_hardware)
        self.assertTrue(ns.json)


class CmdAiRouteTests(unittest.TestCase):
    def _ns(self, **overrides: object) -> argparse.Namespace:
        base = dict(
            path=".",
            role="Forge Worker",
            task="build",
            explain=False,
            no_hardware=False,
            json=True,
        )
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_json_envelope_default(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_route

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._ns(path=tmp, no_hardware=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ai_route(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["command"], "ai route")
        self.assertEqual(payload["role"], "Forge Worker")
        self.assertEqual(payload["task_type"], "build")
        # Without --explain, reasons are stripped to keep the envelope tight.
        self.assertNotIn("reasons", payload["decision"])
        # decision still carries provider/model/fallbacks.
        self.assertIn("provider", payload["decision"])
        self.assertIn("fallbacks", payload["decision"])

    def test_explain_includes_reasons(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_route

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._ns(path=tmp, no_hardware=True, explain=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_route(ns)
            payload = json.loads(buf.getvalue())
        self.assertIn("reasons", payload["decision"])
        self.assertTrue(payload["decision"]["reasons"])
        self.assertTrue(payload["explain"])

    def test_no_hardware_passes_no_profile(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_route

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._ns(path=tmp, no_hardware=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_route(ns)
            payload = json.loads(buf.getvalue())
        self.assertIsNone(payload["hardware"])

    def test_with_hardware_includes_profile(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_route

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._ns(path=tmp, no_hardware=False)
            with mock.patch(
                "mythic_vibe_cli.hardware.detect_profile",
                return_value=HardwareProfile(
                    detected_at="t",
                    os="Linux",
                    ram_total_mb=32_000,
                    logical_cpus=8,
                    python_version="3.11.0",
                    platform="Linux-6.0-x86_64",
                ),
            ):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    cmd_ai_route(ns)
                payload = json.loads(buf.getvalue())
        self.assertIsNotNone(payload["hardware"])
        self.assertEqual(payload["hardware"]["ram_total_mb"], 32_000)

    def test_text_output_lists_provider_and_fallbacks(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_route

        with tempfile.TemporaryDirectory() as tmp:
            ns = self._ns(path=tmp, json=False, no_hardware=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_route(ns)
            rendered = buf.getvalue()
        self.assertIn("Route:", rendered)
        self.assertIn("role='Forge Worker'", rendered)
        self.assertIn("provider=", rendered)
        self.assertIn("fallbacks", rendered)

    def test_overlay_routing_json_takes_effect(self) -> None:
        """A user-supplied mythic/ai/routing.json overlay should
        win over the default rules — slice 8.1's `RoutingTable.load`
        pre-pends overrides."""
        from mythic_vibe_cli.commands import cmd_ai_route

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overlay_dir = root / "mythic" / "ai"
            overlay_dir.mkdir(parents=True, exist_ok=True)
            (overlay_dir / "routing.json").write_text(
                json.dumps(
                    [
                        {
                            "role": "Forge Worker",
                            "task_type": "*",
                            "provider": "openrouter",
                            "model": "openai/gpt-4o",
                            "fallbacks": ["copy-paste"],
                            "description": "user override",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            ns = self._ns(path=str(root), no_hardware=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_route(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["decision"]["provider"], "openrouter")
        self.assertEqual(payload["decision"]["model"], "openai/gpt-4o")


class AiDispatchUpdateTests(unittest.TestCase):
    def test_route_routed_through_dispatch(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_dispatch, cmd_ai_route

        with mock.patch(
            "mythic_vibe_cli.commands.cmd_ai_route", wraps=cmd_ai_route
        ) as wrapped:
            with tempfile.TemporaryDirectory() as tmp:
                ns = argparse.Namespace(
                    ai_command="route",
                    path=tmp,
                    role="Skald",
                    task="*",
                    explain=False,
                    no_hardware=True,
                    json=True,
                )
                with redirect_stdout(io.StringIO()):
                    cmd_ai_dispatch(ns)
                wrapped.assert_called_once_with(ns)

    def test_unknown_subcommand_includes_route(self) -> None:
        from contextlib import redirect_stderr

        from mythic_vibe_cli.commands import cmd_ai_dispatch

        ns = argparse.Namespace(ai_command="bogus")
        buf = io.StringIO()
        with redirect_stderr(buf):
            cmd_ai_dispatch(ns)
        self.assertIn("route", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
