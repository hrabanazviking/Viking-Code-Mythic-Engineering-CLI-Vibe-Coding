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


if __name__ == "__main__":
    unittest.main()
