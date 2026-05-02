"""Phase E.0 (audit remediation 2026-05-02, finding #2) — chat bridge
config layer tests.

Covers ``MatrixConfig`` and ``TelegramConfig`` with all the additive
classmethods Phase E.0 added: ``from_env``, ``from_file``,
``from_sources``, ``validate``, plus ``is_room_allowed``,
``is_chat_allowed``, ``is_user_allowed``, the master env gate
``is_chat_bridge_enabled``, and the ``ALLOWLIST_BROADCAST`` sentinel
behaviour.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mythic_vibe_cli.surfaces.chat_bridge import (
    ALLOWLIST_BROADCAST,
    CHAT_BRIDGE_ENABLED_ENV,
    ChatBridgeConfigError,
    MatrixConfig,
    TelegramConfig,
    _parse_csv_allowlist,
    _read_config_file,
    is_chat_bridge_enabled,
)


def _clear_env(*names: str) -> dict[str, str]:
    """Build an env dict with the named MYTHIC_CHAT_* vars cleared.
    Used as `patch.dict('os.environ', _clear_env(...), clear=False)`
    to deterministically remove inherited values."""
    return {n: "" for n in names}


def _matrix_env_clear() -> dict[str, str]:
    return _clear_env(
        "MYTHIC_CHAT_MATRIX_HOMESERVER",
        "MYTHIC_CHAT_MATRIX_ACCESS_TOKEN",
        "MYTHIC_CHAT_MATRIX_USER_ID",
        "MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS",
        "MYTHIC_CHAT_MATRIX_ROOM_ID",
        "MYTHIC_CHAT_MATRIX_SYNC_TIMEOUT_MS",
    )


def _telegram_env_clear() -> dict[str, str]:
    return _clear_env(
        "MYTHIC_CHAT_TELEGRAM_BOT_TOKEN",
        "MYTHIC_CHAT_TELEGRAM_CHAT_ID",
        "MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS",
        "MYTHIC_CHAT_TELEGRAM_ALLOWED_USERS",
        "MYTHIC_CHAT_TELEGRAM_API_ROOT",
        "MYTHIC_CHAT_TELEGRAM_POLL_TIMEOUT_S",
    )


# --------------------------------------------------------------------------- #
# Master env gate
# --------------------------------------------------------------------------- #


class IsChatBridgeEnabledTests(unittest.TestCase):
    def test_unset_env_returns_false(self) -> None:
        with patch.dict("os.environ", {CHAT_BRIDGE_ENABLED_ENV: ""}, clear=False):
            self.assertFalse(is_chat_bridge_enabled())

    def test_truthy_values_enable(self) -> None:
        for value in ("1", "true", "yes", "on", "TRUE", "Yes"):
            with self.subTest(value=value):
                with patch.dict(
                    "os.environ", {CHAT_BRIDGE_ENABLED_ENV: value}, clear=False
                ):
                    self.assertTrue(is_chat_bridge_enabled())

    def test_falsy_values_disable(self) -> None:
        for value in ("0", "false", "no", "off", "anything-else", " "):
            with self.subTest(value=value):
                with patch.dict(
                    "os.environ", {CHAT_BRIDGE_ENABLED_ENV: value}, clear=False
                ):
                    self.assertFalse(is_chat_bridge_enabled())


# --------------------------------------------------------------------------- #
# CSV allowlist parser + JSON config-file reader
# --------------------------------------------------------------------------- #


class ParseCsvAllowlistTests(unittest.TestCase):
    def test_empty_returns_empty_tuple(self) -> None:
        self.assertEqual(_parse_csv_allowlist(""), ())
        self.assertEqual(_parse_csv_allowlist("   "), ())

    def test_single_value(self) -> None:
        self.assertEqual(_parse_csv_allowlist("!a:s"), ("!a:s",))

    def test_multiple_values_stripped(self) -> None:
        self.assertEqual(
            _parse_csv_allowlist("!a:s, !b:s ,!c:s"), ("!a:s", "!b:s", "!c:s")
        )

    def test_broadcast_sentinel_collapses_to_single_entry(self) -> None:
        self.assertEqual(_parse_csv_allowlist("*"), (ALLOWLIST_BROADCAST,))
        self.assertEqual(
            _parse_csv_allowlist("!a:s, *, !b:s"), (ALLOWLIST_BROADCAST,)
        )

    def test_duplicates_removed(self) -> None:
        self.assertEqual(
            _parse_csv_allowlist("!a:s,!a:s,!b:s"), ("!a:s", "!b:s")
        )


class ReadConfigFileTests(unittest.TestCase):
    def test_reads_well_formed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cb.json"
            path.write_text(
                json.dumps({"matrix": {"homeserver": "https://h"}}),
                encoding="utf-8",
            )
            payload = _read_config_file(path)
            self.assertEqual(payload["matrix"]["homeserver"], "https://h")

    def test_raises_on_non_object_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cb.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                _read_config_file(path)


# --------------------------------------------------------------------------- #
# MatrixConfig
# --------------------------------------------------------------------------- #


class MatrixConfigFromEnvTests(unittest.TestCase):
    def test_empty_env_yields_empty_config(self) -> None:
        with patch.dict("os.environ", _matrix_env_clear(), clear=False):
            cfg = MatrixConfig.from_env()
        self.assertEqual(cfg.homeserver, "https://matrix.org")  # default
        self.assertEqual(cfg.access_token, "")
        self.assertEqual(cfg.allowed_rooms, ())
        self.assertEqual(cfg.user_id, "")
        self.assertEqual(cfg.room_id, "")

    def test_full_env_parses_all_fields(self) -> None:
        env = _matrix_env_clear()
        env.update(
            {
                "MYTHIC_CHAT_MATRIX_HOMESERVER": "https://my.matrix.example",
                "MYTHIC_CHAT_MATRIX_ACCESS_TOKEN": "tok-123",
                "MYTHIC_CHAT_MATRIX_USER_ID": "@bot:example",
                "MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS": "!a:example,!b:example",
                "MYTHIC_CHAT_MATRIX_SYNC_TIMEOUT_MS": "20000",
            }
        )
        with patch.dict("os.environ", env, clear=False):
            cfg = MatrixConfig.from_env()
        self.assertEqual(cfg.homeserver, "https://my.matrix.example")
        self.assertEqual(cfg.access_token, "tok-123")
        self.assertEqual(cfg.user_id, "@bot:example")
        self.assertEqual(cfg.allowed_rooms, ("!a:example", "!b:example"))
        self.assertEqual(cfg.room_id, "!a:example")  # auto-derived from first allowed
        self.assertEqual(cfg.sync_timeout_ms, 20_000)

    def test_explicit_room_id_overrides_allowlist_first(self) -> None:
        env = _matrix_env_clear()
        env.update(
            {
                "MYTHIC_CHAT_MATRIX_ACCESS_TOKEN": "tok",
                "MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS": "!a:s,!b:s",
                "MYTHIC_CHAT_MATRIX_ROOM_ID": "!explicit:s",
            }
        )
        with patch.dict("os.environ", env, clear=False):
            cfg = MatrixConfig.from_env()
        self.assertEqual(cfg.room_id, "!explicit:s")

    def test_invalid_sync_timeout_falls_back_to_default(self) -> None:
        env = _matrix_env_clear()
        env["MYTHIC_CHAT_MATRIX_SYNC_TIMEOUT_MS"] = "not-an-int"
        with patch.dict("os.environ", env, clear=False):
            cfg = MatrixConfig.from_env()
        self.assertEqual(cfg.sync_timeout_ms, 30_000)


class MatrixConfigFromFileTests(unittest.TestCase):
    def test_reads_matrix_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cb.json"
            path.write_text(
                json.dumps(
                    {
                        "matrix": {
                            "homeserver": "https://h",
                            "access_token": "tok",
                            "user_id": "@bot:h",
                            "allowed_rooms": ["!a:h"],
                            "room_id": "!a:h",
                            "sync_timeout_ms": 25_000,
                        },
                        "telegram": {"bot_token": "ignore-me"},
                    }
                ),
                encoding="utf-8",
            )
            cfg = MatrixConfig.from_file(path)
        self.assertEqual(cfg.homeserver, "https://h")
        self.assertEqual(cfg.access_token, "tok")
        self.assertEqual(cfg.allowed_rooms, ("!a:h",))
        self.assertEqual(cfg.user_id, "@bot:h")
        self.assertEqual(cfg.sync_timeout_ms, 25_000)

    def test_missing_matrix_section_yields_empty_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cb.json"
            path.write_text(json.dumps({"telegram": {}}), encoding="utf-8")
            cfg = MatrixConfig.from_file(path)
        self.assertEqual(cfg.access_token, "")
        self.assertEqual(cfg.allowed_rooms, ())

    def test_csv_string_allowed_rooms_is_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cb.json"
            path.write_text(
                json.dumps(
                    {"matrix": {"allowed_rooms": "!a:s, !b:s, !c:s"}}
                ),
                encoding="utf-8",
            )
            cfg = MatrixConfig.from_file(path)
        self.assertEqual(cfg.allowed_rooms, ("!a:s", "!b:s", "!c:s"))


class MatrixConfigFromSourcesTests(unittest.TestCase):
    def test_no_path_behaves_like_from_env(self) -> None:
        env = _matrix_env_clear()
        env["MYTHIC_CHAT_MATRIX_ACCESS_TOKEN"] = "from-env"
        with patch.dict("os.environ", env, clear=False):
            cfg = MatrixConfig.from_sources(config_path=None)
        self.assertEqual(cfg.access_token, "from-env")

    def test_file_overrides_env_when_both_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cb.json"
            path.write_text(
                json.dumps(
                    {"matrix": {"access_token": "from-file", "allowed_rooms": ["!file:s"]}}
                ),
                encoding="utf-8",
            )
            env = _matrix_env_clear()
            env["MYTHIC_CHAT_MATRIX_ACCESS_TOKEN"] = "from-env"
            env["MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS"] = "!env:s"
            with patch.dict("os.environ", env, clear=False):
                cfg = MatrixConfig.from_sources(config_path=path)
        self.assertEqual(cfg.access_token, "from-file")
        self.assertEqual(cfg.allowed_rooms, ("!file:s",))

    def test_env_provides_default_when_file_omits_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cb.json"
            path.write_text(
                json.dumps({"matrix": {"allowed_rooms": ["!file:s"]}}),
                encoding="utf-8",
            )
            env = _matrix_env_clear()
            env["MYTHIC_CHAT_MATRIX_ACCESS_TOKEN"] = "from-env"
            with patch.dict("os.environ", env, clear=False):
                cfg = MatrixConfig.from_sources(config_path=path)
        self.assertEqual(cfg.access_token, "from-env")
        self.assertEqual(cfg.allowed_rooms, ("!file:s",))

    def test_unreadable_file_raises_chat_bridge_config_error(self) -> None:
        with self.assertRaises(ChatBridgeConfigError):
            MatrixConfig.from_sources(
                config_path=Path("/nonexistent-chat-bridge-config.json")
            )


class MatrixConfigValidateTests(unittest.TestCase):
    def test_validate_refuses_without_access_token(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h",
            access_token="",
            room_id="!a:h",
            allowed_rooms=("!a:h",),
        )
        with self.assertRaises(ChatBridgeConfigError) as ctx:
            cfg.validate()
        self.assertIn("access_token", str(ctx.exception))

    def test_validate_refuses_without_allowlist(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h",
            access_token="tok",
            room_id="!a:h",
            allowed_rooms=(),  # the safety-load-bearing field
        )
        with self.assertRaises(ChatBridgeConfigError) as ctx:
            cfg.validate()
        self.assertIn("allowed_rooms", str(ctx.exception))

    def test_validate_accepts_explicit_broadcast_opt_in(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h",
            access_token="tok",
            room_id="",
            allowed_rooms=(ALLOWLIST_BROADCAST,),
        )
        cfg.validate()  # must not raise

    def test_validate_accepts_explicit_room_allowlist(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h",
            access_token="tok",
            room_id="!a:h",
            allowed_rooms=("!a:h",),
        )
        cfg.validate()


class MatrixIsRoomAllowedTests(unittest.TestCase):
    def test_empty_allowlist_denies_everything(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h", access_token="t", room_id="", allowed_rooms=()
        )
        self.assertFalse(cfg.is_room_allowed("!any:s"))

    def test_explicit_match(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h",
            access_token="t",
            room_id="",
            allowed_rooms=("!a:s", "!b:s"),
        )
        self.assertTrue(cfg.is_room_allowed("!a:s"))
        self.assertTrue(cfg.is_room_allowed("!b:s"))
        self.assertFalse(cfg.is_room_allowed("!c:s"))

    def test_broadcast_allows_everything(self) -> None:
        cfg = MatrixConfig(
            homeserver="https://h",
            access_token="t",
            room_id="",
            allowed_rooms=(ALLOWLIST_BROADCAST,),
        )
        self.assertTrue(cfg.is_room_allowed("!whatever:server"))


# --------------------------------------------------------------------------- #
# TelegramConfig
# --------------------------------------------------------------------------- #


class TelegramConfigFromEnvTests(unittest.TestCase):
    def test_empty_env_yields_empty_config(self) -> None:
        with patch.dict("os.environ", _telegram_env_clear(), clear=False):
            cfg = TelegramConfig.from_env()
        self.assertEqual(cfg.bot_token, "")
        self.assertEqual(cfg.chat_id, "")
        self.assertEqual(cfg.allowed_chats, ())
        self.assertEqual(cfg.allowed_users, ())

    def test_full_env_parses_all_fields(self) -> None:
        env = _telegram_env_clear()
        env.update(
            {
                "MYTHIC_CHAT_TELEGRAM_BOT_TOKEN": "bot-123:abc",
                "MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS": "1234,5678",
                "MYTHIC_CHAT_TELEGRAM_ALLOWED_USERS": "9999",
                "MYTHIC_CHAT_TELEGRAM_POLL_TIMEOUT_S": "20",
            }
        )
        with patch.dict("os.environ", env, clear=False):
            cfg = TelegramConfig.from_env()
        self.assertEqual(cfg.bot_token, "bot-123:abc")
        self.assertEqual(cfg.allowed_chats, ("1234", "5678"))
        self.assertEqual(cfg.allowed_users, ("9999",))
        self.assertEqual(cfg.chat_id, 1234)  # auto-derived first as int
        self.assertEqual(cfg.poll_timeout_s, 20)

    def test_string_chat_id_preserved_when_not_numeric(self) -> None:
        env = _telegram_env_clear()
        env["MYTHIC_CHAT_TELEGRAM_BOT_TOKEN"] = "x"
        env["MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS"] = "@channel-name"
        with patch.dict("os.environ", env, clear=False):
            cfg = TelegramConfig.from_env()
        self.assertEqual(cfg.chat_id, "@channel-name")


class TelegramConfigValidateTests(unittest.TestCase):
    def test_validate_refuses_without_bot_token(self) -> None:
        cfg = TelegramConfig(
            bot_token="", chat_id=0, allowed_chats=("123",)
        )
        with self.assertRaises(ChatBridgeConfigError) as ctx:
            cfg.validate()
        self.assertIn("bot_token", str(ctx.exception))

    def test_validate_refuses_without_allowed_chats(self) -> None:
        cfg = TelegramConfig(bot_token="t", chat_id=0, allowed_chats=())
        with self.assertRaises(ChatBridgeConfigError) as ctx:
            cfg.validate()
        self.assertIn("allowed_chats", str(ctx.exception))

    def test_validate_accepts_explicit_broadcast_opt_in(self) -> None:
        cfg = TelegramConfig(
            bot_token="t", chat_id=0, allowed_chats=(ALLOWLIST_BROADCAST,)
        )
        cfg.validate()


class TelegramAllowlistTests(unittest.TestCase):
    def test_chat_allowlist_explicit(self) -> None:
        cfg = TelegramConfig(
            bot_token="t", chat_id=0, allowed_chats=("1234", "5678")
        )
        self.assertTrue(cfg.is_chat_allowed(1234))
        self.assertTrue(cfg.is_chat_allowed("5678"))
        self.assertFalse(cfg.is_chat_allowed(9999))

    def test_chat_allowlist_broadcast(self) -> None:
        cfg = TelegramConfig(
            bot_token="t", chat_id=0, allowed_chats=(ALLOWLIST_BROADCAST,)
        )
        self.assertTrue(cfg.is_chat_allowed(99))

    def test_user_allowlist_empty_means_any_user(self) -> None:
        cfg = TelegramConfig(
            bot_token="t",
            chat_id=0,
            allowed_chats=("1",),
            allowed_users=(),
        )
        self.assertTrue(cfg.is_user_allowed(42))
        self.assertTrue(cfg.is_user_allowed("anyone"))

    def test_user_allowlist_explicit(self) -> None:
        cfg = TelegramConfig(
            bot_token="t",
            chat_id=0,
            allowed_chats=("1",),
            allowed_users=("42",),
        )
        self.assertTrue(cfg.is_user_allowed(42))
        self.assertTrue(cfg.is_user_allowed("42"))
        self.assertFalse(cfg.is_user_allowed(99))


if __name__ == "__main__":
    unittest.main()
