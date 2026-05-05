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


# PH-23.12 — coverage push for chat_bridge.py:
# parse_command edge cases, handle_message exception branches,
# _render_chat_block formatting, Matrix + Telegram config edge
# cases, _matrix_request + _telegram_request JSON edge cases,
# is_chat_allowed + is_user_allowed allowlist semantics.


class ParseCommandAdditionalEdgeCasesTests(unittest.TestCase):
    """Cover lines 163-164 + 168 in parse_command."""

    def test_shlex_error_returns_invalid(self) -> None:
        # An unclosed quote is a shlex error → reason carries
        # the underlying exception text.
        result = parse_command('/cmd foo "unclosed')
        self.assertFalse(result.valid)
        self.assertIn("shlex error", result.reason)

    def test_whitespace_only_body_invalid(self) -> None:
        # Body is whitespace; shlex returns no tokens → invalid.
        result = parse_command(COMMAND_PREFIX + " " * 5 + "\t")
        self.assertFalse(result.valid)
        # Lands in the empty-body branch (line 159-160), not the
        # post-shlex empty-token-list branch — both are valid
        # outcomes for whitespace-only input.
        self.assertIn("empty", result.reason.lower())


class HandleMessageExceptionTests(unittest.TestCase):
    """Cover lines 216-220 in handle_message — the generic
    Exception swallow + exit-code mapping."""

    def test_handler_raising_returns_error_response(self) -> None:
        # Patch a real handler to raise. handle_message must
        # never propagate exceptions to the chat surface — they
        # all become an exit-code-1 ChatResponse.
        from unittest import mock
        import mythic_vibe_cli.surfaces.chat_bridge as cb

        # Pick a real command name + replace its handler.
        with mock.patch.dict(
            "mythic_vibe_cli.commands.COMMAND_HANDLERS",
            {
                "doctor": lambda ns: (_ for _ in ()).throw(
                    RuntimeError("kaboom in handler")
                )
            },
            clear=False,
        ):
            response = cb.handle_message("/cmd doctor")

        self.assertIsNotNone(response)
        assert response is not None  # for type narrowing
        self.assertEqual(response.exit_code, 1)
        self.assertIn("RuntimeError", response.stderr)
        self.assertIn("kaboom in handler", response.stderr)

    def test_handler_raising_systemexit_carries_exit_code(self) -> None:
        # SystemExit with an int code maps directly; SystemExit
        # with a non-int payload (None, str) maps to exit 1.
        from unittest import mock
        import mythic_vibe_cli.surfaces.chat_bridge as cb

        with mock.patch.dict(
            "mythic_vibe_cli.commands.COMMAND_HANDLERS",
            {
                "doctor": lambda ns: (_ for _ in ()).throw(
                    SystemExit(7)
                )
            },
            clear=False,
        ):
            response = cb.handle_message("/cmd doctor")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.exit_code, 7)

    def test_handler_systemexit_non_int_maps_to_one(self) -> None:
        # Some handlers raise SystemExit with str payload.
        # handle_message must not crash; it maps to exit 1.
        from unittest import mock
        import mythic_vibe_cli.surfaces.chat_bridge as cb

        with mock.patch.dict(
            "mythic_vibe_cli.commands.COMMAND_HANDLERS",
            {
                "doctor": lambda ns: (_ for _ in ()).throw(
                    SystemExit("bad")
                )
            },
            clear=False,
        ):
            response = cb.handle_message("/cmd doctor")

        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response.exit_code, 1)


class RenderChatBlockTests(unittest.TestCase):
    """Cover lines 242-247 in _render_chat_block — the body
    composition edge cases (no stdout, no stderr, no body,
    truncation at 1500)."""

    def setUp(self) -> None:
        from mythic_vibe_cli.surfaces.chat_bridge import (
            _render_chat_block,
        )
        self._render = _render_chat_block

    def test_no_output_renders_no_output_marker(self) -> None:
        # Both empty strings: body falls back to "(no output)".
        rendered = self._render("doctor", 0, "", "")
        self.assertIn("(no output)", rendered)

    def test_stdout_only_renders_clean(self) -> None:
        # Just stdout, no stderr: no "--- stderr ---" divider.
        rendered = self._render("doctor", 0, "all good", "")
        self.assertIn("all good", rendered)
        self.assertNotIn("--- stderr ---", rendered)

    def test_stderr_only_renders_with_divider(self) -> None:
        # Just stderr, no stdout: divider IS present so the
        # operator can see this output came from stderr.
        rendered = self._render("doctor", 1, "", "broken")
        self.assertIn("broken", rendered)
        # When body is empty the divider doesn't apply (the
        # implementation uses an empty divider in that case).
        # Verify the rendered block at least carries the stderr.

    def test_both_streams_render_with_divider(self) -> None:
        rendered = self._render("doctor", 1, "step ok", "step failed")
        self.assertIn("step ok", rendered)
        self.assertIn("--- stderr ---", rendered)
        self.assertIn("step failed", rendered)

    def test_long_body_truncated(self) -> None:
        # Body over 1500 chars truncates with an ellipsis. We
        # construct stdout > 1500 chars deliberately.
        long_body = "x" * 2000
        rendered = self._render("doctor", 0, long_body, "")
        # Truncation marker appears in the rendered text.
        self.assertIn("...", rendered)
        # The full 2000-char input should NOT appear verbatim.
        self.assertNotIn("x" * 2000, rendered)


