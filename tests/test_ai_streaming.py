"""Tests for PH-06 Slice 6.4 — streaming contract + cancellation.

Step 1 covers the typed StreamChunk + StreamingProvider Protocol
+ single_chunk_stream / stream_provider_response shortcuts.
"""

from __future__ import annotations

import threading
import unittest

from mythic_vibe_cli.ai.providers.base import (
    ProviderResponse,
    StreamChunk,
    StreamingProvider,
    single_chunk_stream,
    stream_provider_response,
)


class _FakeNonStreamingProvider:
    """Mimics the AIProvider Protocol without ``run_stream``. Used
    to drive the single_chunk_stream fallback path."""

    name = "fake-nonstream"

    def __init__(self, *, content: str = "ok", usage: dict | None = None) -> None:
        self._content = content
        self._usage = usage or {"input_tokens": 1, "output_tokens": 1}

    def validate_config(self):  # pragma: no cover — unused in these tests
        from mythic_vibe_cli.ai.providers.base import ProviderStatus
        return ProviderStatus(configured=True, details=[])

    def estimate(self, packet):  # pragma: no cover — unused
        from mythic_vibe_cli.ai.providers.base import Estimate
        return Estimate(input_tokens=1, output_tokens=1)

    def run(self, packet, *, dry_run=False):
        return ProviderResponse(
            provider=self.name,
            model="test",
            content=self._content,
            packet_id="PKT-X",
            dry_run=dry_run,
            usage=self._usage,
            metadata={"source": "test"},
        )


class _FakeStreamingProvider:
    """Mimics a streaming provider with run_stream emitting
    multiple chunks before a terminal done=True chunk."""

    name = "fake-stream"

    def __init__(self, *, chunks: list[str]) -> None:
        self._chunks = list(chunks)

    def validate_config(self):  # pragma: no cover
        from mythic_vibe_cli.ai.providers.base import ProviderStatus
        return ProviderStatus(configured=True, details=[])

    def estimate(self, packet):  # pragma: no cover
        from mythic_vibe_cli.ai.providers.base import Estimate
        return Estimate(input_tokens=1, output_tokens=1)

    def run(self, packet, *, dry_run=False):  # pragma: no cover
        return ProviderResponse(
            provider=self.name,
            model="test",
            content="".join(self._chunks),
            packet_id="PKT-X",
            dry_run=dry_run,
        )

    def run_stream(self, packet, *, dry_run=False, cancel_event=None):
        for piece in self._chunks:
            if cancel_event is not None and cancel_event.is_set():
                yield StreamChunk(
                    text="",
                    done=True,
                    metadata={"cancelled": True, "source": "fake-stream"},
                )
                return
            yield StreamChunk(text=piece, done=False)
        yield StreamChunk(
            text="",
            done=True,
            usage={"input_tokens": 5, "output_tokens": 10},
            metadata={"source": "fake-stream"},
        )


# ---- StreamChunk -----------------------------------------------------


class StreamChunkTests(unittest.TestCase):
    def test_default_chunk(self) -> None:
        chunk = StreamChunk()
        self.assertEqual(chunk.text, "")
        self.assertFalse(chunk.done)
        self.assertEqual(chunk.usage, {})
        self.assertEqual(chunk.metadata, {})

    def test_to_dict_round_trip(self) -> None:
        chunk = StreamChunk(
            text="hi",
            done=True,
            usage={"input_tokens": 3},
            metadata={"k": "v"},
        )
        payload = chunk.to_dict()
        self.assertEqual(payload["text"], "hi")
        self.assertTrue(payload["done"])
        self.assertEqual(payload["usage"], {"input_tokens": 3})
        self.assertEqual(payload["metadata"], {"k": "v"})


# ---- StreamingProvider Protocol --------------------------------------


class StreamingProviderProtocolTests(unittest.TestCase):
    def test_streaming_provider_runtime_checkable(self) -> None:
        self.assertTrue(
            isinstance(_FakeStreamingProvider(chunks=["a"]), StreamingProvider)
        )

    def test_non_streaming_provider_not_streaming(self) -> None:
        self.assertFalse(
            isinstance(_FakeNonStreamingProvider(), StreamingProvider)
        )


# ---- single_chunk_stream ---------------------------------------------


