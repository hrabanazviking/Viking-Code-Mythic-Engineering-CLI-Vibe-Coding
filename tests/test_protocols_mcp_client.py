"""Tests for PH-16 Slice 16.2 — MCP client."""

from __future__ import annotations

import io
import json
import threading
import unittest

from mythic_vibe_cli.protocols.mcp_client import McpClient, McpClientError


class _LoopbackPipe:
    """Two paired StringIO-like objects connected by a queue.
    Lets us drive the McpClient against an in-process fake server
    without spawning a subprocess."""

    def __init__(self) -> None:
        self._inbound: list[str] = []
        self._outbound: list[str] = []
        self._cv = threading.Condition()


def _make_streams() -> tuple[io.StringIO, io.StringIO, io.StringIO, io.StringIO]:
    """Return (client_stdin, client_stdout, server_stdin, server_stdout).

    For tests we drive the conversation manually — the client
    writes to client_stdin (server reads from it) and reads from
    client_stdout (server writes to it).
    """
    client_to_server = io.StringIO()
    server_to_client = io.StringIO()
    return client_to_server, server_to_client, server_to_client, client_to_server


class _RewindableStream(io.StringIO):
    """Helper StringIO that lets us rewind the read pointer after
    each test write so the client can readline() what the fake
    server pushed."""


def _push_response(stream: _RewindableStream, payload: dict) -> None:
    pos = stream.tell()
    stream.seek(0, io.SEEK_END)
    stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    stream.seek(pos)


class McpClientCallTests(unittest.TestCase):
    def _build(self) -> tuple[McpClient, _RewindableStream, _RewindableStream]:
        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)
        return client, client_in, client_out

    def test_call_returns_result(self) -> None:
        client, client_in, client_out = self._build()
        # Pre-load the response.
        _push_response(
            client_out,
            {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}},
        )
        result = client.call("ping")
        self.assertEqual(result, {"ok": True})
        # Client wrote the request to client_in.
        client_in.seek(0)
        sent = json.loads(client_in.readline())
        self.assertEqual(sent["method"], "ping")
        self.assertEqual(sent["id"], 1)
        self.assertEqual(sent["jsonrpc"], "2.0")

    def test_call_with_params(self) -> None:
        client, client_in, client_out = self._build()
        _push_response(
            client_out,
            {"jsonrpc": "2.0", "id": 1, "result": "ok"},
        )
        client.call("tools/call", params={"name": "x"})
        client_in.seek(0)
        sent = json.loads(client_in.readline())
        self.assertEqual(sent["params"], {"name": "x"})

    def test_call_skips_unrelated_responses(self) -> None:
        client, _client_in, client_out = self._build()
        # Server emits an unrelated id=99 response first, then
        # the id=1 response we're waiting on.
        _push_response(client_out, {"jsonrpc": "2.0", "id": 99, "result": "noise"})
        _push_response(client_out, {"jsonrpc": "2.0", "id": 1, "result": "match"})
        result = client.call("ping")
        self.assertEqual(result, "match")

    def test_error_response_raises(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32601, "message": "method not found"},
            },
        )
        with self.assertRaises(McpClientError) as ctx:
            client.call("ghost")
        self.assertIn("method not found", str(ctx.exception))

    def test_server_closed_stdout_raises(self) -> None:
        client, _client_in, client_out = self._build()
        # No response loaded — readline returns empty string.
        with self.assertRaises(McpClientError) as ctx:
            client.call("ping")
        self.assertIn("closed stdout", str(ctx.exception))

    def test_invalid_json_raises(self) -> None:
        client, _client_in, client_out = self._build()
        client_out.write("this is not json\n")
        client_out.seek(0)
        with self.assertRaises(McpClientError) as ctx:
            client.call("ping")
        self.assertIn("invalid JSON", str(ctx.exception))


class McpClientNotifyTests(unittest.TestCase):
    def test_notify_sends_no_id(self) -> None:
        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)
        client.notify("notifications/initialized")
        client_in.seek(0)
        sent = json.loads(client_in.readline())
        self.assertEqual(sent["method"], "notifications/initialized")
        self.assertNotIn("id", sent)


