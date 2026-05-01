"""Tests for PH-16 Slice 16.1 — MCP server."""

from __future__ import annotations

import io
import json
import unittest

from mythic_vibe_cli.protocols.mcp_server import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    PARSE_ERROR,
    PROTOCOL_VERSION,
    SERVER_NAME,
    McpServer,
    run_stdio_server,
)
from mythic_vibe_cli.protocols.mcp_tools import (
    McpTool,
    build_tool_catalogue,
)


class McpToolDataclassTests(unittest.TestCase):
    def test_to_dict_uses_camel_case_input_schema(self) -> None:
        tool = McpTool(
            name="x",
            description="...",
            input_schema={"type": "object"},
        )
        payload = tool.to_dict()
        self.assertEqual(payload["name"], "x")
        # MCP spec uses camelCase; we expose `inputSchema`.
        self.assertIn("inputSchema", payload)


class BuildToolCatalogueTests(unittest.TestCase):
    def test_catalogue_non_empty(self) -> None:
        tools = build_tool_catalogue()
        self.assertGreater(len(tools), 10)

    def test_each_tool_has_mythic_vibe_prefix(self) -> None:
        tools = build_tool_catalogue()
        for tool in tools:
            self.assertTrue(
                tool.name.startswith("mythic_vibe."),
                f"tool {tool.name!r} missing prefix",
            )

    def test_aliases_excluded(self) -> None:
        names = {t.name for t in build_tool_catalogue()}
        # `start` / `imbue` / `evoke` / `scry` are aliases per the
        # PH-02 slice 2.1 invariant; only canonical names appear.
        self.assertNotIn("mythic_vibe.start", names)
        self.assertNotIn("mythic_vibe.imbue", names)
        self.assertIn("mythic_vibe.init", names)


# ---- McpServer dispatch ----------------------------------------------


class McpServerInitializeTests(unittest.TestCase):
    def test_initialize_returns_protocol_version(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {},
            }
        )
        self.assertIsNotNone(response)
        assert response is not None
        self.assertEqual(response["id"], 1)
        result = response["result"]
        self.assertEqual(result["protocolVersion"], PROTOCOL_VERSION)
        self.assertEqual(result["serverInfo"]["name"], SERVER_NAME)
        self.assertIn("tools", result["capabilities"])
        self.assertTrue(server.initialized)

    def test_notifications_initialized_returns_none(self) -> None:
        server = McpServer()
        # Notification (no `id`).
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
        )
        self.assertIsNone(response)


class McpServerToolsListTests(unittest.TestCase):
    def test_tools_list_returns_catalogue(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        assert response is not None
        tools = response["result"]["tools"]
        self.assertGreater(len(tools), 10)
        self.assertTrue(tools[0]["name"].startswith("mythic_vibe."))


class McpServerToolsCallTests(unittest.TestCase):
    def test_call_status_in_temp_project(self) -> None:
        import tempfile

        server = McpServer()
        with tempfile.TemporaryDirectory() as tmp:
            response = server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": "mythic_vibe.status",
                        "arguments": {"argv": ["--path", tmp, "--json"]},
                    },
                }
            )
        assert response is not None
        result = response["result"]
        self.assertIsInstance(result, dict)
        self.assertIn("content", result)
        # `content` is a list of typed blocks per MCP spec.
        self.assertEqual(result["content"][0]["type"], "text")

    def test_call_unknown_tool_returns_error_envelope(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "ghost.command",
                    "arguments": {"argv": []},
                },
            }
        )
        assert response is not None
        # Internal error because the call raises ValueError; the
        # JSON-RPC error envelope is returned, not a result.
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], INTERNAL_ERROR)

    def test_call_missing_name_raises(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {"arguments": {"argv": []}},
            }
        )
        assert response is not None
        self.assertIn("error", response)


class McpServerErrorPathTests(unittest.TestCase):
    def test_missing_method_returns_invalid_request(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {"jsonrpc": "2.0", "id": 6}
        )
        assert response is not None
        self.assertEqual(response["error"]["code"], INVALID_REQUEST)

    def test_unknown_method_returns_method_not_found(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {"jsonrpc": "2.0", "id": 7, "method": "ghost"}
        )
        assert response is not None
        self.assertEqual(response["error"]["code"], METHOD_NOT_FOUND)

    def test_unknown_notification_silently_ignored(self) -> None:
        server = McpServer()
        # Notification (no `id`) on unknown method → returns None.
        response = server.handle_request(
            {"jsonrpc": "2.0", "method": "ghost"}
        )
        self.assertIsNone(response)

    def test_non_dict_payload_returns_invalid_request(self) -> None:
        server = McpServer()
        # Pass a list — not a JSON object.
        response = server.handle_request([])
        assert response is not None
        self.assertEqual(response["error"]["code"], INVALID_REQUEST)

    def test_non_dict_params_returns_invalid_params(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/list",
                "params": "not a dict",
            }
        )
        assert response is not None
        self.assertEqual(response["error"]["code"], INVALID_PARAMS)


class McpServerPingTests(unittest.TestCase):
    def test_ping_returns_empty_object(self) -> None:
        server = McpServer()
        response = server.handle_request(
            {"jsonrpc": "2.0", "id": 9, "method": "ping"}
        )
        assert response is not None
        self.assertEqual(response["result"], {})


# ---- run_stdio_server -----------------------------------------------


class RunStdioServerTests(unittest.TestCase):
    def _run_with_input(self, lines: list[str]) -> list[dict]:
        stdin = io.StringIO("\n".join(lines) + "\n" if lines else "")
        stdout = io.StringIO()
        run_stdio_server(stdin=stdin, stdout=stdout)
        responses: list[dict] = []
        for line in stdout.getvalue().splitlines():
            if line.strip():
                responses.append(json.loads(line))
        return responses

    def test_initialize_then_tools_list(self) -> None:
        responses = self._run_with_input(
            [
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {},
                    }
                ),
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/list",
                    }
                ),
            ]
        )
        self.assertEqual(len(responses), 2)
        self.assertEqual(responses[0]["id"], 1)
        self.assertEqual(responses[1]["id"], 2)
        self.assertGreater(len(responses[1]["result"]["tools"]), 10)

    def test_invalid_json_emits_parse_error(self) -> None:
        responses = self._run_with_input(["this is not json"])
        self.assertEqual(len(responses), 1)
        self.assertEqual(responses[0]["error"]["code"], PARSE_ERROR)

    def test_blank_lines_skipped(self) -> None:
        responses = self._run_with_input([""])
        self.assertEqual(responses, [])


if __name__ == "__main__":
    unittest.main()
