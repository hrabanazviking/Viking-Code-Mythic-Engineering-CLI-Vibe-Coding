from __future__ import annotations

from pathlib import Path
import unittest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10 only.
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        from pip._vendor import tomli as tomllib


class PackagingContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    def test_console_scripts_and_metadata_are_release_ready(self) -> None:
        project = self.pyproject["project"]
        scripts = project["scripts"]
        urls = project["urls"]

        self.assertEqual(scripts["mythic-vibe"], "mythic_vibe_cli.cli:main")
        self.assertEqual(scripts["mythic"], "mythic_vibe_cli.cli:main")
        self.assertIn("Repository", urls)
        self.assertIn("Issues", urls)
        self.assertIn("Changelog", urls)
        self.assertIn("Programming Language :: Python :: 3.12", project["classifiers"])

    def test_optional_dependency_groups_cover_stage_13_contract(self) -> None:
        optional = self.pyproject["project"]["optional-dependencies"]

        for group in ["dev", "ai", "docs", "test", "lint", "type", "build"]:
            self.assertIn(group, optional)
            self.assertTrue(optional[group], f"{group} optional dependency group should not be empty")

        self.assertTrue(any(item.startswith("pytest-cov") for item in optional["test"]))
        self.assertTrue(any(item.startswith("ruff") for item in optional["lint"]))
        self.assertTrue(any(item.startswith("mypy") for item in optional["type"]))
        self.assertTrue(any(item.startswith("build") for item in optional["build"]))

    def test_tooling_configuration_exists(self) -> None:
        tool = self.pyproject["tool"]

        self.assertIn("ruff", tool)
        self.assertIn("mypy", tool)
        self.assertIn("coverage", tool)

    def test_release_docs_and_ci_exist(self) -> None:
        self.assertTrue(Path(".github/workflows/ci.yml").exists())
        self.assertTrue(Path("docs/INSTALL.md").exists())
        self.assertTrue(Path("docs/RELEASE_CHECKLIST.md").exists())
        self.assertTrue(Path("scripts/check_changelog.py").exists())


if __name__ == "__main__":
    unittest.main()