class McpClientHighLevelTests(unittest.TestCase):
    def test_initialize_sends_handshake_then_notify(self) -> None:
        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)
        _push_response(
            client_out,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "x", "version": "1.0"},
                    "capabilities": {},
                },
            },
        )
        info = client.initialize()
        self.assertEqual(info["serverInfo"]["name"], "x")
        # Two messages sent: initialize request + post-init notification.
        client_in.seek(0)
        lines = [
            line for line in client_in.read().splitlines() if line.strip()
        ]
        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        second = json.loads(lines[1])
        self.assertEqual(first["method"], "initialize")
        self.assertEqual(second["method"], "notifications/initialized")
        self.assertNotIn("id", second)

    def test_list_tools_returns_array(self) -> None:
        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)
        _push_response(
            client_out,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "tools": [
                        {"name": "a", "description": "A"},
                        {"name": "b", "description": "B"},
                    ]
                },
            },
        )
        tools = client.list_tools()
        self.assertEqual(len(tools), 2)

    def test_call_tool_envelope(self) -> None:
        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)
        _push_response(
            client_out,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "isError": False,
                    "content": [{"type": "text", "text": "hello"}],
                },
            },
        )
        result = client.call_tool("mythic_vibe.status", arguments={"argv": []})
        self.assertEqual(result["isError"], False)


# ---- Phase 19.0 / BS-2 (audit remediation 2026-05-02) ----------------
#
# Hang-protection regression tests. Without these bounds, a stalled
# server (no lines on stdout) hangs the calling thread on
# readline() forever; a notification-spamming server spins the
# discard loop in call() forever. The new bounds close both vectors.


class ReadTimeoutTests(unittest.TestCase):
    """`_read_one` raises `McpClientError` after
    `read_timeout_seconds` of no data, instead of blocking forever."""

    def test_call_times_out_when_server_stdout_silent(self) -> None:
        import io
        import threading

        from mythic_vibe_cli.protocols.mcp_client import (
            McpClient,
            McpClientError,
        )

        # Custom stream-like whose readline() blocks until ``close()``
        # is called (or forever if it isn't). This is more reliable
        # than os.pipe across platforms — Windows in particular has
        # quirks around closing a pipe FD while another thread is
        # blocked in readline. Here, close() unblocks the reader
        # thread cooperatively.
        class _BlockingStdout:
            def __init__(self) -> None:
                self._closed = threading.Event()

            def readline(self) -> str:
                self._closed.wait()
                return ""  # EOF when closed

            def close(self) -> None:
                self._closed.set()

        stub = _BlockingStdout()
        client = McpClient.from_streams(
            stdin=io.StringIO(),
            stdout=stub,  # type: ignore[arg-type]
            read_timeout_seconds=0.3,  # tight bound for fast test
            max_discard=10,
        )
        try:
            with self.assertRaises(McpClientError) as ctx:
                client.call("anything")
            self.assertIn("timed out", str(ctx.exception).lower())
            self.assertIn("0.3", str(ctx.exception))
        finally:
            stub.close()  # unblock the reader thread before close
            client.close()

    def test_legacy_zero_timeout_preserves_unbounded_readline(self) -> None:
        """Setting read_timeout_seconds=0.0 opts back into the
        pre-Phase-19 behaviour: no reader thread is started, and
        ``_read_one`` calls readline directly. With a stream that
        EOFs immediately, this surfaces as "server closed stdout"
        rather than a timeout — proving the legacy path is in use."""
        import io

        from mythic_vibe_cli.protocols.mcp_client import (
            McpClient,
            McpClientError,
        )

        client = McpClient.from_streams(
            stdin=io.StringIO(),
            stdout=io.StringIO(""),  # EOF immediately
            read_timeout_seconds=0.0,
        )
        with self.assertRaises(McpClientError) as ctx:
            client.call("anything")
        # Legacy path raises "server closed stdout" — NOT "timed out".
        self.assertIn("closed stdout", str(ctx.exception).lower())
        self.assertNotIn("timed out", str(ctx.exception).lower())


