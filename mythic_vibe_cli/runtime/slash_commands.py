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
    """Metadata for any non-builtin slash command.

    PH-02 slice 2.6 added the optional ``argv`` field — a tuple of
    string arguments the picker uses to actually dispatch the
    command via ``RunningCommandScreen``. When ``argv`` is empty
    (the default), the slash entry is **discoverable but not
    runnable** — the picker shows a "(plugin dispatch not yet
    implemented)" notice and the operator must fall back to the
    plugin's documented invocation. This keeps the contract
    backwards-compatible: existing plugins that contribute
    descriptions only continue to work.
    """

    name: str
    source: SlashCommandSource
    source_info: SourceInfo
    description: str = ""
    argv: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "source": self.source,
            "source_info": self.source_info.to_dict(),
            "description": self.description,
            "argv": list(self.argv),
        }


BUILTIN_SLASH_COMMANDS: tuple[BuiltinSlashCommand, ...] = (
    # --- Interactive-session locals (REPL/TUI handles directly) ---
    BuiltinSlashCommand(name="help", description="List available slash commands and their sources"),
    BuiltinSlashCommand(name="reload", description="Reload plugins, skills, prompts, and method cache"),
    BuiltinSlashCommand(name="quit", description="Exit the interactive session"),

    # --- Project lifecycle ---
    BuiltinSlashCommand(name="init", description="Initialize a new Mythic Engineering project scaffold"),
    BuiltinSlashCommand(name="imbue", description="Alias of init — imbue an existing directory with the Mythic scaffold"),
    BuiltinSlashCommand(name="start", description="Alias of init — start a new Mythic project"),
    BuiltinSlashCommand(name="status", description="Show project state and recent verification"),
    BuiltinSlashCommand(name="next", description="Print the next recommended action for the current phase"),
    BuiltinSlashCommand(name="checkin", description="Record a phase check-in and append to DEVLOG"),

    # --- Workflow & scanning ---
    BuiltinSlashCommand(name="scan", description="Scan the project and update the local context index"),
    BuiltinSlashCommand(name="workflow", description="Workflow plan, run, packets, history"),
    BuiltinSlashCommand(name="reflect", description="Create a session handoff with summary and next-step"),
    BuiltinSlashCommand(name="handoff", description="Inspect or list session handoffs"),
    BuiltinSlashCommand(name="resume", description="Load the latest handoff and show its next-recommended action"),

    # --- Packets & AI ---
    BuiltinSlashCommand(name="packet", description="Packet operations: create, show, list, ingest, diff"),
    BuiltinSlashCommand(name="codex-pack", description="Generate a ChatGPT/Codex packet from project context"),
    BuiltinSlashCommand(name="evoke", description="Mythic alias of codex-pack — evoke a packet"),
    BuiltinSlashCommand(name="codex-log", description="Log a Codex/AI response back into the project DEVLOG"),
    BuiltinSlashCommand(name="ai", description="AI provider operations: providers, test, run, ingest-response"),

    # --- Verification & diagnostics ---
    BuiltinSlashCommand(name="verify", description="Run verification checks against the project"),
    BuiltinSlashCommand(name="doctor", description="Diagnostic checks across artefacts, state, docs, boundaries"),
    BuiltinSlashCommand(name="scry", description="Mythic alias of doctor — scry the project's health"),

    # --- Method corpus ---
    BuiltinSlashCommand(name="method", description="Show / sync / diff / pin the Mythic Engineering method corpus"),
    BuiltinSlashCommand(name="import-md", description="Import the Mythic Engineering markdown corpus"),
    BuiltinSlashCommand(name="sync", description="Sync the method corpus from the upstream source"),

    # --- UX helpers ---
    BuiltinSlashCommand(name="examples", description="Print canonical command-line examples"),
    BuiltinSlashCommand(name="guide", description="Print the short Mythic Engineering operator guide"),
    BuiltinSlashCommand(name="explain", description="Explain a phase or artifact in plain language"),
    BuiltinSlashCommand(name="tutorial", description="Walk through the Mythic Engineering loop interactively"),
    BuiltinSlashCommand(name="completion", description="Print a shell completion script for the CLI"),

    # --- Rituals (scaffold-mode today; real impl lives at PH-13/14) ---
    BuiltinSlashCommand(name="weave", description="Record a weave/reflect checkpoint (note: F-021 gates this until verify --record)"),
    BuiltinSlashCommand(name="prune", description="Prune stale Mythic artefacts (scaffold today; PH-13 grows it)"),
    BuiltinSlashCommand(name="heal", description="Heal failing-test workflow (scaffold today; PH-13 grows it)"),
    BuiltinSlashCommand(name="oath", description="Display and accept the AI-review oath"),

    # --- Plugins & registry ---
    BuiltinSlashCommand(name="plugin", description="List, inspect, or disable plugins"),
    BuiltinSlashCommand(name="grimoire", description="Plugin registry: add or list entrypoints"),

    # --- Configuration & operational ---
    BuiltinSlashCommand(name="config", description="Show or set Mythic CLI configuration values"),
    BuiltinSlashCommand(name="state", description="Project state: show or validate the schema-versioned status.json"),
    BuiltinSlashCommand(name="db", description="Database operations: migrate the state schema"),
    BuiltinSlashCommand(name="plunder", description="Lawful single-file reuse from upstream Apache/MIT/BSD repositories"),

    # --- Developer-tool shortcuts (PH-02 slice 2.2) ---
    BuiltinSlashCommand(name="test", description="Run the project's test suite (pytest by default; --command to override)"),
    BuiltinSlashCommand(name="lint", description="Run ruff check across the project (--command to override)"),
    BuiltinSlashCommand(name="typecheck", description="Run mypy across the project (--command to override)"),
    BuiltinSlashCommand(name="scaffold", description="Add an artefact to an existing project (today: adr)"),
    BuiltinSlashCommand(name="changelog", description="Print or validate the [Unreleased] section of CHANGELOG.md"),
    BuiltinSlashCommand(name="version", description="Print the CLI version (subcommand form of --version)"),

    # --- Workflow-phase capture commands (PH-02 slice 2.3) ---
    BuiltinSlashCommand(name="intent", description="Capture a Mythic Phase Record for the intent phase"),
    BuiltinSlashCommand(name="constraints", description="Capture a Mythic Phase Record for the constraints phase"),
    BuiltinSlashCommand(name="architecture", description="Capture a Mythic Phase Record for the architecture phase"),
    BuiltinSlashCommand(name="plan", description="Capture a Mythic Phase Record for the plan phase"),
    BuiltinSlashCommand(name="build", description="Capture a Mythic Phase Record for the build phase"),

    # --- Multi-agent forge (PH-03 slice 3.3) ---
    BuiltinSlashCommand(name="forge", description="Multi-agent forge orchestrator (forge plan --dry-run today; forge ledger list/show/latest)"),

    # --- Provider/AI alias (PH-02 slice 2.4) ---
    BuiltinSlashCommand(name="provider", description="List configured AI providers (alias of `ai providers`)"),

    # --- Diagnostic alias (PH-02 slice 2.5) ---
    BuiltinSlashCommand(name="audit", description="Run a doctor pass and emit JSON (alias of `doctor --json`)"),

    # --- Drift detection (PH-13 slice 13.1) ---
    BuiltinSlashCommand(name="drift", description="Scan for drift between docs, code, and decisions (heuristic v1)"),

    # --- Knowledge graph (PH-05 slices 5.5 + 5.6) ---
    BuiltinSlashCommand(name="graph", description="Read-only graph queries: query, entity, edges, brief, visualize"),

    # --- Conversation memory (PH-15 slices 15.3 + 15.4) ---
    BuiltinSlashCommand(name="memory", description="Conversation memory: list, show, compact, rehydrate"),

    # --- Hardware profile (PH-06 slice 6.6) ---
    BuiltinSlashCommand(name="hardware", description="Detect host hardware (CPU/RAM/OS); --write persists to docs/"),

    # --- Voice & multimodal (PH-07 slices 7.1-7.3) ---
    BuiltinSlashCommand(name="voice", description="Voice transcribe + TTS (opt-in; stub engines work without extras)"),
)
