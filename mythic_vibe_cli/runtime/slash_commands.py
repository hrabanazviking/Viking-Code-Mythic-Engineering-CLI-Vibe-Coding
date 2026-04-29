# Portions adapted from badlogic/pi-mono (packages/coding-agent/src/core/slash-commands.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md at the repo root.
"""Typed catalog of slash commands.

This is a **catalog only** — there is no runtime dispatcher in this module.
The dispatcher belongs to whichever surface ultimately consumes the catalog
(a future REPL, TUI, or SDK). Keeping the two separate matches pi's design:
the same `/foo` works in any consumer because the catalog is the single
source of truth for "what commands exist."

Three public types and one constant:

- :class:`SlashCommandSource` — the four kinds of source a command can come
  from. Pi names three (``extension`` / ``prompt`` / ``skill``); Mythic adds
  ``plugin`` because the plugin layer is first-class here.
- :class:`BuiltinSlashCommand` — frozen dataclass for the canonical
  shipped-with-the-CLI commands.
- :class:`SlashCommandInfo` — frozen dataclass for any slash command (built
  in or contributed), including the source label and a free-form
  ``source_info`` string for traceability (path, plugin entrypoint, etc.).
- :data:`BUILTIN_SLASH_COMMANDS` — the canonical Mythic catalog.

The Mythic builtin list mirrors the existing sub-command surface so a future
REPL or TUI feels consistent with the CLI a user already knows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .source_info import SourceInfo


SlashCommandSource = Literal["extension", "prompt", "skill", "plugin"]


@dataclass(frozen=True)
class BuiltinSlashCommand:
    name: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "description": self.description}


@dataclass(frozen=True)
class SlashCommandInfo:
    name: str
    source: SlashCommandSource
    source_info: SourceInfo
    description: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "source": self.source,
            "source_info": self.source_info.to_dict(),
            "description": self.description,
        }


BUILTIN_SLASH_COMMANDS: tuple[BuiltinSlashCommand, ...] = (
    BuiltinSlashCommand(name="help", description="List available slash commands and their sources"),
    BuiltinSlashCommand(name="status", description="Show project state"),
    BuiltinSlashCommand(name="scan", description="Run a project context scan"),
    BuiltinSlashCommand(name="packet", description="Packet operations: create, show, list, ingest, diff"),
    BuiltinSlashCommand(name="verify", description="Run verification checks against the project"),
    BuiltinSlashCommand(name="reflect", description="Create a session handoff with summary and next-step"),
    BuiltinSlashCommand(name="resume", description="Load the latest handoff and show its next-recommended action"),
    BuiltinSlashCommand(name="method", description="Show active Mythic Engineering method notes"),
    BuiltinSlashCommand(name="handoff", description="Inspect or list session handoffs"),
    BuiltinSlashCommand(name="workflow", description="Workflow plan, run, packets, history"),
    BuiltinSlashCommand(name="plugin", description="List, inspect, or disable plugins"),
    BuiltinSlashCommand(name="grimoire", description="Plugin registry: add or list entrypoints"),
    BuiltinSlashCommand(name="reload", description="Reload plugins, skills, prompts, and method cache"),
    BuiltinSlashCommand(name="quit", description="Exit the interactive session"),
)
