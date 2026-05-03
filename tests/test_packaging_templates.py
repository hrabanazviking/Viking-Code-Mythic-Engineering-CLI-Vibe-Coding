"""Phase 19.7 (audit remediation 2026-05-02) — packaging template
sanity tests.

The Homebrew formula and Scoop manifest templates are consumed by
``.github/workflows/release.yml`` via ``sed``-based substitution
of ``__VERSION__`` + ``__SDIST_SHA256__`` / ``__WHEEL_SHA256__``
placeholders.

Substitution failures (typos, removed placeholders, broken
template syntax) only surface at *release time* — i.e. the first
notice would be a failed PR against the tap or bucket repo,
which is too late.

These tests render the templates with sample values and assert
the result is structurally valid so we catch the failure on
every PR instead.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGING_DIR = REPO_ROOT / "packaging"
HOMEBREW_TEMPLATE = PACKAGING_DIR / "homebrew" / "mythic-vibe.rb.template"
SCOOP_TEMPLATE = PACKAGING_DIR / "scoop" / "mythic-vibe.json.template"

# Sample values that mimic what release.yml substitutes.
SAMPLE_VERSION = "1.2.3"
SAMPLE_SDIST_SHA = "a" * 64
SAMPLE_WHEEL_SHA = "b" * 64


class HomebrewTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            HOMEBREW_TEMPLATE.is_file(),
            f"Homebrew template missing at {HOMEBREW_TEMPLATE}",
        )
        self.raw = HOMEBREW_TEMPLATE.read_text(encoding="utf-8")

    def test_declares_required_placeholders(self) -> None:
        """release.yml expects exactly these two substitution
        markers. If a template author drops or renames one, the
        sed pipeline silently produces a broken formula."""
        self.assertIn("__VERSION__", self.raw)
        self.assertIn("__SDIST_SHA256__", self.raw)

    def test_substitution_removes_all_placeholders(self) -> None:
        """After release.yml's two sed passes, no __PLACEHOLDER__
        markers should remain. Anything left over means the
        formula will publish with a literal __FOO__ string."""
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__SDIST_SHA256__", SAMPLE_SDIST_SHA
        )
        leftover = re.findall(r"__[A-Z0-9_]+__", rendered)
        self.assertEqual(
            leftover, [],
            f"unrendered placeholders in formula: {leftover}",
        )

    def test_rendered_formula_is_well_formed_ruby(self) -> None:
        """The Ruby Homebrew DSL is line-oriented enough that we
        can sanity-check structure without invoking ruby. We
        check that the class declaration, install method, and
        test block all close cleanly."""
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__SDIST_SHA256__", SAMPLE_SDIST_SHA
        )
        self.assertRegex(rendered, r"\bclass MythicVibe\b")
        self.assertIn('url "https://files.pythonhosted.org/', rendered)
        self.assertIn(f'sha256 "{SAMPLE_SDIST_SHA}"', rendered)
        # ``end`` count ≥ 3 (class + install + test). The exact
        # number can vary if helpers are added, so check ≥ 3
        # rather than == 3.
        end_count = sum(
            1 for line in rendered.splitlines()
            if line.strip() == "end"
        )
        self.assertGreaterEqual(
            end_count, 3,
            f"too few `end` keywords ({end_count}) — formula is "
            "unbalanced",
        )


class ScoopTemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SCOOP_TEMPLATE.is_file(),
            f"Scoop template missing at {SCOOP_TEMPLATE}",
        )
        self.raw = SCOOP_TEMPLATE.read_text(encoding="utf-8")

    def test_declares_required_placeholders(self) -> None:
        self.assertIn("__VERSION__", self.raw)
        self.assertIn("__WHEEL_SHA256__", self.raw)

    def test_renders_to_valid_json(self) -> None:
        """The Scoop manifest must be valid JSON. The template is
        already valid JSON with placeholder values inline; after
        substitution with realistic sha256 + version it must
        still parse."""
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__WHEEL_SHA256__", SAMPLE_WHEEL_SHA
        )
        try:
            parsed = json.loads(rendered)
        except json.JSONDecodeError as exc:
            self.fail(f"rendered manifest is not valid JSON: {exc}")
        # Required Scoop manifest fields per the spec.
        self.assertEqual(parsed.get("version"), SAMPLE_VERSION)
        self.assertEqual(parsed.get("hash"), f"sha256:{SAMPLE_WHEEL_SHA}")
        self.assertIn("url", parsed)
        self.assertIn("bin", parsed)
        self.assertIn("installer", parsed)
        # bin entries: list of [path, alias] pairs.
        for entry in parsed["bin"]:
            self.assertEqual(len(entry), 2)

    def test_substitution_removes_all_placeholders(self) -> None:
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__WHEEL_SHA256__", SAMPLE_WHEEL_SHA
        )
        leftover = re.findall(r"__[A-Z0-9_]+__", rendered)
        self.assertEqual(
            leftover, [],
            f"unrendered placeholders in manifest: {leftover}",
        )


class ReleaseWorkflowTests(unittest.TestCase):
    """Sanity-check that ``.github/workflows/release.yml`` exists
    and references the expected templates + secrets. Catches the
    "someone renamed a template but forgot to update the
    workflow" regression."""

    def setUp(self) -> None:
        self.workflow_path = (
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        self.assertTrue(
            self.workflow_path.is_file(),
            f"release workflow missing at {self.workflow_path}",
        )
        self.raw = self.workflow_path.read_text(encoding="utf-8")

    def test_publishes_via_oidc_trusted_publishing(self) -> None:
        """The PyPI step must use the official action — long-lived
        API tokens in repo secrets are explicitly out per the
        threat model."""
        self.assertIn("pypa/gh-action-pypi-publish", self.raw)
        # No long-lived PYPI_API_TOKEN reference allowed.
        self.assertNotIn("PYPI_API_TOKEN", self.raw)

    def test_references_homebrew_template(self) -> None:
        self.assertIn(
            "packaging/homebrew/mythic-vibe.rb.template", self.raw
        )

    def test_references_scoop_template(self) -> None:
        self.assertIn(
            "packaging/scoop/mythic-vibe.json.template", self.raw
        )

    def test_runs_sbom_regen(self) -> None:
        self.assertIn("scripts/regenerate_sbom.py", self.raw)

    def test_validates_distributions_with_twine(self) -> None:
        self.assertIn("twine check", self.raw)

    def test_builds_wheelhouse(self) -> None:
        self.assertIn("wheelhouse", self.raw)
        self.assertIn("pip wheel", self.raw)


if __name__ == "__main__":
    unittest.main()
