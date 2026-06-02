"""Phase 3 command catalog contract tests."""

from __future__ import annotations

import unittest

from mythic_vibe_cli.commands import COMMAND_HANDLERS
from mythic_vibe_cli.runtime.command_catalog import (
    ARGPARSE_ONLY_NAMES,
    SLASH_LOCAL_NAMES,
    build_command_catalog,
    iter_builtin_slash_commands,
    validate_command_catalog,
)
from mythic_vibe_cli.runtime.slash_commands import BuiltinSlashCommand


class CommandCatalogTests(unittest.TestCase):
    def test_runtime_catalog_validates_current_handlers(self) -> None:
        result = validate_command_catalog(COMMAND_HANDLERS)
        self.assertTrue(result.ok, msg="\n".join(result.errors))

    def test_catalog_entries_classify_slash_and_argparse_surfaces(self) -> None:
        entries = {entry.name: entry for entry in build_command_catalog(COMMAND_HANDLERS)}

        for name in SLASH_LOCAL_NAMES:
            self.assertTrue(entries[name].slash_visible)
            self.assertTrue(entries[name].interactive_local)
            self.assertFalse(entries[name].argparse_registered)

        for name in ARGPARSE_ONLY_NAMES:
            self.assertTrue(entries[name].argparse_registered)
            self.assertFalse(entries[name].slash_visible)

        self.assertTrue(entries["status"].slash_visible)
        self.assertTrue(entries["status"].argparse_registered)
        self.assertFalse(entries["status"].interactive_local)

    def test_validation_reports_duplicate_builtin_names(self) -> None:
        duplicate = (
            *iter_builtin_slash_commands(),
            BuiltinSlashCommand("status", "duplicate status"),
        )
        result = validate_command_catalog(COMMAND_HANDLERS, builtin_commands=duplicate)
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate slash builtin names" in error for error in result.errors))

    def test_validation_reports_handler_without_slash_entry(self) -> None:
        result = validate_command_catalog({"status", "ghost-command"})
        self.assertFalse(result.ok)
        self.assertTrue(any("argparse handlers without slash builtins" in error for error in result.errors))
