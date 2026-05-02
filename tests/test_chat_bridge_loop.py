"""Phase E.1 + E.2 + E.3 (audit remediation 2026-05-02, finding #2)
— chat-bridge long-poll loop tests + cmd_surface_chat --run wire-up.

Both loops are exercised through their injection points (``transport``,
``sender``, ``handler``, ``clock_sleep``, ``backoff``) so tests run
deterministically without HTTP. The wire-up tests cover the master env
gate, allowlist refusal at validate(), and the happy --run path.
"""

from __future__ import annotations

import argparse
import io
import json
import threading
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from mythic_vibe_cli.surfaces.chat_bridge import (
    CHAT_BRIDGE_ENABLED_ENV,
    ChatResponse,
    MatrixConfig,
    TelegramConfig,
)
from mythic_vibe_cli.surfaces.chat_bridge_loop import (
    _Backoff,
    _is_transient_http_error,
    _matrix_extract_messages,
    _telegram_extract_messages,
    run_matrix_loop,
    run_telegram_loop,
)


# --------------------------------------------------------------------------- #
# Helpers + small-utility tests
# --------------------------------------------------------------------------- #


class BackoffTests(unittest.TestCase):
    def test_first_delay_is_base(self) -> None:
        bo = _Backoff(base=1.0, factor=2.0, cap=60.0)
        self.assertEqual(bo.next_delay(), 1.0)

    def test_each_delay_multiplies_by_factor_until_cap(self) -> None:
        bo = _Backoff(base=1.0, factor=2.0, cap=5.0)
        delays = [bo.next_delay() for _ in range(6)]
        self.assertEqual(delays, [1.0, 2.0, 4.0, 5.0, 5.0, 5.0])

    def test_reset_returns_to_base(self) -> None:
        bo = _Backoff(base=1.0, factor=2.0, cap=60.0)
        bo.next_delay()
        bo.next_delay()
        bo.next_delay()
        bo.reset()
        self.assertEqual(bo.next_delay(), 1.0)


class TransientHttpErrorTests(unittest.TestCase):
    def test_5xx_is_transient(self) -> None:
        for code in (500, 502, 503, 504):
            self.assertTrue(
                _is_transient_http_error(
                    urllib.error.HTTPError("u", code, "", {}, None)
                )
            )

    def test_4xx_is_terminal_except_408_429(self) -> None:
        # 408/429 are retryable per HTTP spec
        for code in (408, 429):
            self.assertTrue(
                _is_transient_http_error(
                    urllib.error.HTTPError("u", code, "", {}, None)
                )
            )
        # 401 / 403 / 404 / 400 are terminal
        for code in (400, 401, 403, 404):
            self.assertFalse(
                _is_transient_http_error(
                    urllib.error.HTTPError("u", code, "", {}, None)
                )
            )

    def test_url_error_is_transient(self) -> None:
        self.assertTrue(_is_transient_http_error(urllib.error.URLError("net")))


# --------------------------------------------------------------------------- #
# Matrix message extraction
# --------------------------------------------------------------------------- #


