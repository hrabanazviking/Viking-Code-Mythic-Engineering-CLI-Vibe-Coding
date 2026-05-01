"""Tests for PH-05 follow-up: graph auto-population.

Covers the helpers in :mod:`mythic_vibe_cli.context.autopopulate`
plus the integration into ``cmd_checkin`` and ``cmd_scan``.
"""

from __future__ import annotations

import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from mythic_vibe_cli.context.autopopulate import (
    AutoPopulateResult,
    populate_from_checkin,
    populate_from_scan,
)
from mythic_vibe_cli.context.graph import GraphStore
from mythic_vibe_cli.context.scanner import ProjectIndex
from mythic_vibe_cli.exit_codes import SUCCESS


def _index(
    *,
    docs: list[dict[str, object]] | None = None,
    tests: list[dict[str, object]] | None = None,
    important_files: list[dict[str, object]] | None = None,
) -> ProjectIndex:
    return ProjectIndex(
        generated_at="2026-05-01T00:00:00Z",
        root="/test",
        languages={"Python": {"files": 1, "bytes": 100}},
        docs=docs or [],
        tests=tests or [],
        important_files=important_files or [],
    )


# ---- AutoPopulateResult ----------------------------------------------


class AutoPopulateResultTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        r = AutoPopulateResult(entities_upserted=3, tags_added=4)
        payload = r.to_dict()
        self.assertEqual(payload["entities_upserted"], 3)
        self.assertEqual(payload["tags_added"], 4)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["errors"], [])

    def test_ok_false_when_errors_present(self) -> None:
        r = AutoPopulateResult(errors=["something blew up"])
        self.assertFalse(r.ok)


# ---- populate_from_scan ----------------------------------------------