class DiscardLoopBoundTests(unittest.TestCase):
    """``call()`` raises after `max_discard` non-matching messages,
    instead of spinning forever on a notification-spamming server."""

    def test_call_aborts_after_max_discard_unrelated_messages(self) -> None:
        import io
        import json

        from mythic_vibe_cli.protocols.mcp_client import (
            McpClient,
            McpClientError,
        )

        # Stream of 50 unrelated responses (id 9999) — never matches
        # the request id, so the discard loop walks all of them.
        spam_lines = "\n".join(
            json.dumps({"jsonrpc": "2.0", "id": 9999, "result": "ignored"})
            for _ in range(50)
        ) + "\n"
        client = McpClient.from_streams(
            stdin=io.StringIO(),
            stdout=io.StringIO(spam_lines),
            read_timeout_seconds=2.0,  # plenty of slack so timeout doesn't fire first
            max_discard=10,
        )
        with self.assertRaises(McpClientError) as ctx:
            client.call("anything")
        msg = str(ctx.exception).lower()
        self.assertIn("discarded", msg)
        self.assertIn("10", str(ctx.exception))  # max_discard value
        client.close()

    def test_legitimate_response_still_returns_after_some_discards(
        self,
    ) -> None:
        """Servers legitimately interleave notifications with
        responses. Make sure a real response found within the
        max_discard budget still returns successfully."""
        import io
        import json

        from mythic_vibe_cli.protocols.mcp_client import McpClient

        # 5 notifications then the actual response (id will be 1
        # since itertools.count starts at 1 — see _id_counter).
        lines = []
        for i in range(5):
            lines.append(
                json.dumps({"jsonrpc": "2.0", "method": f"notification.{i}"})
            )
        lines.append(
            json.dumps({"jsonrpc": "2.0", "id": 1, "result": "found-it"})
        )
        client = McpClient.from_streams(
            stdin=io.StringIO(),
            stdout=io.StringIO("\n".join(lines) + "\n"),
            read_timeout_seconds=2.0,
            max_discard=100,  # well above 5
        )
        result = client.call("anything")
        self.assertEqual(result, "found-it")
        client.close()


class EnvVarConfigTests(unittest.TestCase):
    """The default field factories read MYTHIC_MCP_READ_TIMEOUT and
    MYTHIC_MCP_MAX_DISCARD env vars so operators can tune without
    code changes."""

    def test_env_var_overrides_default_read_timeout(self) -> None:
        import io
        from unittest import mock

        from mythic_vibe_cli.protocols.mcp_client import McpClient

        with mock.patch.dict(
            "os.environ", {"MYTHIC_MCP_READ_TIMEOUT": "5.5"}, clear=False
        ):
            client = McpClient.from_streams(
                stdin=io.StringIO(), stdout=io.StringIO()
            )
        self.assertEqual(client.read_timeout_seconds, 5.5)

    def test_env_var_overrides_default_max_discard(self) -> None:
        import io
        from unittest import mock

        from mythic_vibe_cli.protocols.mcp_client import McpClient

        with mock.patch.dict(
            "os.environ", {"MYTHIC_MCP_MAX_DISCARD": "42"}, clear=False
        ):
            client = McpClient.from_streams(
                stdin=io.StringIO(), stdout=io.StringIO()
            )
        self.assertEqual(client.max_discard, 42)

    def test_invalid_env_var_falls_back_to_default(self) -> None:
        import io
        from unittest import mock
        from mythic_vibe_cli.protocols.mcp_client import (
            McpClient,
            DEFAULT_READ_TIMEOUT_SECONDS,
            DEFAULT_MAX_DISCARD,
        )

        with mock.patch.dict(
            "os.environ",
            {
                "MYTHIC_MCP_READ_TIMEOUT": "not-a-float",
                "MYTHIC_MCP_MAX_DISCARD": "not-an-int",
            },
            clear=False,
        ):
            client = McpClient.from_streams(
                stdin=io.StringIO(), stdout=io.StringIO()
            )
        self.assertEqual(
            client.read_timeout_seconds, DEFAULT_READ_TIMEOUT_SECONDS
        )
        self.assertEqual(client.max_discard, DEFAULT_MAX_DISCARD)


# ---------------------------------------------------------------------------
# PH-26.1 coverage push — exercise the high-level convenience methods
# (initialize / list_tools / call_tool with non-dict / non-list responses)
# + close() lifecycle paths. Goal: take ``protocols/mcp_client.py`` from
# 78% to 90%+.
# ---------------------------------------------------------------------------


class McpClientSpawnValidationTests(unittest.TestCase):
    def test_spawn_rejects_empty_argv(self) -> None:
        with self.assertRaises(ValueError) as cm:
            McpClient.spawn([])
        self.assertIn("argv must contain", str(cm.exception))


