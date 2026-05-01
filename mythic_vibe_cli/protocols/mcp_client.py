"""MCP client (PH-16 Slice 16.2).

Stdlib JSON-RPC 2.0 client that spawns an MCP server subprocess
and invokes its tools. Used by forge plugins (and slice 16.1
self-tests) to integrate external MCPs.

Cross-platform: pure stdlib (``subprocess`` + ``json`` +
``threading``).
"""

from __future__ import annotations

import itertools
import json
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, IO


JsonRpcMessage = dict[str, Any]


class McpClientError(RuntimeError):
    """Raised when an MCP client call fails (server returned an
    error envelope, subprocess died, malformed JSON, etc.)."""


@dataclass
class McpClient:
    """Lightweight JSON-RPC 2.0 client. Construct via
    :meth:`spawn` for subprocess-backed servers or
    :meth:`from_streams` for in-process pipes (testing)."""

    stdin: IO[str]
    stdout: IO[str]
    process: subprocess.Popen | None = None
    _id_counter: itertools.count = field(default_factory=lambda: itertools.count(1))
    _read_lock: threading.Lock = field(default_factory=threading.Lock)
    _write_lock: threading.Lock = field(default_factory=threading.Lock)

    # ---- Construction --------------------------------------------------

    @classmethod
    def spawn(cls, argv: list[str]) -> "McpClient":
        """Spawn the given argv as an MCP server subprocess. Pipes
        stdin / stdout for JSON-RPC framing. stderr is left
        attached to the parent for diagnostic output."""
        if not argv:
            raise ValueError("argv must contain at least the server binary")
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            shell=False,
            text=True,
            bufsize=1,  # line-buffered
        )
        if proc.stdin is None or proc.stdout is None:  # pragma: no cover — Popen contract
            raise McpClientError("Popen did not provide stdin/stdout pipes")
        return cls(stdin=proc.stdin, stdout=proc.stdout, process=proc)

    @classmethod
    def from_streams(cls, *, stdin: IO[str], stdout: IO[str]) -> "McpClient":
        """In-process construction for tests."""
        return cls(stdin=stdin, stdout=stdout)

    # ---- JSON-RPC pump -------------------------------------------------

    def _next_id(self) -> int:
        return next(self._id_counter)

    def _send(self, payload: JsonRpcMessage) -> None:
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with self._write_lock:
            self.stdin.write(line)
            self.stdin.flush()

    def _read_one(self) -> JsonRpcMessage:
        with self._read_lock:
            raw = self.stdout.readline()
        if not raw:
            raise McpClientError("server closed stdout before responding")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise McpClientError(f"server returned invalid JSON: {exc}") from exc

    def call(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Send a JSON-RPC request and return the ``result``
        field. Raises :class:`McpClientError` on transport or
        protocol errors."""
        request_id = self._next_id()
        payload: JsonRpcMessage = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        self._send(payload)

        # Read until we see a response with the matching id;
        # discard notifications / unrelated messages along the
        # way (servers may interleave them).
        while True:
            response = self._read_one()
            if response.get("id") != request_id:
                continue
            error = response.get("error")
            if isinstance(error, dict):
                message = error.get("message", "(no message)")
                code = error.get("code", "?")
                raise McpClientError(
                    f"server error code={code}: {message}"
                )
            return response.get("result")

    def notify(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Fire-and-forget notification (no id, no response)."""
        payload: JsonRpcMessage = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    # ---- High-level convenience ---------------------------------------

    def initialize(self) -> dict[str, Any]:
        """Send the standard MCP handshake. Returns the server's
        info / capabilities payload."""
        result = self.call(
            "initialize",
            params={
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "mythic-vibe-client", "version": "0.1.0"},
                "capabilities": {},
            },
        )
        # Send the post-init notification per MCP spec.
        self.notify("notifications/initialized")
        if not isinstance(result, dict):
            raise McpClientError("initialize did not return an object")
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        result = self.call("tools/list")
        if not isinstance(result, dict):
            raise McpClientError("tools/list did not return an object")
        tools = result.get("tools", [])
        if not isinstance(tools, list):
            raise McpClientError("tools/list result missing tools array")
        return [t for t in tools if isinstance(t, dict)]

    def call_tool(
        self,
        name: str,
        *,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        result = self.call(
            "tools/call",
            params={
                "name": name,
                "arguments": arguments or {},
            },
        )
        if not isinstance(result, dict):
            raise McpClientError("tools/call did not return an object")
        return result

    # ---- Lifecycle ----------------------------------------------------

    def close(self) -> None:
        """Close stdin (signals server shutdown) and reap the
        subprocess if we own one."""
        try:
            self.stdin.close()
        except (OSError, ValueError):
            pass
        try:
            self.stdout.close()
        except (OSError, ValueError):
            pass
        if self.process is not None:
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except OSError:
                pass

    def __enter__(self) -> "McpClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


__all__ = [
    "JsonRpcMessage",
    "McpClient",
    "McpClientError",
]
