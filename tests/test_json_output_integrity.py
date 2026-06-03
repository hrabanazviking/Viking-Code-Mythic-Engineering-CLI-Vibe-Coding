"""Regression tests for machine-readable CLI stdout contracts."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS


def _parse_single_json_document(text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    payload, end = decoder.raw_decode(text)
    trailing = text[end:].strip()
    if trailing:
        raise AssertionError(f"stdout contains extra data after JSON document: {trailing!r}")
    if not isinstance(payload, dict):
        raise AssertionError(f"stdout JSON must be an object, got {type(payload).__name__}")
    return payload


class JsonOutputIntegrityTests(unittest.TestCase):
    def test_simulate_json_emits_one_document(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = app.main(["simulate", "--json"])

        self.assertEqual(code, SUCCESS)
        self.assertEqual(stderr.getvalue(), "")
        payload = _parse_single_json_document(stdout.getvalue())
        self.assertEqual(payload["command"], "simulate")
        self.assertTrue(payload["report"]["ok"])
        self.assertEqual(payload["report"]["total"], 4)
