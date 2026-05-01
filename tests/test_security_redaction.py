"""Tests for PH-11 Slice 11.2 — redaction engine."""

from __future__ import annotations

import re
import unittest

from mythic_vibe_cli.security.redaction import (
    DEFAULT_FORBIDDEN_PATHS,
    REDACTION_PLACEHOLDER,
    RedactionEngine,
    engine_from_config,
    is_path_forbidden,
    redact_payload,
    redact_text,
)


# ---- redact_text -----------------------------------------------------


class RedactTextTests(unittest.TestCase):
    def test_redacts_openai_key(self) -> None:
        text = "key=sk-AAAABBBBCCCCDDDD"
        out = redact_text(text)
        self.assertNotIn("sk-AAAABBBBCCCCDDDD", out)
        self.assertIn(REDACTION_PLACEHOLDER, out)

    def test_redacts_gemini_key(self) -> None:
        text = "GEMINI_API_KEY=AIzaSyABCDEFGHIJ"
        out = redact_text(text)
        self.assertNotIn("AIzaSyABCDEFGHIJ", out)

    def test_redacts_bearer_header(self) -> None:
        text = "Authorization: Bearer abc.def.ghi"
        out = redact_text(text)
        self.assertIn(REDACTION_PLACEHOLDER, out)

    def test_redacts_secret_keyword(self) -> None:
        text = 'password = "hunter2"'
        out = redact_text(text)
        self.assertIn(REDACTION_PLACEHOLDER, out)

    def test_blank_text_passes_through(self) -> None:
        self.assertEqual(redact_text(""), "")

    def test_clean_text_unchanged(self) -> None:
        self.assertEqual(redact_text("hello world"), "hello world")


# ---- redact_payload --------------------------------------------------


class RedactPayloadTests(unittest.TestCase):
    def test_dict_recursion(self) -> None:
        out = redact_payload({"key": "sk-AAAABBBBCCCCDDDD", "ok": "fine"})
        self.assertEqual(out["ok"], "fine")
        self.assertIn(REDACTION_PLACEHOLDER, out["key"])

    def test_list_recursion(self) -> None:
        out = redact_payload(["clean", "sk-AAAABBBBCCCCDDDD"])
        self.assertEqual(out[0], "clean")
        self.assertIn(REDACTION_PLACEHOLDER, out[1])

    def test_tuple_recursion(self) -> None:
        out = redact_payload(("ok", "sk-AAAABBBBCCCCDDDD"))
        self.assertIsInstance(out, tuple)
        self.assertIn(REDACTION_PLACEHOLDER, out[1])

    def test_non_string_scalars_passthrough(self) -> None:
        for value in (42, True, None, 3.14):
            self.assertEqual(redact_payload(value), value)


# ---- is_path_forbidden -----------------------------------------------


class IsPathForbiddenTests(unittest.TestCase):
    def test_dotenv_forbidden(self) -> None:
        self.assertTrue(is_path_forbidden(".env"))
        self.assertTrue(is_path_forbidden(".env.local"))
        self.assertTrue(is_path_forbidden(".env.production"))

    def test_pem_key_forbidden(self) -> None:
        self.assertTrue(is_path_forbidden("server.pem"))
        self.assertTrue(is_path_forbidden("private.key"))
        self.assertTrue(is_path_forbidden("auth.token"))

    def test_credentials_forbidden(self) -> None:
        self.assertTrue(is_path_forbidden("credentials.json"))
        self.assertTrue(is_path_forbidden("service_account.json"))
        self.assertTrue(is_path_forbidden("id_rsa"))
        self.assertTrue(is_path_forbidden("id_ed25519"))

    def test_safe_paths(self) -> None:
        self.assertFalse(is_path_forbidden("README.md"))
        self.assertFalse(is_path_forbidden("src/main.py"))
        self.assertFalse(is_path_forbidden("config.toml"))

    def test_basename_only(self) -> None:
        # Forbidden pattern matches against basename, not full path.
        self.assertTrue(is_path_forbidden("/some/deep/path/.env"))
        self.assertTrue(is_path_forbidden("subdir/private.key"))


# ---- RedactionEngine -------------------------------------------------


class RedactionEngineTests(unittest.TestCase):
    def test_default_engine_to_dict(self) -> None:
        engine = RedactionEngine()
        payload = engine.to_dict()
        self.assertGreater(payload["pattern_count"], 0)
        self.assertIn(".env", payload["forbidden_paths"])
        self.assertEqual(payload["placeholder"], REDACTION_PLACEHOLDER)

    def test_custom_placeholder(self) -> None:
        engine = RedactionEngine(placeholder="<HIDDEN>")
        out = engine.redact_text("api_key=sk-XXXAAABBBCCC")
        self.assertIn("<HIDDEN>", out)
        self.assertNotIn(REDACTION_PLACEHOLDER, out)

    def test_extra_patterns(self) -> None:
        engine = RedactionEngine(
            patterns=(re.compile(r"AKIA[0-9A-Z]{6,}"),),
        )
        out = engine.redact_text("AWS=AKIAFAKEKEY12345")
        self.assertIn(REDACTION_PLACEHOLDER, out)


# ---- engine_from_config ----------------------------------------------


class EngineFromConfigTests(unittest.TestCase):
    def test_no_section_returns_defaults(self) -> None:
        engine = engine_from_config({})
        self.assertEqual(engine.placeholder, REDACTION_PLACEHOLDER)
        self.assertEqual(
            engine.forbidden_paths, DEFAULT_FORBIDDEN_PATHS
        )

    def test_extra_patterns_appended(self) -> None:
        engine = engine_from_config(
            {"redaction": {"extra_patterns": [r"AKIA[0-9A-Z]{6,}"]}}
        )
        self.assertGreater(
            len(engine.patterns), len(RedactionEngine().patterns)
        )
        out = engine.redact_text("AWS=AKIAFAKEKEY12345")
        self.assertIn(REDACTION_PLACEHOLDER, out)

    def test_invalid_extra_pattern_skipped(self) -> None:
        # An invalid regex shouldn't crash the engine builder.
        engine = engine_from_config(
            {"redaction": {"extra_patterns": ["[invalid", "AKIA[0-9A-Z]{6,}"]}}
        )
        # Defaults + the one valid extra.
        self.assertEqual(
            len(engine.patterns), len(RedactionEngine().patterns) + 1
        )

    def test_extra_forbidden_paths_appended(self) -> None:
        engine = engine_from_config(
            {"redaction": {"forbidden_paths": ["*.secret"]}}
        )
        self.assertTrue(engine.is_path_forbidden("nuclear.secret"))
        # Defaults still respected.
        self.assertTrue(engine.is_path_forbidden(".env"))

    def test_custom_placeholder(self) -> None:
        engine = engine_from_config(
            {"redaction": {"placeholder": "<HIDDEN>"}}
        )
        self.assertEqual(engine.placeholder, "<HIDDEN>")

    def test_invalid_section_falls_back_to_defaults(self) -> None:
        engine = engine_from_config({"redaction": "not a dict"})
        self.assertEqual(engine.placeholder, REDACTION_PLACEHOLDER)


if __name__ == "__main__":
    unittest.main()