class PopulateFromScanTests(unittest.TestCase):
    def test_doc_entity_upserted_with_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = _index(
                docs=[{"path": "docs/SYSTEM.md", "size": 1024, "language": "markdown"}]
            )
            result = populate_from_scan(root, index)
            self.assertTrue(result.ok)
            self.assertEqual(result.entities_upserted, 1)
            self.assertEqual(result.tags_added, 1)

            with GraphStore.open(root) as store:
                doc = store.find_entity("doc", "docs/SYSTEM.md")
                self.assertIsNotNone(doc)
                assert doc is not None
                self.assertEqual(doc.path, "docs/SYSTEM.md")
                self.assertEqual(doc.metadata.get("size"), 1024)
                tags = dict(store.tags_for(doc.id))
                self.assertIn("kind:doc", tags)

    def test_test_entity_upserted_with_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = _index(
                tests=[{"path": "tests/test_x.py", "size": 200, "command": "pytest"}]
            )
            result = populate_from_scan(root, index)
            self.assertEqual(result.entities_upserted, 1)

            with GraphStore.open(root) as store:
                test_entity = store.find_entity("test", "tests/test_x.py")
                self.assertIsNotNone(test_entity)
                assert test_entity is not None
                tags = dict(store.tags_for(test_entity.id))
                self.assertIn("kind:test", tags)

    def test_python_module_upserted_from_important_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = _index(
                important_files=[
                    {
                        "path": "mythic_vibe_cli/app.py",
                        "reason": "CLI entry",
                        "size": 4096,
                    }
                ]
            )
            result = populate_from_scan(root, index)
            self.assertEqual(result.entities_upserted, 1)
            self.assertEqual(result.tags_added, 2)  # kind:module + language:python

            with GraphStore.open(root) as store:
                module = store.find_entity("module", "mythic_vibe_cli.app")
                self.assertIsNotNone(module)
                assert module is not None
                tags = dict(store.tags_for(module.id))
                self.assertIn("kind:module", tags)
                self.assertIn("language:python", tags)

    def test_non_python_important_file_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = _index(
                important_files=[
                    {"path": "README.md", "reason": "docs", "size": 1000}
                ]
            )
            result = populate_from_scan(root, index)
            self.assertEqual(result.entities_upserted, 0)

    def test_idempotent_repeat_scan(self) -> None:
        """Running the helper twice on the same index must not
        duplicate entities — GraphStore.upsert_entity is keyed by
        (kind, name)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            index = _index(docs=[{"path": "docs/A.md", "size": 1, "language": "md"}])
            populate_from_scan(root, index)
            populate_from_scan(root, index)
            with GraphStore.open(root) as store:
                self.assertEqual(store.entity_count(), 1)

    def test_empty_index_is_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = populate_from_scan(root, _index())
            self.assertTrue(result.ok)
            self.assertEqual(result.entities_upserted, 0)

    def test_failure_does_not_raise(self) -> None:
        """When sqlite is unwritable (simulated by passing a
        non-existent root that can't be created), the helper logs to
        result.errors and never raises."""
        with mock.patch.object(
            GraphStore, "open", side_effect=OSError("read-only fs")
        ):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = populate_from_scan(
                    root,
                    _index(docs=[{"path": "x.md", "size": 1, "language": "md"}]),
                )
        self.assertFalse(result.ok)
        self.assertTrue(any("open graph store" in e for e in result.errors))


# ---- populate_from_checkin -------------------------------------------


class PopulateFromCheckinTests(unittest.TestCase):
    def test_checkin_entity_upserted_with_phase_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = populate_from_checkin(
                root,
                phase="build",
                update_text="implemented sub-slice 4",
                timestamp="2026-05-01T12:00:00Z",
                status_path=root / "STATUS.md",
                devlog_path=root / "DEVLOG.md",
            )
            self.assertTrue(result.ok)
            self.assertEqual(result.entities_upserted, 1)
            self.assertEqual(result.tags_added, 2)

            with GraphStore.open(root) as store:
                checkin = store.find_entity("checkin", "build-2026-05-01T12:00:00Z")
                self.assertIsNotNone(checkin)
                assert checkin is not None
                self.assertEqual(checkin.metadata.get("phase"), "build")
                self.assertEqual(
                    checkin.metadata.get("update_text"),
                    "implemented sub-slice 4",
                )
                tags = dict(store.tags_for(checkin.id))
                self.assertIn("phase:build", tags)
                self.assertIn("kind:checkin", tags)

    def test_failure_does_not_raise(self) -> None:
        with mock.patch.object(
            GraphStore, "open", side_effect=OSError("oops")
        ):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = populate_from_checkin(
                    root,
                    phase="build",
                    update_text="x",
                    timestamp="2026-05-01T12:00:00Z",
                )
        self.assertFalse(result.ok)


# ---- cmd_checkin / cmd_scan integration ------------------------------


class CmdCheckinAutoPopulateTests(unittest.TestCase):
    def test_real_checkin_populates_graph(self) -> None:
        """Use the real init command via app.main to set up a project,
        then call cmd_checkin and assert the graph has the check-in
        entity."""
        from mythic_vibe_cli import app
        from mythic_vibe_cli.commands import cmd_checkin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirect_stdout(io.StringIO()):
                app.main(
                    ["init", "--goal", "Test sub-slice 4", "--path", str(root)]
                )

            checkin_ns = argparse.Namespace(
                path=str(root),
                phase="build",
                update="phase progress",
                json=False,
                dry_run=False,
            )
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_checkin(checkin_ns)
            self.assertEqual(exit_code, SUCCESS)

            # Verify the graph got a check-in entity.
            with GraphStore.open(root) as store:
                rows = store.find_entities(kind="checkin")
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].metadata.get("phase"), "build")

    def test_dry_run_checkin_does_not_populate_graph(self) -> None:
        from mythic_vibe_cli.commands import cmd_checkin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = argparse.Namespace(
                path=str(root),
                phase="intent",
                update="x",
                json=False,
                dry_run=True,
            )
            with redirect_stdout(io.StringIO()):
                cmd_checkin(ns)
            # Graph DB shouldn't even exist.
            self.assertFalse((root / "mythic" / "graph.sqlite3").is_file())


class CmdScanAutoPopulateTests(unittest.TestCase):
    def test_real_scan_populates_graph(self) -> None:
        from mythic_vibe_cli.commands import cmd_scan

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Build a minimal project with one doc + one test.
            (root / "docs").mkdir()
            (root / "docs" / "SYSTEM.md").write_text(
                "# System\n", encoding="utf-8"
            )
            (root / "tests").mkdir()
            (root / "tests" / "test_x.py").write_text(
                "def test(): pass\n", encoding="utf-8"
            )

            ns = argparse.Namespace(
                path=str(root),
                changed=False,
                docs=False,
                include=[],
                exclude=[],
                json=True,
                dry_run=False,
            )
            with redirect_stdout(io.StringIO()):
                exit_code = cmd_scan(ns)
            self.assertEqual(exit_code, SUCCESS)

            # Graph should contain a doc + a test entity.
            with GraphStore.open(root) as store:
                docs = store.find_entities(kind="doc")
                tests = store.find_entities(kind="test")
            self.assertGreaterEqual(len(docs), 1)
            self.assertGreaterEqual(len(tests), 1)

    def test_dry_run_scan_does_not_populate_graph(self) -> None:
        from mythic_vibe_cli.commands import cmd_scan

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ns = argparse.Namespace(
                path=str(root),
                changed=False,
                docs=False,
                include=[],
                exclude=[],
                json=True,
                dry_run=True,
            )
            with redirect_stdout(io.StringIO()):
                cmd_scan(ns)
            self.assertFalse((root / "mythic" / "graph.sqlite3").is_file())


if __name__ == "__main__":
    unittest.main()