class SingleChunkStreamTests(unittest.TestCase):
    def test_emits_exactly_one_terminal_chunk(self) -> None:
        provider = _FakeNonStreamingProvider(content="hello")
        chunks = list(single_chunk_stream(provider, "packet"))
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].done)
        self.assertEqual(chunks[0].text, "hello")

    def test_chunk_carries_usage_from_run(self) -> None:
        provider = _FakeNonStreamingProvider(
            usage={"input_tokens": 7, "output_tokens": 11}
        )
        chunks = list(single_chunk_stream(provider, "packet"))
        self.assertEqual(chunks[0].usage["input_tokens"], 7)
        self.assertEqual(chunks[0].usage["output_tokens"], 11)

    def test_metadata_includes_wrapping_marker(self) -> None:
        provider = _FakeNonStreamingProvider()
        chunks = list(single_chunk_stream(provider, "packet"))
        self.assertEqual(chunks[0].metadata["source"], "single_chunk_stream")
        self.assertEqual(
            chunks[0].metadata["wraps_provider"], "fake-nonstream"
        )

    def test_pre_set_cancel_event_short_circuits(self) -> None:
        provider = _FakeNonStreamingProvider()
        event = threading.Event()
        event.set()
        chunks = list(
            single_chunk_stream(provider, "packet", cancel_event=event)
        )
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].done)
        self.assertEqual(chunks[0].text, "")
        self.assertTrue(chunks[0].metadata["cancelled"])

    def test_dry_run_passthrough(self) -> None:
        provider = _FakeNonStreamingProvider()
        chunks = list(single_chunk_stream(provider, "packet", dry_run=True))
        # Provider's run propagated dry_run; metadata may include it.
        self.assertEqual(chunks[0].text, "ok")  # default content


# ---- stream_provider_response ----------------------------------------


class StreamProviderResponseTests(unittest.TestCase):
    def test_routes_through_native_streaming_when_available(self) -> None:
        provider = _FakeStreamingProvider(chunks=["A", "B", "C"])
        chunks = list(stream_provider_response(provider, "packet"))
        # 3 token chunks + 1 terminal chunk.
        self.assertEqual(len(chunks), 4)
        self.assertEqual(
            "".join(c.text for c in chunks if not c.done),
            "ABC",
        )
        self.assertTrue(chunks[-1].done)

    def test_falls_back_to_single_chunk_for_non_streaming(self) -> None:
        provider = _FakeNonStreamingProvider(content="full")
        chunks = list(stream_provider_response(provider, "packet"))
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].done)
        self.assertEqual(chunks[0].text, "full")

    def test_cancellation_mid_stream(self) -> None:
        provider = _FakeStreamingProvider(chunks=["A", "B", "C", "D"])
        event = threading.Event()
        chunks: list[StreamChunk] = []
        for idx, chunk in enumerate(
            stream_provider_response(provider, "packet", cancel_event=event)
        ):
            chunks.append(chunk)
            if idx == 1:  # set cancel after the second chunk
                event.set()
            if chunk.done:
                break
        # We should see A, B, then the cancellation terminal chunk.
        self.assertEqual(chunks[0].text, "A")
        self.assertEqual(chunks[1].text, "B")
        self.assertTrue(chunks[-1].done)
        self.assertTrue(chunks[-1].metadata.get("cancelled", False))


# ---- Ollama native streaming -----------------------------------------


class _FakeHttpResponse:
    """Stand-in for the urllib HTTP response object — feeds NDJSON
    lines via readline() the same way the real Ollama daemon does."""

    def __init__(self, lines: list[bytes]) -> None:
        self._lines = list(lines)
        self.closed = False

    def readline(self) -> bytes:
        if not self._lines:
            return b""
        return self._lines.pop(0)

    def close(self) -> None:
        self.closed = True