class MatrixExtractMessagesTests(unittest.TestCase):
    def _payload(self, events: list[dict]) -> dict:
        return {
            "rooms": {
                "join": {
                    "!room:s": {"timeline": {"events": events}}
                }
            }
        }

    def test_extracts_text_messages(self) -> None:
        events = [
            {
                "type": "m.room.message",
                "sender": "@user:s",
                "event_id": "$1",
                "content": {"msgtype": "m.text", "body": "hi"},
            }
        ]
        out = _matrix_extract_messages(self._payload(events))
        self.assertEqual(out, [("!room:s", "@user:s", "$1", "hi")])

    def test_skips_non_text_events(self) -> None:
        events = [
            {
                "type": "m.room.message",
                "content": {"msgtype": "m.image", "body": "ignored"},
            },
            {
                "type": "m.reaction",
                "content": {"body": "ignored"},
            },
        ]
        self.assertEqual(_matrix_extract_messages(self._payload(events)), [])

    def test_skips_empty_body(self) -> None:
        events = [
            {
                "type": "m.room.message",
                "sender": "@u:s",
                "content": {"msgtype": "m.text", "body": ""},
            }
        ]
        self.assertEqual(_matrix_extract_messages(self._payload(events)), [])

    def test_handles_missing_structure_gracefully(self) -> None:
        for payload in (
            {},
            {"rooms": None},
            {"rooms": {"join": None}},
            {"rooms": {"join": {"!r:s": None}}},
            {"rooms": {"join": {"!r:s": {"timeline": None}}}},
            {"rooms": {"join": {"!r:s": {"timeline": {"events": None}}}}},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(_matrix_extract_messages(payload), [])


# --------------------------------------------------------------------------- #
# Telegram message extraction
# --------------------------------------------------------------------------- #


class TelegramExtractMessagesTests(unittest.TestCase):
    def test_extracts_text_messages(self) -> None:
        payload = {
            "ok": True,
            "result": [
                {
                    "update_id": 42,
                    "message": {
                        "chat": {"id": 1234},
                        "from": {"id": 999},
                        "text": "/cmd status",
                    },
                }
            ],
        }
        out = _telegram_extract_messages(payload)
        self.assertEqual(out, [(42, 1234, 999, "/cmd status")])

    def test_skips_non_message_updates(self) -> None:
        payload = {
            "result": [
                {"update_id": 1, "callback_query": {"data": "cbq"}},
                {"update_id": 2, "edited_message": {"text": "edit"}},
            ]
        }
        self.assertEqual(_telegram_extract_messages(payload), [])

    def test_skips_empty_text(self) -> None:
        payload = {
            "result": [
                {"update_id": 1, "message": {"chat": {"id": 1}, "text": ""}}
            ]
        }
        self.assertEqual(_telegram_extract_messages(payload), [])


# --------------------------------------------------------------------------- #
# run_matrix_loop
# --------------------------------------------------------------------------- #


class RunMatrixLoopTests(unittest.TestCase):
    def _config(
        self,
        *,
        allowed_rooms: tuple[str, ...] = ("!room:s",),
        user_id: str = "@bot:s",
    ) -> MatrixConfig:
        return MatrixConfig(
            homeserver="https://h.s",
            access_token="tok",
            room_id="",
            allowed_rooms=allowed_rooms,
            user_id=user_id,
        )

    def _sync_payload(self, events: list[dict]) -> dict:
        return {
            "next_batch": "tok-1",
            "rooms": {
                "join": {"!room:s": {"timeline": {"events": events}}}
            },
        }

    def test_dispatches_allowed_message_to_origin_room(self) -> None:
        cfg = self._config()
        sent: list[tuple[str, str]] = []

        def fake_transport(_cfg, method, path, **kw):
            return self._sync_payload(
                [
                    {
                        "type": "m.room.message",
                        "sender": "@user:s",
                        "event_id": "$1",
                        "content": {"msgtype": "m.text", "body": "/cmd status"},
                    }
                ]
            )

        def fake_sender(_cfg, text, *, txn_id=None, room_id=None):
            sent.append((room_id or "", text))
            return {"event_id": "$reply"}

        def fake_handler(text):
            return ChatResponse(
                command="status", exit_code=0, stdout="ok", stderr="", rendered="OK"
            )

        dispatched = run_matrix_loop(
            cfg,
            transport=fake_transport,
            sender=fake_sender,
            handler=fake_handler,
            clock_sleep=lambda _s: None,
            max_iterations=1,
        )
        self.assertEqual(dispatched, 1)
        self.assertEqual(sent, [("!room:s", "OK")])

    def test_skips_non_allowlisted_rooms(self) -> None:
        cfg = self._config(allowed_rooms=("!only-this:s",))
        sent: list = []

        def fake_transport(_cfg, method, path, **kw):
            return {
                "next_batch": "x",
                "rooms": {
                    "join": {
                        "!other:s": {
                            "timeline": {
                                "events": [
                                    {
                                        "type": "m.room.message",
                                        "sender": "@u:s",
                                        "event_id": "$1",
                                        "content": {
                                            "msgtype": "m.text",
                                            "body": "/cmd status",
                                        },
                                    }
                                ]
                            }
                        }
                    }
                },
            }

        run_matrix_loop(
            cfg,
            transport=fake_transport,
            sender=lambda *a, **kw: sent.append(a) or {},
            handler=lambda _t: ChatResponse(
                "status", 0, "", "", "OK"
            ),
            clock_sleep=lambda _s: None,
            max_iterations=1,
        )
        self.assertEqual(sent, [])

    def test_echo_prevention_skips_own_messages(self) -> None:
        cfg = self._config(user_id="@bot:s")
        sent: list = []

        def fake_transport(_cfg, method, path, **kw):
            return self._sync_payload(
                [
                    {
                        "type": "m.room.message",
                        "sender": "@bot:s",  # the bot itself
                        "event_id": "$echo",
                        "content": {"msgtype": "m.text", "body": "/cmd status"},
                    }
                ]
            )

        run_matrix_loop(
            cfg,
            transport=fake_transport,
            sender=lambda *a, **kw: sent.append(a) or {},
            handler=lambda _t: ChatResponse("status", 0, "", "", "OK"),
            clock_sleep=lambda _s: None,
            max_iterations=1,
        )
        self.assertEqual(sent, [])

    def test_silent_on_chitchat_messages(self) -> None:
        cfg = self._config()
        sent: list = []

        def fake_transport(_cfg, method, path, **kw):
            return self._sync_payload(
                [
                    {
                        "type": "m.room.message",
                        "sender": "@user:s",
                        "event_id": "$noise",
                        "content": {"msgtype": "m.text", "body": "hello world"},
                    }
                ]
            )

        # The default handle_message returns None for non-/cmd text.
        run_matrix_loop(
            cfg,
            transport=fake_transport,
            sender=lambda *a, **kw: sent.append(a) or {},
            clock_sleep=lambda _s: None,
            max_iterations=1,
        )
        self.assertEqual(sent, [])

    def test_stop_event_breaks_loop_immediately(self) -> None:
        cfg = self._config()
        stop = threading.Event()
        stop.set()

        def fake_transport(*args, **kwargs):
            self.fail("transport should not be called when stop set")

        # Should return 0 dispatches without invoking transport.
        result = run_matrix_loop(
            cfg,
            stop_event=stop,
            transport=fake_transport,
            clock_sleep=lambda _s: None,
        )
        self.assertEqual(result, 0)

    def test_validate_refuses_to_start_without_allowlist(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h", access_token="t", room_id="", allowed_rooms=()
        )
        from mythic_vibe_cli.surfaces.chat_bridge import ChatBridgeConfigError

        with self.assertRaises(ChatBridgeConfigError):
            run_matrix_loop(cfg, max_iterations=1, clock_sleep=lambda _s: None)

    def test_transient_error_triggers_backoff_then_recovers(self) -> None:
        cfg = self._config()
        call_count = {"n": 0}
        sleeps: list[float] = []

        def flaky_transport(_cfg, method, path, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise urllib.error.HTTPError("u", 503, "Service Unavailable", {}, None)
            return self._sync_payload([])

        run_matrix_loop(
            cfg,
            transport=flaky_transport,
            sender=lambda *a, **kw: {},
            clock_sleep=sleeps.append,
            backoff=_Backoff(base=0.1, factor=2.0, cap=1.0),
            max_iterations=2,
        )
        # First iteration should have triggered exactly one backoff sleep.
        self.assertEqual(len(sleeps), 1)
        self.assertAlmostEqual(sleeps[0], 0.1, places=5)
        # And the loop must have made a second sync call (the recovery).
        self.assertGreaterEqual(call_count["n"], 2)

    def test_terminal_4xx_raises_through(self) -> None:
        cfg = self._config()

        def auth_failing_transport(*args, **kwargs):
            raise urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)

        with self.assertRaises(urllib.error.HTTPError):
            run_matrix_loop(
                cfg,
                transport=auth_failing_transport,
                clock_sleep=lambda _s: None,
                max_iterations=2,
            )


# --------------------------------------------------------------------------- #
# run_telegram_loop
# --------------------------------------------------------------------------- #


class RunTelegramLoopTests(unittest.TestCase):
    def _config(
        self,
        *,
        allowed_chats: tuple[str, ...] = ("1234",),
        allowed_users: tuple[str, ...] = (),
    ) -> TelegramConfig:
        return TelegramConfig(
            bot_token="t",
            chat_id=1234,
            allowed_chats=allowed_chats,
            allowed_users=allowed_users,
            poll_timeout_s=1,
        )

    def _updates_payload(self, msgs: list[dict]) -> dict:
        return {"ok": True, "result": msgs}

    def test_dispatches_allowed_message(self) -> None:
        cfg = self._config()
        sent: list[tuple[int | str, str]] = []
        captured_offsets: list[int | None] = []

        def fake_transport(_cfg, offset):
            captured_offsets.append(offset)
            if len(captured_offsets) == 1:
                return self._updates_payload(
                    [
                        {
                            "update_id": 100,
                            "message": {
                                "chat": {"id": 1234},
                                "from": {"id": 99},
                                "text": "/cmd status",
                            },
                        }
                    ]
                )
            return self._updates_payload([])

        def fake_sender(_cfg, text, *, chat_id=None):
            sent.append((chat_id, text))
            return {"ok": True, "result": {"message_id": 1}}

        run_telegram_loop(
            cfg,
            transport=fake_transport,
            sender=fake_sender,
            handler=lambda _t: ChatResponse(
                "status", 0, "ok", "", "OK"
            ),
            clock_sleep=lambda _s: None,
            max_iterations=2,
        )
        self.assertEqual(sent, [(1234, "OK")])
        # The second iteration must have advanced the offset.
        self.assertEqual(captured_offsets[0], None)
        self.assertEqual(captured_offsets[1], 101)

    def test_skips_non_allowlisted_chats(self) -> None:
        cfg = self._config(allowed_chats=("999",))
        sent: list = []

        def fake_transport(_cfg, offset):
            return self._updates_payload(
                [
                    {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": 1234},
                            "from": {"id": 99},
                            "text": "/cmd status",
                        },
                    }
                ]
            )

        run_telegram_loop(
            cfg,
            transport=fake_transport,
            sender=lambda *a, **kw: sent.append(a) or {},
            handler=lambda _t: ChatResponse("status", 0, "", "", "OK"),
            clock_sleep=lambda _s: None,
            max_iterations=1,
        )
        self.assertEqual(sent, [])

    def test_skips_non_allowlisted_users_when_user_filter_set(self) -> None:
        cfg = self._config(allowed_chats=("1234",), allowed_users=("42",))
        sent: list = []

        def fake_transport(_cfg, offset):
            return self._updates_payload(
                [
                    {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": 1234},
                            "from": {"id": 999},  # not in allowed_users
                            "text": "/cmd status",
                        },
                    }
                ]
            )

        run_telegram_loop(
            cfg,
            transport=fake_transport,
            sender=lambda *a, **kw: sent.append(a) or {},
            handler=lambda _t: ChatResponse("status", 0, "", "", "OK"),
            clock_sleep=lambda _s: None,
            max_iterations=1,
        )
        self.assertEqual(sent, [])

    def test_empty_user_allowlist_accepts_any_user(self) -> None:
        cfg = self._config(allowed_chats=("1234",), allowed_users=())
        sent: list = []

        def fake_transport(_cfg, offset):
            return self._updates_payload(
                [
                    {
                        "update_id": 7,
                        "message": {
                            "chat": {"id": 1234},
                            "from": {"id": 12345},  # any user
                            "text": "/cmd status",
                        },
                    }
                ]
            )

        run_telegram_loop(
            cfg,
            transport=fake_transport,
            sender=lambda *a, **kw: (sent.append(kw) or {"ok": True}),
            handler=lambda _t: ChatResponse("status", 0, "", "", "OK"),
            clock_sleep=lambda _s: None,
            max_iterations=1,
        )
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["chat_id"], 1234)

    def test_validate_refuses_to_start_without_allowlist(self) -> None:
        cfg = TelegramConfig(bot_token="t", chat_id=1, allowed_chats=())
        from mythic_vibe_cli.surfaces.chat_bridge import ChatBridgeConfigError

        with self.assertRaises(ChatBridgeConfigError):
            run_telegram_loop(cfg, max_iterations=1, clock_sleep=lambda _s: None)

    def test_ok_false_triggers_backoff_continue(self) -> None:
        cfg = self._config()
        sleeps: list[float] = []

        def fake_transport(_cfg, offset):
            return {"ok": False, "description": "bad"}

        run_telegram_loop(
            cfg,
            transport=fake_transport,
            sender=lambda *a, **kw: {},
            handler=lambda _t: None,
            clock_sleep=sleeps.append,
            backoff=_Backoff(base=0.05, factor=2.0, cap=1.0),
            max_iterations=2,
        )
        self.assertGreaterEqual(len(sleeps), 1)


