"""Phase E.4 (audit remediation 2026-05-02, finding #7) — coverage
for the chat-bridge HTTP client functions.

The first audit flagged ``matrix_send_message``, ``telegram_send_message``,
``_matrix_request``, and ``_telegram_request`` as zero-coverage. This
test file exercises each one through a mocked ``urllib.request.urlopen``,
asserting URL shape, headers, body, and method. Additionally it covers
the Phase E.0 additive ``room_id`` / ``chat_id`` keyword overrides on
the public send functions.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from mythic_vibe_cli.surfaces.chat_bridge import (
    ChatBridgeConfigError,
    MatrixConfig,
    TelegramConfig,
    _matrix_request,
    _telegram_request,
    matrix_send_message,
    telegram_send_message,
)


class _FakeResponse:
    """Stand-in for urllib's response context-manager."""

    def __init__(self, body: bytes | dict | str = b"{}") -> None:
        if isinstance(body, dict):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self._body = body
        self.captured_request = None  # populated externally

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


# --------------------------------------------------------------------------- #
# _matrix_request
# --------------------------------------------------------------------------- #


class MatrixRequestTests(unittest.TestCase):
    def _config(self) -> MatrixConfig:
        return MatrixConfig(
            homeserver="https://h.example",
            access_token="tok-xyz",
            room_id="!room:example",
            allowed_rooms=("!room:example",),
        )

    def test_get_with_params_builds_query_string(self) -> None:
        cfg = self._config()
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["auth"] = req.headers.get("Authorization")
            captured["body"] = req.data
            return _FakeResponse({"ok": True})

        with patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            payload = _matrix_request(
                cfg, "GET", "/_matrix/client/v3/sync",
                params={"timeout": 30000, "since": "abc"},
            )
        self.assertEqual(payload, {"ok": True})
        self.assertIn("/_matrix/client/v3/sync", captured["url"])
        self.assertIn("timeout=30000", captured["url"])
        self.assertIn("since=abc", captured["url"])
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["auth"], "Bearer tok-xyz")
        self.assertIsNone(captured["body"])

    def test_put_with_body_serialises_json(self) -> None:
        cfg = self._config()
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout):
            captured["method"] = req.get_method()
            captured["content_type"] = req.headers.get("Content-type")
            captured["body"] = req.data
            return _FakeResponse({"event_id": "$abc"})

        with patch(
            "urllib.request.urlopen", side_effect=fake_urlopen
        ):
            payload = _matrix_request(
                cfg, "PUT", "/_matrix/.../send/m.room.message/txn1",
                body={"msgtype": "m.text", "body": "hi"},
            )
        self.assertEqual(payload["event_id"], "$abc")
        self.assertEqual(captured["method"], "PUT")
        self.assertEqual(captured["content_type"], "application/json")
        decoded = json.loads(captured["body"].decode())
        self.assertEqual(decoded["body"], "hi")

    def test_empty_response_body_returns_empty_dict(self) -> None:
        cfg = self._config()
        with patch(
            "urllib.request.urlopen", return_value=_FakeResponse(b"")
        ):
            self.assertEqual(_matrix_request(cfg, "GET", "/x"), {})


# --------------------------------------------------------------------------- #
# matrix_send_message — including room_id keyword override
# --------------------------------------------------------------------------- #


