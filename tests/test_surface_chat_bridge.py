"""Tests for PH-17 Slice 17.4 — chat bridge."""

from __future__ import annotations

import argparse
import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from mythic_vibe_cli.commands import (
    cmd_surface_chat,
    cmd_surface_dispatch,
    cmd_surface_ssh_doctor,
)
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.surfaces.chat_bridge import (
    COMMAND_PREFIX,
    ChatResponse,
    ParsedCommand,
    handle_message,
    parse_command,
)


class ParseCommandTests(unittest.TestCase):
    def test_blank_message_invalid(self) -> None:
        self.assertFalse(parse_command("").valid)
        self.assertFalse(parse_command("   ").valid)

    def test_no_prefix_invalid(self) -> None:
        result = parse_command("hello world")
        self.assertFalse(result.valid)
        self.assertIn("missing /cmd", result.reason)

    def test_empty_body_invalid(self) -> None:
        result = parse_command(COMMAND_PREFIX)
        self.assertFalse(result.valid)
        self.assertIn("empty command body", result.reason)

    def test_simple_command(self) -> None:
        result = parse_command(f"{COMMAND_PREFIX} status")
        self.assertTrue(result.valid)
        self.assertEqual(result.command, "status")
        self.assertEqual(result.argv, ())

    def test_with_argv(self) -> None:
        result = parse_command(f"{COMMAND_PREFIX} status --path . --json")
        self.assertEqual(result.command, "status")
        self.assertEqual(result.argv, ("--path", ".", "--json"))

    def test_quoted_argv_handled_via_shlex(self) -> None:
        result = parse_command(
            f'{COMMAND_PREFIX} oath --override "urgent fire"'
        )
        self.assertEqual(result.argv, ("--override", "urgent fire"))


class HandleMessageTests(unittest.TestCase):
    def test_chitchat_returns_none(self) -> None:
        self.assertIsNone(handle_message("hello, anyone there?"))

    def test_unknown_command(self) -> None:
        response = handle_message(f"{COMMAND_PREFIX} ghost")
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.exit_code, 2)
        self.assertIn("unknown command", response.stderr)
        self.assertIn("❌", response.rendered)

    def test_status_runs(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            response = handle_message(
                f"{COMMAND_PREFIX} status --path {tmp} --json"
            )
        self.assertIsNotNone(response)
        assert response is not None
        # exit_code may be 0 or 1 depending on whether init has run;
        # both shapes are acceptable for this smoke test.
        self.assertIn(response.exit_code, {0, 1, 2})
        self.assertIn("status", response.rendered)
        self.assertIn("```", response.rendered)

    def test_argparse_failure_renders_error_block(self) -> None:
        response = handle_message(f"{COMMAND_PREFIX} status --not-a-flag")
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.exit_code, 2)
        self.assertIn("❌", response.rendered)
        self.assertIn("argparse rejected", response.stderr)

    def test_response_truncates_long_output(self) -> None:
        # We can't easily force a >1500-char output without invoking
        # a real heavy command; instead, verify the truncation is in
        # place by passing oversized stdout via a manual ChatResponse
        # rendering. (handle_message itself caps via _render_chat_block.)
        from mythic_vibe_cli.surfaces.chat_bridge import _render_chat_block

        big = "x" * 5000
        rendered = _render_chat_block("status", 0, big, "")
        self.assertLess(len(rendered), 1700)
        self.assertIn("...", rendered)


# ---- ChatResponse / ParsedCommand dataclasses -----------------------


class DataclassTests(unittest.TestCase):
    def test_parsed_command_to_dict(self) -> None:
        parsed = ParsedCommand(valid=True, command="status", argv=("--json",))
        payload = parsed.to_dict()
        for key in {"valid", "command", "argv", "reason"}:
            self.assertIn(key, payload)

    def test_chat_response_to_dict(self) -> None:
        response = ChatResponse(
            command="status",
            exit_code=0,
            stdout="hi",
            stderr="",
            rendered="✅ status",
        )
        payload = response.to_dict()
        for key in {"command", "exit_code", "stdout", "stderr", "rendered"}:
            self.assertIn(key, payload)


# ---- cmd_surface_chat ------------------------------------------------


class CmdSurfaceChatTests(unittest.TestCase):
    def test_missing_backend_returns_error(self) -> None:
        ns = argparse.Namespace(backend="", json=False)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_surface_chat(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("matrix|telegram", stderr.getvalue())

    def test_matrix_backend_returns_scaffolding(self) -> None:
        ns = argparse.Namespace(backend="matrix", json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_surface_chat(ns)
        payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertEqual(payload["backend"], "matrix")
        self.assertTrue(payload["scaffolded"])

    def test_telegram_backend_text_mode(self) -> None:
        ns = argparse.Namespace(backend="telegram", json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_surface_chat(ns)
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("Chat bridge (telegram)", buf.getvalue())


# ---- cmd_surface_ssh_doctor ------------------------------------------


class CmdSurfaceSshDoctorTests(unittest.TestCase):
    def test_json_mode(self) -> None:
        ns = argparse.Namespace(json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            exit_code = cmd_surface_ssh_doctor(ns)
        payload = json.loads(buf.getvalue())
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("report", payload)
        self.assertGreaterEqual(len(payload["report"]["checks"]), 4)

    def test_text_mode(self) -> None:
        ns = argparse.Namespace(json=False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cmd_surface_ssh_doctor(ns)
        output = buf.getvalue()
        self.assertIn("SSH readiness check", output)


# ---- cmd_surface_dispatch --------------------------------------------


class CmdSurfaceDispatchTests(unittest.TestCase):
    def test_unknown_subcommand(self) -> None:
        ns = argparse.Namespace(surface_command="ghost")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cmd_surface_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)


# ---- argparse --------------------------------------------------------


class SurfaceArgparseTests(unittest.TestCase):
    def test_web_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(
            ["surface", "web", "--port", "8888", "--token", "x"]
        )
        self.assertEqual(ns.command, "surface")
        self.assertEqual(ns.surface_command, "web")
        self.assertEqual(ns.port, 8888)
        self.assertEqual(ns.token, "x")

    def test_ssh_doctor_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["surface", "ssh-doctor", "--json"])
        self.assertEqual(ns.surface_command, "ssh-doctor")
        self.assertTrue(ns.json)

    def test_chat_parses_with_backend(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(
            ["surface", "chat", "--backend", "matrix"]
        )
        self.assertEqual(ns.surface_command, "chat")
        self.assertEqual(ns.backend, "matrix")

    def test_chat_backend_choices_enforced(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                parser.parse_args(
                    ["surface", "chat", "--backend", "ghost"]
                )


if __name__ == "__main__":
    unittest.main()
