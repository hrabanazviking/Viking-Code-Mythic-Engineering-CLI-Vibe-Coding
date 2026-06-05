from __future__ import annotations

import io
import json
import shlex
import contextlib
import os
import subprocess
from pathlib import Path
from typing import Any

from ..protocols.mcp_tools import build_tool_catalogue


def get_agent_tools() -> list[dict[str, Any]]:
    """Convert MCP tools and OS tools into OpenAI-compatible tool schemas for the agent."""
    mcp_tools = build_tool_catalogue()
    tools = []
    
    # OS Level Tools
    tools.extend([
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file to read."}
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write or overwrite the contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file."},
                        "content": {"type": "string", "description": "Content to write."}
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Run a shell command in the project directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The shell command to execute."}
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List the contents of a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the directory."}
                    },
                    "required": ["path"],
                    "additionalProperties": False,
                }
            }
        }
    ])

    for mcp_tool in mcp_tools:
        parameters = dict(mcp_tool.input_schema)
        tools.append({
            "type": "function",
            "function": {
                "name": mcp_tool.name.replace(".", "_"),  
                "description": mcp_tool.description,
                "parameters": parameters,
            }
        })
    return tools


def execute_tool(name: str, arguments: dict[str, Any], project_root: Path | None = None) -> str:
    """Execute a tool request and return its stdout/stderr as a string."""
    
    root_path = project_root if project_root is not None else Path.cwd()
    
    if name == "read_file":
        path = root_path / arguments.get("path", "")
        try:
            return path.read_text(encoding="utf-8")
        except Exception as exc:
            return f"Failed to read file: {exc}"
            
    if name == "write_file":
        path = root_path / arguments.get("path", "")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(arguments.get("content", ""), encoding="utf-8")
            return f"Successfully wrote to {path}"
        except Exception as exc:
            return f"Failed to write file: {exc}"
            
    if name == "run_command":
        command = arguments.get("command", "")
        try:
            result = subprocess.run(
                command, shell=True, cwd=str(root_path), 
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )
            return result.stdout or f"Command executed with exit code {result.returncode}"
        except Exception as exc:
            return f"Command failed: {exc}"
            
    if name == "list_dir":
        path = root_path / arguments.get("path", ".")
        try:
            items = os.listdir(path)
            return "\\n".join(sorted(items))
        except Exception as exc:
            return f"Failed to list directory: {exc}"

    from ..app import main

    if not name.startswith("mythic_vibe_"):
        return f"Error: Unknown tool prefix {name}"

    command_name = name[len("mythic_vibe_"):]
    tool_argv = arguments.get("argv", [])
    if not isinstance(tool_argv, list):
        return f"Error: argv must be a list, got {type(tool_argv)}"
    
    tool_argv = [str(arg) for arg in tool_argv]
    full_argv = [command_name] + tool_argv

    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = main(full_argv)
    except SystemExit as exc:
        exit_code = exc.code if exc.code is not None else 0
    except Exception as exc:
        return f"Tool execution crashed: {exc}\\n{stderr.getvalue()}"

    output = stdout.getvalue()
    err_output = stderr.getvalue()

    result = []
    if output:
        result.append(output.strip())
    if err_output:
        result.append(f"STDERR:\\n{err_output.strip()}")
    result.append(f"Exit code: {exit_code}")
    
    return "\\n".join(result)