class OllamaStreamingTests(unittest.TestCase):
    """Wire the Ollama provider's run_stream against a fake HTTP
    response so we don't need a live daemon in CI."""

    def _fake_health(self):
        from mythic_vibe_cli.ai.ollama_health import OllamaHealth

        return OllamaHealth(
            reachable=True,
            endpoint="http://localhost:11434",
            latency_ms=1.0,
            error="",
            details=["fake daemon up"],
        )

    def _build_ndjson_response(
        self, *, chunks: list[str], usage: dict
    ) -> _FakeHttpResponse:
        import json as _json

        lines: list[bytes] = []
        for delta in chunks:
            lines.append(
                (_json.dumps({"response": delta, "done": False}) + "\n").encode("utf-8")
            )
        terminal = {
            "response": "",
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": usage.get("input_tokens", 1),
            "eval_count": usage.get("output_tokens", 3),
            "total_duration": 1_234,
            "load_duration": 456,
            "eval_duration": 789,
        }
        lines.append((_json.dumps(terminal) + "\n").encode("utf-8"))
        lines.append(b"")  # EOF
        return _FakeHttpResponse(lines)

    def test_streams_tokens_then_terminal_chunk(self) -> None:
        from unittest import mock
        from mythic_vibe_cli.ai.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        fake_response = self._build_ndjson_response(
            chunks=["Hel", "lo ", "world"],
            usage={"input_tokens": 4, "output_tokens": 9},
        )

        with mock.patch(
            "mythic_vibe_cli.ai.providers.ollama.check_ollama_health",
            return_value=self._fake_health(),
        ):
            with mock.patch(
                "urllib.request.urlopen", return_value=fake_response
            ):
                chunks = list(provider.run_stream("hello"))

        # 3 token chunks (Hel / lo / world) + 1 terminal.
        self.assertEqual(len(chunks), 4)
        self.assertEqual(
            "".join(c.text for c in chunks if not c.done),
            "Hello world",
        )
        terminal = chunks[-1]
        self.assertTrue(terminal.done)
        self.assertEqual(terminal.usage["input_tokens"], 4)
        self.assertEqual(terminal.usage["output_tokens"], 9)
        self.assertFalse(terminal.metadata.get("cancelled", False))
        self.assertTrue(fake_response.closed)

    def test_dry_run_emits_single_terminal_chunk(self) -> None:
        from mythic_vibe_cli.ai.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        chunks = list(provider.run_stream("hello", dry_run=True))
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].done)
        self.assertEqual(chunks[0].text, "hello")
        self.assertTrue(chunks[0].metadata["dry_run"])

    def test_pre_set_cancel_event_short_circuits(self) -> None:
        from mythic_vibe_cli.ai.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        event = threading.Event()
        event.set()
        chunks = list(provider.run_stream("hello", cancel_event=event))
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].done)
        self.assertTrue(chunks[0].metadata["cancelled"])

    def test_cancellation_mid_stream_closes_response(self) -> None:
        """Set the cancel event after the first chunk; the loop
        should stop and the http response close cleanly."""
        from unittest import mock
        from mythic_vibe_cli.ai.providers.ollama import OllamaProvider

        provider = OllamaProvider()
        event = threading.Event()
        fake_response = self._build_ndjson_response(
            chunks=["A", "B", "C", "D"],
            usage={"input_tokens": 1, "output_tokens": 4},
        )

        with mock.patch(
            "mythic_vibe_cli.ai.providers.ollama.check_ollama_health",
            return_value=self._fake_health(),
        ):
            with mock.patch(
                "urllib.request.urlopen", return_value=fake_response
            ):
                chunks: list[StreamChunk] = []
                for idx, chunk in enumerate(
                    provider.run_stream("hello", cancel_event=event)
                ):
                    chunks.append(chunk)
                    if idx == 0:
                        event.set()
                    if chunk.done:
                        break

        # First chunk landed; terminal chunk reports cancelled=True.
        self.assertEqual(chunks[0].text, "A")
        self.assertTrue(chunks[-1].done)
        self.assertTrue(chunks[-1].metadata["cancelled"])
        self.assertTrue(fake_response.closed)

    def test_unreachable_daemon_raises_connection_error(self) -> None:
        from unittest import mock
        from mythic_vibe_cli.ai.providers.ollama import OllamaProvider
        from mythic_vibe_cli.ai.ollama_health import OllamaHealth

        provider = OllamaProvider()
        unreachable = OllamaHealth(
            reachable=False,
            endpoint="http://localhost:11434",
            latency_ms=0.0,
            error="connection refused",
            details=[],
        )
        with mock.patch(
            "mythic_vibe_cli.ai.providers.ollama.check_ollama_health",
            return_value=unreachable,
        ):
            with self.assertRaises(ConnectionError) as ctx:
                # Have to consume the generator to trigger the call.
                list(provider.run_stream("hello"))
        self.assertIn("Ollama daemon unreachable", str(ctx.exception))

    def test_streaming_provider_protocol_membership(self) -> None:
        """OllamaProvider should now satisfy the StreamingProvider
        Protocol (has run_stream + name)."""
        from mythic_vibe_cli.ai.providers.ollama import OllamaProvider

        self.assertTrue(isinstance(OllamaProvider(), StreamingProvider))


