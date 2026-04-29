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
from mythic_vibe_cli.runtime.source_info import synthetic_source_info


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
        provenance = synthetic_source_info(
            "audit_plugin:Plugin",
            source="audit_plugin",
            scope="project",
            origin="top-level",
        )
        info = SlashCommandInfo(
            name="audit",
            source="plugin",
            source_info=provenance,
            description="Append-only audit log",
        )
        payload = info.to_dict()
        self.assertEqual(payload["source"], "plugin")
        self.assertEqual(payload["source_info"], provenance.to_dict())
        self.assertEqual(payload["source_info"]["scope"], "project")
        self.assertEqual(payload["source_info"]["path"], "audit_plugin:Plugin")

    def test_slash_command_info_default_description_is_empty(self) -> None:
        provenance = synthetic_source_info("ext.py", source="extension")
        info = SlashCommandInfo(name="raw", source="extension", source_info=provenance)
        self.assertEqual(info.description, "")

    def test_catalog_is_immutable_tuple(self) -> None:
        self.assertIsInstance(BUILTIN_SLASH_COMMANDS, tuple)
        # And entries are frozen dataclasses
        with self.assertRaises(Exception):  # noqa: BLE001 - intentional broad capture
            BUILTIN_SLASH_COMMANDS[0].name = "mutated"  # type: ignore[misc]

    def test_catalog_covers_every_argparse_handler_after_phase2_slice_2_1(self) -> None:
        """Locks in the slice 2.1 invariant: every argparse-side handler in
        ``COMMAND_HANDLERS`` is exposed as a slash entry, with the
        deliberate exclusions ``shell`` and ``tui`` (nonsensical from
        within the surfaces themselves) and the three interactive-local
        commands ``help`` / ``reload`` / ``quit`` (which exist only as
        slash entries with no argparse counterpart).
        """
        from mythic_vibe_cli.commands import COMMAND_HANDLERS

        DELIBERATELY_EXCLUDED_FROM_SLASH = {"shell", "tui"}
        SLASH_LOCALS_WITHOUT_ARGPARSE = {"help", "reload", "quit"}

        catalog_names = {entry.name for entry in BUILTIN_SLASH_COMMANDS}
        argparse_names = set(COMMAND_HANDLERS) - DELIBERATELY_EXCLUDED_FROM_SLASH
        # `slash` is the meta-introspection command and lives in argparse,
        # not as a builtin-slash entry, since `/slash list` would be
        # circular. Acceptable asymmetry.
        argparse_names.discard("slash")

        missing_from_catalog = argparse_names - catalog_names
        self.assertEqual(
            missing_from_catalog,
            set(),
            msg=f"argparse handlers without slash entries: {sorted(missing_from_catalog)}",
        )

        catalog_extras = catalog_names - argparse_names
        self.assertEqual(
            catalog_extras,
            SLASH_LOCALS_WITHOUT_ARGPARSE,
            msg=(
                "Catalog has slash-only entries beyond the documented "
                "interactive locals: "
                f"{sorted(catalog_extras - SLASH_LOCALS_WITHOUT_ARGPARSE)}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
