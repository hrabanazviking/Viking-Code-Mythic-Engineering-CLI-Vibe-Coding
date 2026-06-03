from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from mythic_vibe_cli.runtime.paths import (
    PathOwnershipError,
    cache_root,
    config_candidates,
    config_root,
    log_root,
    paths_for,
    resolve_within,
    script_crash_reports_root,
    state_root,
    workspace_root,
)


class RuntimePathsTests(unittest.TestCase):
    def test_project_paths_keep_existing_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = paths_for(root)

            self.assertEqual(paths.project_state_dir, root.resolve() / "mythic")
            self.assertEqual(paths.status_file, root.resolve() / "mythic" / "status.json")
            self.assertEqual(paths.provider_calls_log, root.resolve() / "mythic" / "ai" / "provider_calls.jsonl")
            self.assertEqual(paths.routing_file, root.resolve() / "mythic" / "ai" / "routing.json")
            self.assertEqual(paths.events_log, root.resolve() / "mythic" / "events.jsonl")
            self.assertEqual(paths.memory_db, root.resolve() / ".mythic" / "memory.sqlite")

    def test_resolve_within_accepts_nested_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                resolve_within(root, "docs/notes.md"),
                root.resolve() / "docs" / "notes.md",
            )

    def test_resolve_within_rejects_traversal_and_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad_paths = [
                "../outside.txt",
                "docs/../../outside.txt",
                str(root / "absolute.txt"),
                r"C:\Users\volmarr\outside.txt",
                "",
            ]
            for bad_path in bad_paths:
                with self.subTest(bad_path=bad_path):
                    with self.assertRaises(PathOwnershipError):
                        resolve_within(root, bad_path)

    def test_global_roots_honor_env_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            env = {
                "MYTHIC_CONFIG_HOME": str(base / "config"),
                "MYTHIC_STATE_HOME": str(base / "state"),
                "MYTHIC_CACHE_HOME": str(base / "cache"),
                "MYTHIC_LOG_HOME": str(base / "logs"),
                "MYTHIC_WORKSPACE_ROOT": str(base / "work"),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                self.assertEqual(config_root(), base / "config")
                self.assertEqual(state_root(), base / "state")
                self.assertEqual(cache_root(), base / "cache")
                self.assertEqual(log_root(), base / "logs")
                self.assertEqual(workspace_root(), (base / "work").resolve())
                self.assertEqual(script_crash_reports_root(), base / "state" / "script-crashes")

    def test_config_candidates_include_project_and_global_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = config_candidates(root)

        self.assertIn(root.resolve() / "config.yaml", candidates)
        self.assertIn(root.resolve() / ".mythic-vibe.json", candidates)
        self.assertTrue(any(path.name == "config.yaml" for path in candidates))


if __name__ == "__main__":
    unittest.main()
