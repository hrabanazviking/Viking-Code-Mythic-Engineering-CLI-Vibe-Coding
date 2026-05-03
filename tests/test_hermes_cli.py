"""Hermes CLI integration tests — `mythic-vibe hermes` + `surface hermes`.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest

from mythic_vibe_cli.exit_codes import (
    OPERATIONAL_FAILURE,
    SUCCESS,
    USER_INPUT_ERROR,
)


class CmdHermesToolsTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_hermes

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_hermes(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_tools_text_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                hermes_command="tools",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("Hermes registered tools", output)
        self.assertIn("status", output)

    def test_tools_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                hermes_command="tools",
                path=tmp,
                json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertIn("tools", payload)
        self.assertGreater(len(payload["tools"]), 0)


class CmdHermesInspectTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_hermes

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_hermes(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_inspect_known_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                hermes_command="inspect",
                tool="status",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("Tool: status", output)
        self.assertIn("Input schema:", output)

    def test_inspect_unknown_tool(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                hermes_command="inspect",
                tool="nonexistent",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_inspect_missing_tool_arg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                hermes_command="inspect",
                tool="",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)


class CmdHermesInvokeTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_hermes

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_hermes(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_invoke_status_returns_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                hermes_command="invoke",
                tool="status",
                args="",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("Hermes invoke", output)
        self.assertIn("Status: ok", output)

    def test_invoke_with_json_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                hermes_command="invoke",
                tool="ai_recommend",
                args='{"task": "Build a CLI", "top": 1}',
                path=tmp,
                json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["tool"], "ai_recommend")

    def test_invoke_unknown_tool_returns_operational_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                hermes_command="invoke",
                tool="nonexistent",
                args="",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, OPERATIONAL_FAILURE)

    def test_invoke_invalid_json_args(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                hermes_command="invoke",
                tool="status",
                args="{not-valid-json",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_invoke_args_must_be_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                hermes_command="invoke",
                tool="status",
                args='[1, 2, 3]',  # JSON array, not object
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_invoke_missing_tool_arg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                hermes_command="invoke",
                tool="",
                args="",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)


class CmdHermesDispatchTests(unittest.TestCase):
    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_hermes

        captured = io.StringIO()
        sys.stdout = captured
        try:
            code = cmd_hermes(argparse.Namespace(
                hermes_command="bogus",
                path=tempfile.gettempdir(),
                json=False,
            ))
        finally:
            sys.stdout = sys.__stdout__
        self.assertEqual(code, USER_INPUT_ERROR)


class HermesCommandRegistrationTests(unittest.TestCase):
    """Hermes is in COMMAND_HANDLERS + the slash catalog +
    parser registration."""

    def test_in_command_handlers(self) -> None:
        from mythic_vibe_cli.commands import COMMAND_HANDLERS
        self.assertIn("hermes", COMMAND_HANDLERS)

    def test_in_builtin_slash_commands(self) -> None:
        from mythic_vibe_cli.runtime.slash_commands import BUILTIN_SLASH_COMMANDS
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        self.assertIn("hermes", names)

    def test_parser_accepts_hermes_subcommands(self) -> None:
        from mythic_vibe_cli.app import build_parser
        parser = build_parser()
        # Each subcommand should parse cleanly.
        ns = parser.parse_args(["hermes", "tools"])
        self.assertEqual(ns.hermes_command, "tools")
        ns = parser.parse_args(["hermes", "inspect", "--tool", "status"])
        self.assertEqual(ns.hermes_command, "inspect")
        ns = parser.parse_args(["hermes", "invoke", "--tool", "status"])
        self.assertEqual(ns.hermes_command, "invoke")

    def test_parser_accepts_surface_hermes(self) -> None:
        from mythic_vibe_cli.app import build_parser
        parser = build_parser()
        ns = parser.parse_args(["surface", "hermes"])
        self.assertEqual(ns.surface_command, "hermes")
        # Default port
        self.assertEqual(ns.port, 8770)


if __name__ == "__main__":
    unittest.main()
