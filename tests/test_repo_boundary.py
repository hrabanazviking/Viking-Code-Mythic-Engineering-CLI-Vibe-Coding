from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.cli import main
from mythic_vibe_cli.workflow import MythicRunConfig, MythicWorkflow


BOUNDARY_FILES = [
    "REPO_BOUNDARY.md",
    "docs/ACTIVE_PRODUCT_BOUNDARY.md",
    "docs/DORMANT_ISLANDS.md",
    "docs/ADRS/ADR-0001-active-runtime-boundary.md",
    "docs/ADRS/ADR-0002-no-direct-vendor-imports.md",
]


def _initialized_project(root: Path) -> MythicWorkflow:
    workflow = MythicWorkflow(root)
    workflow.init_project(MythicRunConfig(goal="Test boundary", noob_mode=False), method_source="test")
    return workflow


def _write_boundary_docs(root: Path) -> None:
    for rel_path in BOUNDARY_FILES:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n", encoding="utf-8")


class RepoBoundaryDoctorTests(unittest.TestCase):
    def test_repo_boundary_reports_missing_boundary_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = _initialized_project(root)
            (root / "mythic_vibe_cli").mkdir(parents=True, exist_ok=True)

            errors, _warnings = workflow.doctor(repo_boundary=True)

            self.assertTrue(any("Missing repo boundary file: REPO_BOUNDARY.md" in item for item in errors))

    def test_repo_boundary_detects_forbidden_active_runtime_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = _initialized_project(root)
            _write_boundary_docs(root)
            package = root / "mythic_vibe_cli"
            package.mkdir(parents=True, exist_ok=True)
            (package / "bad_import.py").write_text(
                "from yggdrasil.router import route\n",
                encoding="utf-8",
            )

            errors, _warnings = workflow.doctor(repo_boundary=True)

            self.assertTrue(any("Forbidden active runtime import" in item for item in errors))
            self.assertTrue(any("yggdrasil.router" in item for item in errors))

    def test_repo_boundary_allows_internal_active_runtime_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = _initialized_project(root)
            _write_boundary_docs(root)
            package = root / "mythic_vibe_cli"
            package.mkdir(parents=True, exist_ok=True)
            (package / "good_import.py").write_text(
                "from .workflow import MythicWorkflow\n"
                "from mythic_vibe_cli.config import ConfigStore\n",
                encoding="utf-8",
            )

            errors, _warnings = workflow.doctor(repo_boundary=True)

            self.assertEqual(errors, [])

    def test_cli_repo_boundary_mode_does_not_require_project_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_boundary_docs(root)
            package = root / "mythic_vibe_cli"
            package.mkdir(parents=True, exist_ok=True)
            (package / "__init__.py").write_text("", encoding="utf-8")

            code = main(["doctor", "--repo-boundary", "--path", str(root)])

            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