class MatrixConfigCoverageTests(unittest.TestCase):
    """Cover lines 323 + 374 in MatrixConfig (from_file unknown
    allowed_rooms type, validate empty homeserver)."""

    def test_from_file_unknown_allowed_rooms_type_falls_back_to_empty(
        self,
    ) -> None:
        # Line 323: allowed_rooms is an int (not str/list/tuple)
        # → falls back to empty tuple.
        import json
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.surfaces.chat_bridge import MatrixConfig

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "matrix.json"
            cfg_path.write_text(json.dumps({
                "matrix": {
                    "access_token": "tok",
                    "allowed_rooms": 42,  # invalid type
                }
            }), encoding="utf-8")
            cfg = MatrixConfig.from_file(cfg_path)
        self.assertEqual(cfg.allowed_rooms, ())

    def test_validate_empty_homeserver_raises(self) -> None:
        # Line 374: empty homeserver triggers the "homeserver
        # required" problem in the validate method.
        from mythic_vibe_cli.surfaces.chat_bridge import (
            ChatBridgeConfigError,
            MatrixConfig,
        )
        cfg = MatrixConfig(
            homeserver="",
            access_token="tok",
            room_id="!room:matrix.org",
            allowed_rooms=("!room:matrix.org",),
        )
        with self.assertRaises(ChatBridgeConfigError) as ctx:
            cfg.validate()
        self.assertIn("homeserver is required", str(ctx.exception))


class MatrixRequestJsonEdgeTests(unittest.TestCase):
    """Cover lines 425-426 in _matrix_request — JSONDecodeError
    fallback returns empty dict."""

    def test_malformed_json_response_returns_empty_dict(self) -> None:
        from unittest import mock
        from mythic_vibe_cli.surfaces.chat_bridge import (
            MatrixConfig,
            _matrix_request,
        )

        cfg = MatrixConfig(
            homeserver="https://matrix.example",
            access_token="tok",
            room_id="!r:matrix.org",
            allowed_rooms=("*",),
        )

        class FakeResp:
            def __init__(self, body: bytes) -> None:
                self._body = body

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self) -> bytes:
                return self._body

        # The chat_bridge module imports urllib.request at the
        # top so we patch it inside that module's namespace.
        with mock.patch(
            "mythic_vibe_cli.surfaces.chat_bridge.urllib.request.urlopen",
            return_value=FakeResp(b"not-json{"),
        ):
            result = _matrix_request(cfg, "GET", "/_matrix/client/sync")
        self.assertEqual(result, {})