class McpClientHighLevelCoverageTests(unittest.TestCase):
    """Cover initialize / list_tools / call_tool happy + sad paths.
    Existing tests focus on call() — these cover the convenience layer."""

    def _build(self) -> tuple[McpClient, _RewindableStream, _RewindableStream]:
        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)
        return client, client_in, client_out

    def test_initialize_returns_dict_and_sends_initialized_notification(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out,
            {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "fake"}}},
        )
        result = client.initialize()
        self.assertEqual(result, {"serverInfo": {"name": "fake"}})

    def test_initialize_raises_when_result_not_dict(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out,
            {"jsonrpc": "2.0", "id": 1, "result": ["not", "a", "dict"]},
        )
        with self.assertRaises(McpClientError) as cm:
            client.initialize()
        self.assertIn("initialize", str(cm.exception))

    def test_list_tools_returns_filtered_list(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out,
            {
                "jsonrpc": "2.0", "id": 1,
                "result": {
                    "tools": [
                        {"name": "ok-tool"},
                        "not-a-dict-skip",  # filtered out
                        {"name": "another"},
                    ]
                },
            },
        )
        tools = client.list_tools()
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0]["name"], "ok-tool")

    def test_list_tools_raises_when_result_not_dict(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out, {"jsonrpc": "2.0", "id": 1, "result": "scalar"}
        )
        with self.assertRaises(McpClientError) as cm:
            client.list_tools()
        self.assertIn("tools/list", str(cm.exception))

    def test_list_tools_raises_when_tools_missing_array(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out,
            {"jsonrpc": "2.0", "id": 1, "result": {"tools": "not-a-list"}},
        )
        with self.assertRaises(McpClientError) as cm:
            client.list_tools()
        self.assertIn("tools array", str(cm.exception))

    def test_call_tool_returns_dict_result(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out,
            {
                "jsonrpc": "2.0", "id": 1,
                "result": {"content": [{"type": "text", "text": "ok"}]},
            },
        )
        result = client.call_tool("get_weather", arguments={"city": "Oslo"})
        self.assertEqual(result["content"][0]["text"], "ok")

    def test_call_tool_raises_when_result_not_dict(self) -> None:
        client, _client_in, client_out = self._build()
        _push_response(
            client_out, {"jsonrpc": "2.0", "id": 1, "result": "not-a-dict"}
        )
        with self.assertRaises(McpClientError) as cm:
            client.call_tool("foo")
        self.assertIn("tools/call", str(cm.exception))

    def test_notify_writes_payload_without_id(self) -> None:
        client, client_in, _client_out = self._build()
        client.notify("custom/notification", params={"k": "v"})
        # Read what the client actually wrote.
        client_in.seek(0)
        line = client_in.readline()
        payload = json.loads(line)
        self.assertEqual(payload["method"], "custom/notification")
        self.assertNotIn("id", payload)
        self.assertEqual(payload["params"], {"k": "v"})

    def test_notify_omits_params_when_none(self) -> None:
        client, client_in, _client_out = self._build()
        client.notify("ping")
        client_in.seek(0)
        line = client_in.readline()
        payload = json.loads(line)
        self.assertEqual(payload["method"], "ping")
        self.assertNotIn("params", payload)


class McpClientCloseTests(unittest.TestCase):
    """Cover the close() lifecycle — stdin/stdout swallow, process
    wait+kill, reader-thread join."""

    def test_close_swallows_stdin_close_errors(self) -> None:
        from unittest import mock

        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)

        with mock.patch.object(client_in, "close", side_effect=OSError("simulated")):
            client.close()  # must not raise

    def test_close_swallows_stdout_close_errors(self) -> None:
        from unittest import mock

        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)

        with mock.patch.object(client_out, "close", side_effect=ValueError("simulated")):
            client.close()  # must not raise

    def test_close_kills_process_on_wait_timeout(self) -> None:
        """If process.wait() times out, close() should call kill()."""
        from unittest import mock
        import subprocess as _sp

        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)

        fake_proc = mock.MagicMock()
        fake_proc.wait.side_effect = _sp.TimeoutExpired(cmd="x", timeout=2.0)
        client.process = fake_proc

        client.close()
        fake_proc.kill.assert_called_once()

    def test_close_swallows_oserror_on_process_wait(self) -> None:
        from unittest import mock

        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)

        fake_proc = mock.MagicMock()
        fake_proc.wait.side_effect = OSError("simulated")
        client.process = fake_proc

        client.close()  # must not raise

    def test_context_manager_calls_close_on_exit(self) -> None:
        from unittest import mock

        client_in = _RewindableStream()
        client_out = _RewindableStream()
        client = McpClient.from_streams(stdin=client_in, stdout=client_out)

        with mock.patch.object(client, "close") as close_mock:
            with client:
                pass
        close_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