class MatrixSendMessageTests(unittest.TestCase):
    def _config(self) -> MatrixConfig:
        return MatrixConfig(
            homeserver="https://h.example",
            access_token="tok",
            room_id="!default:example",
            allowed_rooms=("!default:example",),
        )

    def test_uses_config_room_id_when_no_override(self) -> None:
        cfg = self._config()
        captured: dict[str, str] = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            return _FakeResponse({"event_id": "$1"})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            matrix_send_message(cfg, "hello", txn_id="t1")
        self.assertIn("/rooms/%21default%3Aexample/send/", captured["url"])
        # txn_id appears at the URL tail.
        self.assertTrue(captured["url"].rstrip("/").endswith("/t1"))

    def test_room_id_override_routes_to_alternate_room(self) -> None:
        cfg = self._config()
        captured: dict[str, str] = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            return _FakeResponse({"event_id": "$1"})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            matrix_send_message(
                cfg, "hello", room_id="!other:example", txn_id="t2"
            )
        self.assertIn("/rooms/%21other%3Aexample/send/", captured["url"])
        # config.room_id MUST NOT appear in the URL when overridden.
        self.assertNotIn("default", captured["url"])

    def test_no_room_id_anywhere_raises_chat_bridge_config_error(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h",
            access_token="t",
            room_id="",  # legacy default empty
            allowed_rooms=("!a:s",),
        )
        with self.assertRaises(ChatBridgeConfigError):
            matrix_send_message(cfg, "hi", room_id=None)


# --------------------------------------------------------------------------- #
# _telegram_request
# --------------------------------------------------------------------------- #


class TelegramRequestTests(unittest.TestCase):
    def _config(self) -> TelegramConfig:
        return TelegramConfig(
            bot_token="bot-token:abc",
            chat_id=42,
            allowed_chats=("42",),
        )

    def test_post_serialises_body_and_uses_post_method(self) -> None:
        cfg = self._config()
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            captured["method"] = req.get_method()
            captured["body"] = req.data
            captured["content_type"] = req.headers.get("Content-type")
            return _FakeResponse({"ok": True, "result": []})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            payload = _telegram_request(
                cfg, "sendMessage", body={"chat_id": 42, "text": "hi"}
            )
        self.assertEqual(payload, {"ok": True, "result": []})
        self.assertIn("/botbot-token", captured["url"])
        self.assertIn("/sendMessage", captured["url"])
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["content_type"], "application/json")
        self.assertEqual(json.loads(captured["body"]), {"chat_id": 42, "text": "hi"})

    def test_empty_body_yields_empty_object_post(self) -> None:
        cfg = self._config()
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout):
            captured["body"] = req.data
            return _FakeResponse({})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _telegram_request(cfg, "getMe")
        self.assertEqual(json.loads(captured["body"]), {})


# --------------------------------------------------------------------------- #
# telegram_send_message — including chat_id keyword override
# --------------------------------------------------------------------------- #


class TelegramSendMessageTests(unittest.TestCase):
    def _config(self) -> TelegramConfig:
        return TelegramConfig(
            bot_token="t",
            chat_id=42,
            allowed_chats=("42",),
        )

    def test_uses_config_chat_id_when_no_override(self) -> None:
        cfg = self._config()
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout):
            captured["body"] = json.loads(req.data)
            return _FakeResponse({"ok": True, "result": {"message_id": 1}})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            telegram_send_message(cfg, "hello")
        self.assertEqual(captured["body"]["chat_id"], 42)
        self.assertEqual(captured["body"]["text"], "hello")
        self.assertEqual(captured["body"]["parse_mode"], "Markdown")

    def test_chat_id_override_routes_to_alternate_chat(self) -> None:
        cfg = self._config()
        captured: dict[str, object] = {}

        def fake_urlopen(req, timeout):
            captured["body"] = json.loads(req.data)
            return _FakeResponse({"ok": True, "result": {"message_id": 1}})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            telegram_send_message(cfg, "hello", chat_id=99)
        self.assertEqual(captured["body"]["chat_id"], 99)

    def test_no_chat_id_anywhere_raises_chat_bridge_config_error(self) -> None:
        cfg = TelegramConfig(
            bot_token="t",
            chat_id="",  # legacy default empty
            allowed_chats=("99",),
        )
        with self.assertRaises(ChatBridgeConfigError):
            telegram_send_message(cfg, "hi", chat_id=None)


if __name__ == "__main__":
    unittest.main()
