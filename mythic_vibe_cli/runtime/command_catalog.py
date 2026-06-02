"""Validated command catalog facade.

This module centralizes the rules that relate the public argparse
command set to slash-visible builtins and interactive-local slash
commands. It intentionally wraps the legacy ``BUILTIN_SLASH_COMMANDS``
constant instead of replacing it in one large rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .slash_commands import BUILTIN_SLASH_COMMANDS, BuiltinSlashCommand


SLASH_LOCAL_NAMES = frozenset({"help", "model", "reload", "quit"})
ARGPARSE_ONLY_NAMES = frozenset({"shell", "tui", "slash"})


@dataclass(frozen=True)
class CommandCatalogEntry:
    name: str
    description: str
    slash_visible: bool
    argparse_registered: bool
    interactive_local: bool = False
    source: str = "builtin"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "slash_visible": self.slash_visible,
            "argparse_registered": self.argparse_registered,
            "interactive_local": self.interactive_local,
            "source": self.source,
        }


@dataclass(frozen=True)
class CommandCatalogValidation:
    errors: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


def iter_builtin_slash_commands() -> tuple[BuiltinSlashCommand, ...]:
    """Return the slash-visible builtin command catalog."""
    return BUILTIN_SLASH_COMMANDS


def builtin_slash_by_name(name: str) -> BuiltinSlashCommand | None:
    for entry in iter_builtin_slash_commands():
        if entry.name == name:
            return entry
    return None


def build_command_catalog(handler_names: Iterable[str]) -> tuple[CommandCatalogEntry, ...]:
    """Build the top-level command catalog from handler names and slash data."""
    handlers = set(handler_names)
    entries: list[CommandCatalogEntry] = []
    for item in iter_builtin_slash_commands():
        entries.append(
            CommandCatalogEntry(
                name=item.name,
                description=item.description,
                slash_visible=True,
                argparse_registered=item.name in handlers,
                interactive_local=item.name in SLASH_LOCAL_NAMES,
            )
        )
    descriptions = {
        "shell": "Open the interactive companion shell",
        "tui": "Open the Textual Terminal User Interface",
        "slash": "Inspect slash command catalog entries",
    }
    for name in sorted(ARGPARSE_ONLY_NAMES & handlers):
        entries.append(
            CommandCatalogEntry(
                name=name,
                description=descriptions.get(name, f"Mythic Vibe CLI subcommand: {name}"),
                slash_visible=False,
                argparse_registered=True,
            )
        )
    return tuple(entries)


def validate_command_catalog(
    handler_names: Iterable[str],
    *,
    builtin_commands: Sequence[BuiltinSlashCommand] | None = None,
) -> CommandCatalogValidation:
    """Validate command/slash catalog invariants.

    Rules:
    - slash builtin names must be unique,
    - every non-local slash builtin must have an argparse handler,
    - every handler except argparse-only commands must have a slash entry,
    - interactive-local slash names must not also be argparse handlers.
    """
    handlers = set(handler_names)
    builtins = tuple(BUILTIN_SLASH_COMMANDS if builtin_commands is None else builtin_commands)
    names = [entry.name for entry in builtins]
    builtin_names = set(names)
    errors: list[str] = []

    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        errors.append(f"duplicate slash builtin names: {duplicates}")

    missing_handlers = sorted((builtin_names - SLASH_LOCAL_NAMES) - handlers)
    if missing_handlers:
        errors.append(f"slash builtins without argparse handlers: {missing_handlers}")

    missing_slash = sorted((handlers - ARGPARSE_ONLY_NAMES) - builtin_names)
    if missing_slash:
        errors.append(f"argparse handlers without slash builtins: {missing_slash}")

    locals_with_argparse = sorted(SLASH_LOCAL_NAMES & handlers)
    if locals_with_argparse:
        errors.append(f"interactive-local slash names registered in argparse: {locals_with_argparse}")

    return CommandCatalogValidation(errors=tuple(errors))


__all__ = [
    "ARGPARSE_ONLY_NAMES",
    "CommandCatalogEntry",
    "CommandCatalogValidation",
    "SLASH_LOCAL_NAMES",
    "build_command_catalog",
    "builtin_slash_by_name",
    "iter_builtin_slash_commands",
    "validate_command_catalog",
]