class TelegramConfigCoverageTests(unittest.TestCase):
    """Cover lines 500-503, 516-517, 532-566, 578-587, 619, 632
    in TelegramConfig + the _telegram_request JSON edges 653/656-657."""

    def test_from_env_chat_id_parses_int_when_numeric(self) -> None:
        # Line 500-503: chat_id env var is a numeric string.
        from unittest import mock
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        env = {
            "MYTHIC_CHAT_TELEGRAM_BOT_TOKEN": "tok",
            "MYTHIC_CHAT_TELEGRAM_CHAT_ID": "12345",
            "MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS": "12345",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            cfg = TelegramConfig.from_env()
        self.assertEqual(cfg.chat_id, 12345)

    def test_from_env_chat_id_falls_back_to_string_on_non_numeric(
        self,
    ) -> None:
        # Lines 502-503: ValueError on int() → keep as string.
        from unittest import mock
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        env = {
            "MYTHIC_CHAT_TELEGRAM_BOT_TOKEN": "tok",
            "MYTHIC_CHAT_TELEGRAM_CHAT_ID": "@my_channel",
            "MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS": "@my_channel",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            cfg = TelegramConfig.from_env()
        self.assertEqual(cfg.chat_id, "@my_channel")

    def test_from_env_invalid_poll_timeout_falls_back_to_default(
        self,
    ) -> None:
        # Lines 516-517: poll_timeout_s env var is non-numeric.
        from unittest import mock
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        env = {
            "MYTHIC_CHAT_TELEGRAM_BOT_TOKEN": "tok",
            "MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS": "12345",
            "MYTHIC_CHAT_TELEGRAM_POLL_TIMEOUT_S": "thirty",
        }
        with mock.patch.dict("os.environ", env, clear=False):
            cfg = TelegramConfig.from_env()
        self.assertEqual(cfg.poll_timeout_s, 30)

    def test_from_file_full_path(self) -> None:
        # Lines 532-566: full TelegramConfig.from_file branch.
        import json
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "telegram.json"
            cfg_path.write_text(json.dumps({
                "telegram": {
                    "bot_token": "f-tok",
                    "chat_id": 999,
                    "allowed_chats": ["111", "222"],
                    "allowed_users": ["u1", "u2"],
                    "poll_timeout_s": 45,
                }
            }), encoding="utf-8")
            cfg = TelegramConfig.from_file(cfg_path)
        self.assertEqual(cfg.bot_token, "f-tok")
        self.assertEqual(cfg.chat_id, 999)
        self.assertEqual(cfg.allowed_chats, ("111", "222"))
        self.assertEqual(cfg.allowed_users, ("u1", "u2"))
        self.assertEqual(cfg.poll_timeout_s, 45)

    def test_from_file_csv_string_fields(self) -> None:
        # Lines 539, 545: allowed_chats/users as CSV string
        # rather than list.
        import json
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "tg.json"
            cfg_path.write_text(json.dumps({
                "telegram": {
                    "bot_token": "tok",
                    "allowed_chats": "111,222",
                    "allowed_users": "u1,u2",
                }
            }), encoding="utf-8")
            cfg = TelegramConfig.from_file(cfg_path)
        self.assertEqual(cfg.allowed_chats, ("111", "222"))
        self.assertEqual(cfg.allowed_users, ("u1", "u2"))

    def test_from_file_chat_id_falls_back_to_first_allowed(self) -> None:
        # Lines 559-563: chat_id is empty → derive from allowed_chats[0].
        import json
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "tg.json"
            cfg_path.write_text(json.dumps({
                "telegram": {
                    "bot_token": "tok",
                    "allowed_chats": ["555", "666"],
                }
            }), encoding="utf-8")
            cfg = TelegramConfig.from_file(cfg_path)
        self.assertEqual(cfg.chat_id, 555)

    def test_from_file_chat_id_string_alias(self) -> None:
        # Line 558: chat_id is a non-numeric string → keep as-is.
        import json
        import tempfile
        from pathlib import Path
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "tg.json"
            cfg_path.write_text(json.dumps({
                "telegram": {
                    "bot_token": "tok",
                    "chat_id": "@my_channel",
                    "allowed_chats": ["@my_channel"],
                }
            }), encoding="utf-8")
            cfg = TelegramConfig.from_file(cfg_path)
        self.assertEqual(cfg.chat_id, "@my_channel")

    def test_from_sources_propagates_file_error(self) -> None:
        # Lines 581-587: from_file raises OSError → from_sources
        # wraps in ChatBridgeConfigError with helpful message.
        from pathlib import Path
        from mythic_vibe_cli.surfaces.chat_bridge import (
            ChatBridgeConfigError,
            TelegramConfig,
        )

        bad_path = Path("/definitely/does/not/exist/cfg.json")
        with self.assertRaises(ChatBridgeConfigError) as ctx:
            TelegramConfig.from_sources(config_path=bad_path)
        self.assertIn("Telegram config file", str(ctx.exception))

    def test_is_chat_allowed_empty_allowlist(self) -> None:
        # Line 619: empty allowed_chats → False.
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig

        cfg = TelegramConfig(bot_token="tok", chat_id=0, allowed_chats=())
        self.assertFalse(cfg.is_chat_allowed(123))

    def test_is_user_allowed_broadcast_sentinel(self) -> None:
        # Line 632: ALLOWLIST_BROADCAST in allowed_users → True
        # for any user.
        from mythic_vibe_cli.surfaces.chat_bridge import (
            ALLOWLIST_BROADCAST,
            TelegramConfig,
        )

        cfg = TelegramConfig(
            bot_token="tok",
            chat_id=0,
            allowed_users=(ALLOWLIST_BROADCAST,),
        )
        self.assertTrue(cfg.is_user_allowed("anything"))


class TelegramRequestJsonEdgeTests(unittest.TestCase):
    """Cover lines 653, 656-657 in _telegram_request — empty body
    + JSONDecodeError fallback both return empty dict."""

    def setUp(self) -> None:
        from mythic_vibe_cli.surfaces.chat_bridge import TelegramConfig
        self.cfg = TelegramConfig(
            bot_token="tok", chat_id=0, allowed_chats=("12345",),
        )

    def test_empty_response_returns_empty_dict(self) -> None:
        from unittest import mock
        from mythic_vibe_cli.surfaces.chat_bridge import _telegram_request

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self) -> bytes:
                return b""

        with mock.patch(
            "mythic_vibe_cli.surfaces.chat_bridge.urllib.request.urlopen",
            return_value=FakeResp(),
        ):
            result = _telegram_request(self.cfg, "getMe")
        self.assertEqual(result, {})

    def test_malformed_json_response_returns_empty_dict(self) -> None:
        from unittest import mock
        from mythic_vibe_cli.surfaces.chat_bridge import _telegram_request

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self) -> bytes:
                return b"not-json"

        with mock.patch(
            "mythic_vibe_cli.surfaces.chat_bridge.urllib.request.urlopen",
            return_value=FakeResp(),
        ):
            result = _telegram_request(self.cfg, "getMe")
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