# ---- cmd_ai_stream ---------------------------------------------------


class CmdAiStreamTests(unittest.TestCase):
    """End-to-end coverage for the new `mythic-vibe ai stream`
    handler. We mock the registry so tests don't need a live
    Ollama daemon."""

    def _run_with_provider(
        self, provider, *, json_mode: bool = False, dry_run: bool = False
    ):
        import argparse
        import io
        from contextlib import redirect_stdout
        from unittest import mock

        from mythic_vibe_cli import commands as cmd_module

        ns = argparse.Namespace(
            path=".",
            provider=provider.name,
            packet="hello",
            json=json_mode,
            dry_run=dry_run,
        )

        class _FakeRegistry:
            def __init__(self, p):
                self._p = p

            def providers(self):
                return {self._p.name: self._p}

        registry = _FakeRegistry(provider)
        buf = io.StringIO()
        with mock.patch.object(cmd_module, "_ai_registry", return_value=registry):
            with redirect_stdout(buf):
                exit_code = cmd_module.cmd_ai_stream(ns)
        return exit_code, buf.getvalue()

    def test_streaming_provider_renders_chunks_inline(self) -> None:
        provider = _FakeStreamingProvider(chunks=["Hel", "lo ", "world"])
        exit_code, output = self._run_with_provider(provider)
        from mythic_vibe_cli.exit_codes import SUCCESS

        self.assertEqual(exit_code, SUCCESS)
        # Chunks rendered concatenated in stdout.
        self.assertIn("Hello world", output)
        # Stream summary trailer present.
        self.assertIn("Stream summary", output)
        self.assertIn("Provider", output)

    def test_non_streaming_provider_uses_single_chunk_fallback(self) -> None:
        provider = _FakeNonStreamingProvider(content="full body")
        exit_code, output = self._run_with_provider(provider)
        from mythic_vibe_cli.exit_codes import SUCCESS

        self.assertEqual(exit_code, SUCCESS)
        self.assertIn("full body", output)

    def test_json_mode_emits_ndjson(self) -> None:
        import json as _json

        provider = _FakeStreamingProvider(chunks=["A", "B"])
        exit_code, output = self._run_with_provider(provider, json_mode=True)
        from mythic_vibe_cli.exit_codes import SUCCESS

        self.assertEqual(exit_code, SUCCESS)
        # NDJSON: one parseable JSON object per non-empty line.
        lines = [_json.loads(line) for line in output.splitlines() if line.strip()]
        self.assertGreaterEqual(len(lines), 3)  # 2 token + 1 terminal
        # Last chunk has done=True.
        self.assertTrue(lines[-1]["done"])

    def test_unknown_provider_returns_user_input_error(self) -> None:
        import argparse
        import io
        from contextlib import redirect_stderr
        from unittest import mock

        from mythic_vibe_cli import commands as cmd_module
        from mythic_vibe_cli.exit_codes import USER_INPUT_ERROR

        ns = argparse.Namespace(
            path=".",
            provider="ghost",
            packet="hello",
            json=False,
            dry_run=False,
        )

        class _EmptyRegistry:
            def providers(self):
                return {}

        with mock.patch.object(
            cmd_module, "_ai_registry", return_value=_EmptyRegistry()
        ):
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                exit_code = cmd_module.cmd_ai_stream(ns)
        self.assertEqual(exit_code, USER_INPUT_ERROR)
        self.assertIn("Unknown provider", stderr.getvalue())


class CmdAiStreamArgparseTests(unittest.TestCase):
    def test_stream_subcommand_parses(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(
            ["ai", "stream", "--provider", "copy-paste", "--packet", "hi"]
        )
        self.assertEqual(ns.command, "ai")
        self.assertEqual(ns.ai_command, "stream")
        self.assertEqual(ns.provider, "copy-paste")
        self.assertEqual(ns.packet, "hi")


if __name__ == "__main__":
    unittest.main()
