# Spec for the Pi-derived slash-commands catalog. Pi has no direct unit tests;
# these cases are Mythic-flavored unit tests against the Python port.
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# The Python implementation under test (mythic_vibe_cli.runtime.slash_commands)
# is licensed under the Apache License, Version 2.0.
"""Tests for the Pi-derived slash-commands catalog primitive."""

from __future__ import annotations

import unittest

from mythic_vibe_cli.runtime.slash_commands import (
    BUILTIN_SLASH_COMMANDS,
    BuiltinSlashCommand,
    SlashCommandInfo,
)


class SlashCommandsCatalogTests(unittest.TestCase):
    def test_catalog_is_non_empty(self) -> None:
        self.assertGreater(len(BUILTIN_SLASH_COMMANDS), 0)

    def test_every_entry_has_name_and_description(self) -> None:
        for entry in BUILTIN_SLASH_COMMANDS:
            self.assertIsInstance(entry, BuiltinSlashCommand)
            self.assertTrue(entry.name)
            self.assertTrue(entry.description)
            self.assertNotIn(" ", entry.name, msg=f"{entry.name} should be a single token")

    def test_builtin_names_are_unique(self) -> None:
        names = [entry.name for entry in BUILTIN_SLASH_COMMANDS]
        self.assertEqual(len(names), len(set(names)))

    def test_catalog_includes_canonical_mythic_commands(self) -> None:
        names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        for required in {"help", "status", "scan", "packet", "verify", "reflect", "quit"}:
            self.assertIn(required, names)

    def test_builtin_dataclass_round_trip(self) -> None:
        entry = BUILTIN_SLASH_COMMANDS[0]
        payload = entry.to_dict()
        self.assertEqual(payload, {"name": entry.name, "description": entry.description})
        self.assertEqual(BuiltinSlashCommand(**payload), entry)

    def test_slash_command_info_carries_source_and_source_info(self) -> None:
        info = SlashCommandInfo(
            name="audit",
            source="plugin",
            source_info="audit_plugin:Plugin",
            description="Append-only audit log",
        )
        payload = info.to_dict()
        self.assertEqual(payload["source"], "plugin")
        self.assertEqual(payload["source_info"], "audit_plugin:Plugin")
        self.assertEqual(SlashCommandInfo(**payload), info)

    def test_slash_command_info_default_description_is_empty(self) -> None:
        info = SlashCommandInfo(name="raw", source="extension", source_info="ext.py")
        self.assertEqual(info.description, "")

    def test_catalog_is_immutable_tuple(self) -> None:
        self.assertIsInstance(BUILTIN_SLASH_COMMANDS, tuple)
        # And entries are frozen dataclasses
        with self.assertRaises(Exception):  # noqa: BLE001 - intentional broad capture
            BUILTIN_SLASH_COMMANDS[0].name = "mutated"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
