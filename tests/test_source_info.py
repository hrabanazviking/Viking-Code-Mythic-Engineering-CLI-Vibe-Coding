# Spec for the Pi-derived source-info primitive. Pi has no direct unit tests
# for source-info.ts; these are Mythic-flavored unit tests against the Python
# port. Pi's PathMetadata-dependent createSourceInfo factory is intentionally
# not ported (out of scope for this slice — pi's package-manager subsystem is
# not being plundered).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# The Python implementation under test (mythic_vibe_cli.runtime.source_info)
# is licensed under the Apache License, Version 2.0.
"""Tests for the Pi-derived source-info provenance primitive."""

from __future__ import annotations

import unittest

from mythic_vibe_cli.runtime.source_info import (
    SourceInfo,
    synthetic_source_info,
)


class SourceInfoTests(unittest.TestCase):
    def test_synthetic_factory_uses_pi_default_scope_and_origin(self) -> None:
        info = synthetic_source_info("audit.py", source="audit")

        self.assertEqual(info.scope, "temporary")
        self.assertEqual(info.origin, "top-level")
        self.assertIsNone(info.base_dir)

    def test_synthetic_factory_accepts_explicit_overrides(self) -> None:
        info = synthetic_source_info(
            path="user_skill.py",
            source="custom_skill",
            scope="user",
            origin="package",
            base_dir="~/.mythic-vibe/skills",
        )

        self.assertEqual(info.path, "user_skill.py")
        self.assertEqual(info.source, "custom_skill")
        self.assertEqual(info.scope, "user")
        self.assertEqual(info.origin, "package")
        self.assertEqual(info.base_dir, "~/.mythic-vibe/skills")

    def test_to_dict_omits_base_dir_when_none(self) -> None:
        info = synthetic_source_info("simple.py", source="ext")

        payload = info.to_dict()

        self.assertEqual(
            payload,
            {
                "path": "simple.py",
                "source": "ext",
                "scope": "temporary",
                "origin": "top-level",
            },
        )

    def test_to_dict_includes_base_dir_when_set(self) -> None:
        info = synthetic_source_info(
            "located.py",
            source="ext",
            base_dir="/tmp/mythic-skills",
        )

        payload = info.to_dict()

        self.assertEqual(payload.get("base_dir"), "/tmp/mythic-skills")

    def test_source_info_is_immutable(self) -> None:
        info = synthetic_source_info("frozen.py", source="ext")

        with self.assertRaises(Exception):  # noqa: BLE001 - intentional broad capture
            info.path = "mutated.py"  # type: ignore[misc]

    def test_synthetic_source_info_returns_source_info_instance(self) -> None:
        info = synthetic_source_info("typed.py", source="ext")
        self.assertIsInstance(info, SourceInfo)


if __name__ == "__main__":
    unittest.main()
