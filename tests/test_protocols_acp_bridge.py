"""Tests for PH-16 Slice 16.3 — ACP IDE bridge."""

from __future__ import annotations

import io
import json
import unittest

from mythic_vibe_cli.protocols.acp_bridge import (
    AcpServer,
    PROTOCOL_VERSION,
    SERVER_NAME,
    run_stdio_server,
)


# ---- AcpServer.handle_request -----------------------------------------


class AcpServerStatusTests(unittest.TestCase):
    def test_status_returns_server_info(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "agent.status"}
        )
        assert response is not None
        result = response["result"]
        self.assertEqual(result["protocolVersion"], PROTOCOL_VERSION)
        self.assertEqual(result["serverInfo"]["name"], SERVER_NAME)
        self.assertEqual(result["activeRuns"], [])


class AcpServerExecuteTests(unittest.TestCase):
    def test_execute_status_command(self) -> None:
        import tempfile

        server = AcpServer()
        with tempfile.TemporaryDirectory() as tmp:
            response = server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "agent.execute",
                    "params": {
                        "command": "status",
                        "argv": ["--path", tmp, "--json"],
                    },
                }
            )
        assert response is not None
        result = response["result"]
        self.assertIn("run_id", result)
        self.assertEqual(result["command"], "status")
        self.assertIsInstance(result["exit_code"], int)
        self.assertIsInstance(result["stdout"], str)
        self.assertFalse(result["cancelled"])

    def test_execute_unknown_command_returns_error(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "agent.execute",
                "params": {"command": "ghost", "argv": []},
            }
        )
        assert response is not None
        self.assertIn("error", response)

    def test_execute_missing_command_raises(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "agent.execute",
                "params": {"argv": []},
            }
        )
        assert response is not None
        self.assertIn("error", response)

    def test_execute_invalid_argv_raises(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "agent.execute",
                "params": {"command": "status", "argv": [1, 2, 3]},
            }
        )
        assert response is not None
        self.assertIn("error", response)


class AcpServerCancelTests(unittest.TestCase):
    def test_cancel_unknown_run(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "agent.cancel",
                "params": {"run_id": "RUN-ghost"},
            }
        )
        assert response is not None
        result = response["result"]
        self.assertFalse(result["cancelled"])
        self.assertIn("not found", result["reason"])

    def test_cancel_missing_run_id_raises(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "agent.cancel",
                "params": {},
            }
        )
        assert response is not None
        self.assertIn("error", response)


class AcpServerErrorPathsTests(unittest.TestCase):
    def test_unknown_method(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "ghost"}
        )
        assert response is not None
        self.assertIn("error", response)

    def test_notification_no_response(self) -> None:
        server = AcpServer()
        response = server.handle_request(
            {"jsonrpc": "2.0", "method": "agent.status"}
        )
        self.assertIsNone(response)

    def test_non_dict_payload(self) -> None:
        server = AcpServer()
        response = server.handle_request([])
        assert response is not None
        self.assertIn("error", response)


# ---- run_stdio_server -------------------------------------------------


class RunStdioServerTests(unittest.TestCase):
    def test_status_round_trip(self) -> None:
        request = (
            json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": "agent.status"}
            )
            + "\n"
        )
        stdin = io.StringIO(request)
        stdout = io.StringIO()
        run_stdio_server(stdin=stdin, stdout=stdout)
        line = stdout.getvalue().strip().splitlines()[0]
        response = json.loads(line)
        self.assertEqual(response["id"], 1)

    def test_invalid_json_returns_parse_error(self) -> None:
        stdin = io.StringIO("not json\n")
        stdout = io.StringIO()
        run_stdio_server(stdin=stdin, stdout=stdout)
        response = json.loads(stdout.getvalue().strip())
        self.assertIn("error", response)


if __name__ == "__main__":
    unittest.main()
