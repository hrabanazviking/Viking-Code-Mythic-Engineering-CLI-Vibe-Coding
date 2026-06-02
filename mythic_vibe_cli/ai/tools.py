from __future__ import annotations

import io
import json
import shlex
import contextlib
from typing import Any

from ..protocols.mcp_tools import build_tool_catalogue


def get_agent_tools() -> list[dict[str, Any]]:
    """Convert MCP tools into OpenAI-compatible tool schemas for the agent."""
    mcp_tools = build_tool_catalogue()
    tools = []
    for mcp_tool in mcp_tools:
        # Some providers prefer parameters to be complete JSON schema
        parameters = dict(mcp_tool.input_schema)
        # Ensure additionalProperties is False if required for strict structured output
        # But we leave it as is from mcp_tools.py which already sets it.
        tools.append({
            "type": "function",
            "function": {
                "name": mcp_tool.name.replace(".", "_"),  # e.g. mythic_vibe.memory_search -> mythic_vibe_memory_search
                "description": mcp_tool.description,
                "parameters": parameters,
            }
        })
    return tools


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool request and return its stdout/stderr as a string."""
    from ..app import main

    # Tools are prefixed with mythic_vibe_
    if not name.startswith("mythic_vibe_"):
        return f"Error: Unknown tool prefix {name}"

    # Extract the actual command name
    command_name = name[len("mythic_vibe_"):]
    
    # argv array from the tool arguments
    tool_argv = arguments.get("argv", [])
    if not isinstance(tool_argv, list):
        return f"Error: argv must be a list, got {type(tool_argv)}"
    
    # Ensure they are strings
    tool_argv = [str(arg) for arg in tool_argv]

    full_argv = [command_name] + tool_argv

    # Capture output
    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(full_argv)
    except SystemExit as exc:
        # Argparse might call sys.exit, we catch it so the shell doesn't die.
        exit_code = exc.code if exc.code is not None else 0
    except Exception as exc:
        return f"Tool execution crashed: {exc}\n{stderr.getvalue()}"

    output = stdout.getvalue()
    err_output = stderr.getvalue()

    result = []
    if output:
        result.append(output.strip())
    if err_output:
        result.append(f"STDERR:\n{err_output.strip()}")
    result.append(f"Exit code: {exit_code}")
    
    return "\n".join(result)
