"""Phase 23.1 — mkdocs-material site structural sanity.

We can't run `mkdocs build` here (mkdocs-material isn't a default
test dep — it lives behind the [docs] extra). The CI workflow
runs the strict build on every PR; this test catches the slower
class of regressions (broken nav references, stale yml shape)
at PR time before the workflow even spins up.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
MKDOCS_YML = REPO_ROOT / "mkdocs.yml"
DOCS_DIR = REPO_ROOT / "docs"
DOCS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs.yml"
PYPROJECT = REPO_ROOT / "pyproject.toml"


class MkdocsConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            MKDOCS_YML.is_file(),
            f"mkdocs.yml missing at {MKDOCS_YML}",
        )
        self.raw = MKDOCS_YML.read_text(encoding="utf-8")

    def test_uses_material_theme(self) -> None:
        # Theme block: `theme:` then indented `name: material`.
        self.assertTrue(
            re.search(r"theme:\s*\n\s+name:\s*material\b", self.raw),
            "mkdocs.yml must declare theme.name = material",
        )

    def test_declares_site_metadata(self) -> None:
        for field in (
            "site_name:",
            "site_description:",
            "site_url:",
            "site_author:",
            "repo_url:",
            "edit_uri:",
        ):
            self.assertIn(field, self.raw)

    def test_enables_search_plugin(self) -> None:
        # Search is the highest-value mkdocs-material feature for
        # operators landing on the site without a specific doc in
        # mind. The plugin entry appears under the `plugins:` block.
        self.assertTrue(
            re.search(r"plugins:\s*\n\s+-\s+search\b", self.raw),
            "mkdocs.yml must enable the search plugin",
        )

    def test_enables_code_copy_button(self) -> None:
        # Operators copy commands frequently — content.code.copy
        # is the per-block clipboard button feature.
        self.assertIn("content.code.copy", self.raw)

    def test_enables_palette_toggle(self) -> None:
        # Light / dark mode is a 30-second feature operators expect.
        self.assertIn("toggle:", self.raw)
        self.assertIn("Switch to dark mode", self.raw)
        self.assertIn("Switch to light mode", self.raw)


class NavEntryFilesExistTests(unittest.TestCase):
    """Every nav entry in mkdocs.yml must point at a real file
    under docs/. Strict-mode mkdocs build catches this at CI time;
    we catch it at PR time (faster feedback, no docs deps needed).
    """

    def setUp(self) -> None:
        self.raw = MKDOCS_YML.read_text(encoding="utf-8")

    def _nav_paths(self) -> list[str]:
        # Match any `: <path>` occurrence under the nav: block.
        # Matching the whole nav YAML structure properly would
        # require a real YAML parser; the regex picks up `: foo.md`
        # / `: foo/bar.md` lines under nav.
        in_nav = False
        paths: list[str] = []
        for line in self.raw.splitlines():
            if line.startswith("nav:"):
                in_nav = True
                continue
            if in_nav and line and not line.startswith(("  ", "\t", "-", "#")):
                # New top-level key — nav block is over.
                in_nav = False
            if in_nav:
                m = re.search(r":\s*([\w./-]+\.md)\s*$", line)
                if m:
                    paths.append(m.group(1))
        return paths

    def test_extracts_nav_paths(self) -> None:
        # Smoke-check the parser found a non-empty list. Otherwise
        # the rest of the test class is silently a no-op.
        paths = self._nav_paths()
        self.assertGreater(
            len(paths), 5,
            f"expected several nav paths, got {paths}",
        )

    def test_every_nav_entry_resolves_to_real_file(self) -> None:
        for rel in self._nav_paths():
            target = DOCS_DIR / rel
            self.assertTrue(
                target.is_file(),
                f"nav entry refers to missing file: docs/{rel}",
            )


class SiteLandingPageTests(unittest.TestCase):
    """The home page lives at docs/INDEX.md (the upper-case path
    git tracks; on case-insensitive filesystems mkdocs reads the
    same file via index.md). Smoke-check it has the operator-
    facing landing content, not the legacy contributor index."""

    def test_landing_includes_install_quickstart(self) -> None:
        landing = DOCS_DIR / "INDEX.md"
        self.assertTrue(landing.is_file())
        text = landing.read_text(encoding="utf-8")
        # Operator-facing markers — these don't appear in the old
        # contributor-orientation hub.
        self.assertIn("pipx install mythic-vibe-cli", text)
        self.assertIn("Where to start", text)
        self.assertIn("Distribution channels", text)

    def test_contributor_index_preserved(self) -> None:
        # The old index content must live on at the new path so
        # the additive-only rule isn't violated.
        contributor = DOCS_DIR / "contributor_index.md"
        self.assertTrue(contributor.is_file())
        text = contributor.read_text(encoding="utf-8")
        self.assertIn("Documentation Hub", text)
        self.assertIn("Boundary And Architecture", text)


class DocsWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            DOCS_WORKFLOW.is_file(),
            f"docs.yml workflow missing at {DOCS_WORKFLOW}",
        )
        self.raw = DOCS_WORKFLOW.read_text(encoding="utf-8")

    def test_runs_on_pr_and_main_push(self) -> None:
        self.assertIn("pull_request:", self.raw)
        self.assertIn("main", self.raw)
        self.assertIn("development", self.raw)

    def test_strict_build_gate(self) -> None:
        # Strict mode is the whole reason this workflow exists.
        # Without --strict, broken nav links + missing files ship
        # to docs.<repo>.io silently.
        self.assertIn("mkdocs build --strict", self.raw)

    def test_installs_docs_extra(self) -> None:
        # Installing -e ".[docs]" pulls in mkdocs-material +
        # pymdown-extensions per pyproject.toml.
        self.assertIn(".[docs]", self.raw)

    def test_deploys_to_github_pages_only_on_main(self) -> None:
        # PR + development branches build but don't deploy. The
        # gating expression must reference both refs/heads/main
        # AND github.event_name == push.
        self.assertIn("refs/heads/main", self.raw)
        self.assertIn("github.event_name == 'push'", self.raw)

    def test_uses_actions_deploy_pages(self) -> None:
        self.assertIn("actions/deploy-pages", self.raw)
        self.assertIn("actions/upload-pages-artifact", self.raw)

    def test_has_pages_concurrency_lock(self) -> None:
        # Only one concurrent deployment so a fast follow-up
        # push doesn't deploy stale content over fresh content.
        self.assertIn("concurrency:", self.raw)
        self.assertIn("group: pages", self.raw)


class PyprojectDocsExtraTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(PYPROJECT.is_file())
        self.raw = PYPROJECT.read_text(encoding="utf-8")

    def test_docs_extra_pins_mkdocs_material(self) -> None:
        # The [docs] extra is what `pip install -e ".[docs]"` in
        # the workflow pulls. mkdocs-material must be present or
        # the strict build fails at theme resolution.
        self.assertIn('"mkdocs-material>=', self.raw)

    def test_docs_extra_pins_pymdown_extensions(self) -> None:
        # mkdocs.yml uses pymdownx.* extensions — they live in
        # the pymdown-extensions package (note the dash).
        self.assertIn('"pymdown-extensions>=', self.raw)

    def test_dev_extra_includes_docs_deps(self) -> None:
        # The [dev] superset must include the docs deps so a
        # contributor running `pip install -e ".[dev]"` can
        # build the site without an extra install step.
        # Check both packages are listed in the dev extras block.
        # Use a regex to find the [dev] block specifically rather
        # than any occurrence in the file.
        dev_match = re.search(
            r'dev\s*=\s*\[(.+?)\]', self.raw, re.DOTALL,
        )
        self.assertIsNotNone(dev_match, "dev extras block missing")
        dev_block = dev_match.group(1)
        self.assertIn("mkdocs-material", dev_block)
        self.assertIn("pymdown-extensions", dev_block)


if __name__ == "__main__":
    unittest.main()
