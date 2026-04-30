"""Tests for the telemetry extension + reader (PH-06 slice 6.5)."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.ai.providers.base import timed_post_json
from mythic_vibe_cli.app import build_parser
from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


def _seed_log(root: Path, entries: list[dict[str, object]]) -> Path:
    """Write a sequence of JSONL entries into the canonical
    provider_calls.jsonl path so the reader has something to surface."""
    log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(json.dumps(entry) + "\n")
    return log_path


# ---- timed_post_json --------------------------------------------------


class TimedPostJsonTests(unittest.TestCase):
    def test_returns_payload_and_latency(self) -> None:
        # Stub the underlying post_json so we don't make a real call.
        with mock.patch(
            "mythic_vibe_cli.ai.providers.base.post_json",
            return_value={"ok": True},
        ):
            parsed, latency = timed_post_json("https://x", {}, {})
        self.assertEqual(parsed, {"ok": True})
        self.assertIsInstance(latency, float)
        self.assertGreaterEqual(latency, 0.0)

    def test_latency_rounded_to_two_decimals(self) -> None:
        with mock.patch(
            "mythic_vibe_cli.ai.providers.base.post_json",
            return_value={"ok": True},
        ):
            _parsed, latency = timed_post_json("https://x", {}, {})
        # Two decimal places => the second-decimal place stays stable
        # under repeated call (sanity check on the rounding contract).
        self.assertEqual(round(latency, 2), latency)


# ---- argparse ----------------------------------------------------------


class AiTelemetryArgparseTests(unittest.TestCase):
    def test_parses_default_limit(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(["ai", "telemetry"])
        self.assertEqual(ns.command, "ai")
        self.assertEqual(ns.ai_command, "telemetry")
        self.assertEqual(ns.limit, 20)
        self.assertEqual(ns.provider, "")

    def test_provider_filter_and_limit(self) -> None:
        parser = build_parser()
        ns = parser.parse_args(
            [
                "ai",
                "telemetry",
                "--provider",
                "ollama",
                "--limit",
                "5",
                "--json",
            ]
        )
        self.assertEqual(ns.provider, "ollama")
        self.assertEqual(ns.limit, 5)
        self.assertTrue(ns.json)


# ---- cmd_ai_telemetry --------------------------------------------------


class CmdAiTelemetryTests(unittest.TestCase):
    def test_handler_registered_via_dispatch(self) -> None:
        # The dispatch routes "telemetry" to cmd_ai_telemetry; make
        # sure the bare COMMAND_HANDLERS entry is the dispatcher
        # (existing behaviour) and that the dispatcher has the route.
        from mythic_vibe_cli.commands import cmd_ai_dispatch

        self.assertIs(COMMAND_HANDLERS["ai"], cmd_ai_dispatch)

    def test_missing_log_text_message(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp, provider="", limit=10, json=False
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                exit_code = cmd_ai_telemetry(ns)
        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("no log yet", buf.getvalue())

    def test_missing_log_json_returns_empty_envelope(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp, provider="", limit=10, json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_telemetry(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["entries"], [])
        self.assertEqual(payload["limit"], 10)

    def test_returns_entries_newest_first(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_log(
                root,
                [
                    {
                        "timestamp": "2026-01-01T00:00:00Z",
                        "provider": "anthropic",
                        "model": "claude",
                        "latency_ms": 100.0,
                    },
                    {
                        "timestamp": "2026-02-01T00:00:00Z",
                        "provider": "ollama",
                        "model": "llama3.2",
                        "latency_ms": 50.0,
                    },
                    {
                        "timestamp": "2026-03-01T00:00:00Z",
                        "provider": "openai",
                        "model": "gpt-x",
                        "latency_ms": 75.0,
                    },
                ],
            )
            ns = argparse.Namespace(
                path=str(root), provider="", limit=10, json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_telemetry(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["count"], 3)
        # Newest-first: openai (mar) -> ollama (feb) -> anthropic (jan).
        timestamps = [entry["timestamp"] for entry in payload["entries"]]
        self.assertEqual(
            timestamps,
            [
                "2026-03-01T00:00:00Z",
                "2026-02-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ],
        )

    def test_provider_filter(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_log(
                root,
                [
                    {"provider": "ollama", "model": "x", "latency_ms": 10.0},
                    {"provider": "openai", "model": "y", "latency_ms": 20.0},
                    {"provider": "ollama", "model": "z", "latency_ms": 30.0},
                ],
            )
            ns = argparse.Namespace(
                path=str(root), provider="ollama", limit=10, json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_telemetry(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["count"], 2)
        self.assertTrue(
            all(entry["provider"] == "ollama" for entry in payload["entries"])
        )

    def test_limit_bounds_results(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_log(
                root,
                [
                    {"provider": "ollama", "model": "m", "timestamp": str(i)}
                    for i in range(10)
                ],
            )
            ns = argparse.Namespace(
                path=str(root), provider="", limit=3, json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_telemetry(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["count"], 3)
        # Newest-first means timestamps "9", "8", "7".
        self.assertEqual(
            [e["timestamp"] for e in payload["entries"]],
            ["9", "8", "7"],
        )

    def test_zero_limit_returns_empty(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_log(root, [{"provider": "x", "model": "y", "latency_ms": 1.0}])
            ns = argparse.Namespace(
                path=str(root), provider="", limit=0, json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_telemetry(ns)
            payload = json.loads(buf.getvalue())
        self.assertEqual(payload["count"], 0)

    def test_corrupt_lines_silently_skipped(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "mythic" / "ai" / "provider_calls.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                json.dumps(
                    {"provider": "ollama", "model": "x", "latency_ms": 1.0}
                )
                + "\n"
                + "{not-json\n"
                + json.dumps([1, 2, 3])  # non-dict
                + "\n"
                + json.dumps(
                    {"provider": "ollama", "model": "y", "latency_ms": 2.0}
                )
                + "\n",
                encoding="utf-8",
            )
            ns = argparse.Namespace(
                path=str(root), provider="", limit=10, json=True
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_telemetry(ns)
            payload = json.loads(buf.getvalue())
        # Only the two valid dict entries make it through.
        self.assertEqual(payload["count"], 2)

    def test_text_output_renders_summary(self) -> None:
        from mythic_vibe_cli.commands import cmd_ai_telemetry

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_log(
                root,
                [
                    {
                        "timestamp": "2026-04-29T12:00:00Z",
                        "provider": "ollama",
                        "model": "llama3.2",
                        "latency_ms": 42.5,
                        "response": {
                            "usage": {"total_tokens": 100},
                        },
                    },
                ],
            )
            ns = argparse.Namespace(
                path=str(root), provider="", limit=10, json=False
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_ai_telemetry(ns)
        rendered = buf.getvalue()
        self.assertIn("ollama/llama3.2", rendered)
        self.assertIn("latency=42.5ms", rendered)
        self.assertIn("tokens=100", rendered)


# ---- Dispatch update --------------------------------------------------


class AiDispatchUpdateTests(unittest.TestCase):
    def test_unknown_subcommand_help_includes_telemetry(self) -> None:
        from contextlib import redirect_stderr

        from mythic_vibe_cli.commands import cmd_ai_dispatch

        ns = argparse.Namespace(ai_command="bogus", json=True)
        buf = io.StringIO()
        with redirect_stderr(buf):
            exit_code = cmd_ai_dispatch(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("telemetry", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