# --------------------------------------------------------------------------- #
# cmd_surface_chat --run wire-up
# --------------------------------------------------------------------------- #


class CmdSurfaceChatRunTests(unittest.TestCase):
    """End-to-end wire-up of --run: master gate, config validation,
    invoking the loop. Each test patches just the right level so we
    exercise commands.py without touching real HTTP."""

    def _ns(self, **overrides) -> argparse.Namespace:
        defaults = dict(
            backend="matrix",
            run=True,
            config="",
            max_iterations=1,
            json=False,
            path=".",
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)

    def test_master_gate_off_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_surface_chat
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        ns = self._ns()
        err = io.StringIO()
        with patch.dict(
            "os.environ",
            {CHAT_BRIDGE_ENABLED_ENV: ""},
            clear=False,
        ), redirect_stderr(err):
            code = cmd_surface_chat(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("disabled", err.getvalue())
        self.assertIn(CHAT_BRIDGE_ENABLED_ENV, err.getvalue())

    def test_invalid_config_returns_user_input_error(self) -> None:
        from mythic_vibe_cli.commands import cmd_surface_chat
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        ns = self._ns(backend="matrix")
        err = io.StringIO()
        with patch.dict(
            "os.environ",
            {
                CHAT_BRIDGE_ENABLED_ENV: "1",
                "MYTHIC_CHAT_MATRIX_ACCESS_TOKEN": "",
                "MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS": "",
            },
            clear=False,
        ), redirect_stderr(err):
            code = cmd_surface_chat(ns)
        self.assertEqual(code, USER_INPUT_ERROR)
        self.assertIn("config error", err.getvalue())

    def test_happy_run_path_invokes_matrix_loop(self) -> None:
        from mythic_vibe_cli.commands import cmd_surface_chat
        from mythic_vibe_cli.exit_codes import SUCCESS

        ns = self._ns(backend="matrix", json=True)
        captured: dict[str, object] = {}

        def fake_loop(config, *, stop_event=None, max_iterations=None):
            captured["config_homeserver"] = config.homeserver
            captured["max_iterations"] = max_iterations
            return 7  # number dispatched

        out = io.StringIO()
        with patch.dict(
            "os.environ",
            {
                CHAT_BRIDGE_ENABLED_ENV: "1",
                "MYTHIC_CHAT_MATRIX_HOMESERVER": "https://my.h",
                "MYTHIC_CHAT_MATRIX_ACCESS_TOKEN": "tok",
                "MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS": "!a:my.h",
                "MYTHIC_CHAT_MATRIX_USER_ID": "@bot:my.h",
            },
            clear=False,
        ), patch(
            "mythic_vibe_cli.surfaces.chat_bridge_loop.run_matrix_loop",
            side_effect=fake_loop,
        ), redirect_stdout(out):
            code = cmd_surface_chat(ns)

        self.assertEqual(code, SUCCESS)
        # The output is a mix of text status lines and a JSON payload —
        # find the JSON line.
        payload = None
        for line in out.getvalue().splitlines():
            stripped = line.strip()
            if stripped.startswith("{"):
                try:
                    payload = json.loads(stripped)
                    break
                except json.JSONDecodeError:
                    continue
        # The JSON might also span multiple lines; fall back to a whole-output parse
        # against the JSON object slice.
        if payload is None:
            text = out.getvalue()
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                payload = json.loads(text[start : end + 1])
        self.assertIsNotNone(payload, f"no JSON found in: {out.getvalue()!r}")
        self.assertEqual(payload["dispatched"], 7)
        self.assertEqual(payload["backend"], "matrix")
        self.assertEqual(captured["config_homeserver"], "https://my.h")
        self.assertEqual(captured["max_iterations"], 1)

    def test_legacy_scaffolding_path_unchanged_when_run_absent(self) -> None:
        """Phase E preserved the original 17.4 scaffolding-and-exit
        body — passing no --run flag should still produce a notice
        and exit cleanly without touching env or config."""
        from mythic_vibe_cli.commands import cmd_surface_chat
        from mythic_vibe_cli.exit_codes import SUCCESS

        ns = self._ns(run=False)
        out = io.StringIO()
        # No CHAT_BRIDGE_ENABLED_ENV set — must not gate the legacy path.
        with patch.dict(
            "os.environ",
            {CHAT_BRIDGE_ENABLED_ENV: ""},
            clear=False,
        ), redirect_stdout(out):
            code = cmd_surface_chat(ns)
        self.assertEqual(code, SUCCESS)
        self.assertIn("scaffolding entry", out.getvalue())


if __name__ == "__main__":
    unittest.main()
