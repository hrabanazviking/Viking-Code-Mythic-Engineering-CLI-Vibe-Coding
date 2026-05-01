"""MCP tool catalogue (PH-16 Slice 16.1).

Builds the list of tools the MCP server advertises. Each tool
maps 1:1 onto a Mythic Vibe CLI subcommand. The schema is
intentionally minimal — every tool accepts a single ``argv``
string array which the server turns back into argparse args
when handling ``tools/call``.

Cross-platform: pure stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class McpTool:
    """One MCP-advertised tool."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": dict(self.input_schema),
        }


def _argv_input_schema() -> dict[str, Any]:
    """Schema fragment shared by every tool: a single ``argv``
    array of strings."""
    return {
        "type": "object",
        "properties": {
            "argv": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Subcommand-specific arguments, e.g. "
                    '["--path", ".", "--json"]. Must NOT include the '
                    "tool name itself; the server prepends it."
                ),
            },
        },
        "required": [],
        "additionalProperties": False,
    }


def build_tool_catalogue() -> list[McpTool]:
    """Discover the active CLI command set and return one
    :class:`McpTool` per top-level command.

    The discovery uses :data:`mythic_vibe_cli.commands.COMMAND_HANDLERS`
    as the source of truth — that set is already locked by the
    PH-02 slice 2.1 parity invariant + the slice 2.7 inspect
    surface.
    """
    from ..commands import COMMAND_HANDLERS
    from ..runtime.slash_commands import BUILTIN_SLASH_COMMANDS

    descriptions = {
        entry.name: entry.description for entry in BUILTIN_SLASH_COMMANDS
    }

    seen: set[str] = set()
    tools: list[McpTool] = []
    for raw_name in sorted(COMMAND_HANDLERS):
        name = raw_name
        # Skip aliases that point at the same handler as the
        # canonical name (start/imbue/evoke/scry per slice 2.1).
        if name in {"start", "imbue", "evoke", "scry"}:
            continue
        if name in seen:
            continue
        seen.add(name)
        description = descriptions.get(
            name,
            f"Mythic Vibe CLI subcommand: `mythic-vibe {name}`. "
            "Pass argv to the tool to invoke.",
        )
        tools.append(
            McpTool(
                name=f"mythic_vibe.{name}",
                description=description,
                input_schema=_argv_input_schema(),
            )
        )
    return tools


__all__ = [
    "McpTool",
    "build_tool_catalogue",
]
