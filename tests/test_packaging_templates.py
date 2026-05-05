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
# Phase 21.7 (PH-21 distribution expansion 2026-05-05).
AUR_PKGBUILD_TEMPLATE = PACKAGING_DIR / "aur" / "PKGBUILD.template"
AUR_SRCINFO_TEMPLATE = PACKAGING_DIR / "aur" / ".SRCINFO.template"
# Phase 21.8 (PH-21 distribution expansion 2026-05-05).
WINGET_INSTALLER_TEMPLATE = (
    PACKAGING_DIR / "winget" / "mythic-vibe.installer.yaml.template"
)
WINGET_LOCALE_TEMPLATE = (
    PACKAGING_DIR / "winget" / "mythic-vibe.locale.en-US.yaml.template"
)
WINGET_VERSION_TEMPLATE = (
    PACKAGING_DIR / "winget" / "mythic-vibe.yaml.template"
)

# Sample values that mimic what release.yml substitutes.
SAMPLE_VERSION = "1.2.3"
SAMPLE_SDIST_SHA = "a" * 64
SAMPLE_WHEEL_SHA = "b" * 64
SAMPLE_WINDOWS_URL = (
    "https://github.com/owner/repo/releases/download/v1.2.3/"
    "mythic-vibe-1.2.3-windows-x86_64.exe"
)
SAMPLE_WINDOWS_SHA = "C" * 64
SAMPLE_RELEASE_DATE = "2026-05-05"
SAMPLE_RELEASE_NOTES_URL = (
    "https://github.com/owner/repo/releases/tag/v1.2.3"
)


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


class AurPkgbuildTemplateTests(unittest.TestCase):
    """Phase 21.7 — AUR PKGBUILD template render-time sanity.

    The PKGBUILD is consumed by ``release.yml``'s ``update-aur`` job
    via the same ``sed`` substitution pattern as Homebrew + Scoop.
    Render it, then assert the result has the structural shape AUR
    expects — pkgname / pkgver / sha256sums / build / package
    sections all present and balanced.
    """

    def setUp(self) -> None:
        self.assertTrue(
            AUR_PKGBUILD_TEMPLATE.is_file(),
            f"AUR PKGBUILD template missing at {AUR_PKGBUILD_TEMPLATE}",
        )
        self.raw = AUR_PKGBUILD_TEMPLATE.read_text(encoding="utf-8")

    def test_declares_required_placeholders(self) -> None:
        self.assertIn("__VERSION__", self.raw)
        self.assertIn("__SDIST_SHA256__", self.raw)

    def test_substitution_removes_all_placeholders(self) -> None:
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__SDIST_SHA256__", SAMPLE_SDIST_SHA
        )
        leftover = re.findall(r"__[A-Z0-9_]+__", rendered)
        self.assertEqual(
            leftover, [],
            f"unrendered placeholders in PKGBUILD: {leftover}",
        )

    def test_rendered_pkgbuild_has_required_aur_fields(self) -> None:
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__SDIST_SHA256__", SAMPLE_SDIST_SHA
        )
        # Standard AUR PKGBUILD field set per
        # https://wiki.archlinux.org/title/PKGBUILD .
        self.assertIn("pkgname=mythic-vibe-cli", rendered)
        self.assertIn(f"pkgver={SAMPLE_VERSION}", rendered)
        self.assertIn("pkgrel=", rendered)
        self.assertIn("arch=('any')", rendered)
        self.assertIn("license=('Apache-2.0')", rendered)
        # Pure-Python packages should depend on python (not a
        # pinned interpreter) per AUR Python guidelines.
        self.assertRegex(rendered, r"depends=\(.*python.*\)")
        # The sample sha must appear inside the sha256sums array.
        self.assertIn(f"sha256sums=('{SAMPLE_SDIST_SHA}')", rendered)
        # build() and package() functions must both be defined.
        self.assertRegex(rendered, r"\bbuild\s*\(\)")
        self.assertRegex(rendered, r"\bpackage\s*\(\)")

    def test_pkgbuild_uses_pypi_sdist_url(self) -> None:
        """AUR users get the same bytes PyPI users get — install
        from the published sdist, not from a git ref. Mirrors the
        Homebrew formula's url field."""
        self.assertIn(
            "https://files.pythonhosted.org/packages/source/m/mythic-vibe-cli/",
            self.raw,
        )


class AurSrcinfoTemplateTests(unittest.TestCase):
    """Phase 21.7 — AUR .SRCINFO template render-time sanity.

    .SRCINFO is the machine-readable summary AUR derives from the
    PKGBUILD. The maintainer repo holds both files; the .SRCINFO
    must stay in sync with the PKGBUILD or AUR rejects the package
    push. Render the template and assert the line-based key/value
    format AUR requires."""

    def setUp(self) -> None:
        self.assertTrue(
            AUR_SRCINFO_TEMPLATE.is_file(),
            f"AUR .SRCINFO template missing at {AUR_SRCINFO_TEMPLATE}",
        )
        self.raw = AUR_SRCINFO_TEMPLATE.read_text(encoding="utf-8")

    def test_declares_required_placeholders(self) -> None:
        self.assertIn("__VERSION__", self.raw)
        self.assertIn("__SDIST_SHA256__", self.raw)

    def test_substitution_removes_all_placeholders(self) -> None:
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__SDIST_SHA256__", SAMPLE_SDIST_SHA
        )
        leftover = re.findall(r"__[A-Z0-9_]+__", rendered)
        self.assertEqual(
            leftover, [],
            f"unrendered placeholders in .SRCINFO: {leftover}",
        )

    def test_rendered_srcinfo_has_pkgbase_and_pkgname(self) -> None:
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__SDIST_SHA256__", SAMPLE_SDIST_SHA
        )
        # Required top-level keys for AUR .SRCINFO.
        self.assertIn("pkgbase = mythic-vibe-cli", rendered)
        self.assertIn("pkgname = mythic-vibe-cli", rendered)
        self.assertIn(f"pkgver = {SAMPLE_VERSION}", rendered)
        self.assertIn(f"sha256sums = {SAMPLE_SDIST_SHA}", rendered)


class WingetInstallerTemplateTests(unittest.TestCase):
    """Phase 21.8 — winget Installer manifest render-time sanity.

    The release workflow renders this template with the Windows
    binary URL + sha256 from the PH-21.2 PyInstaller release, then
    submits the result as part of a winget-pkgs PR. Catches
    template drift before the manifest hits Microsoft's review.
    """

    def setUp(self) -> None:
        self.assertTrue(
            WINGET_INSTALLER_TEMPLATE.is_file(),
            f"winget installer template missing at {WINGET_INSTALLER_TEMPLATE}",
        )
        self.raw = WINGET_INSTALLER_TEMPLATE.read_text(encoding="utf-8")

    def test_declares_required_placeholders(self) -> None:
        for placeholder in (
            "__VERSION__",
            "__WINDOWS_BINARY_URL__",
            "__WINDOWS_BINARY_SHA256__",
            "__RELEASE_DATE__",
        ):
            self.assertIn(placeholder, self.raw)

    def test_substitution_removes_all_placeholders(self) -> None:
        rendered = (
            self.raw.replace("__VERSION__", SAMPLE_VERSION)
            .replace("__WINDOWS_BINARY_URL__", SAMPLE_WINDOWS_URL)
            .replace("__WINDOWS_BINARY_SHA256__", SAMPLE_WINDOWS_SHA)
            .replace("__RELEASE_DATE__", SAMPLE_RELEASE_DATE)
        )
        leftover = re.findall(r"__[A-Z0-9_]+__", rendered)
        self.assertEqual(
            leftover, [],
            f"unrendered placeholders in installer manifest: {leftover}",
        )

    def test_uses_portable_installer_type(self) -> None:
        # Portable matches PH-21.2's PyInstaller-built single-file
        # binary — winget extracts to a known location and adds to
        # PATH; no installer chrome.
        self.assertIn("InstallerType: portable", self.raw)

    def test_declares_command_aliases(self) -> None:
        # Both mythic-vibe and the mythic short alias must appear in
        # the Commands array — matches the pyproject.toml console-
        # scripts entry points so winget operators see both on PATH.
        self.assertRegex(self.raw, r"Commands:\s*\n\s+-\s+mythic-vibe")
        self.assertRegex(self.raw, r"-\s+mythic\b")

    def test_uses_x64_architecture(self) -> None:
        # PH-21.2 builds a windows-x86_64 binary; the installer
        # manifest's Architecture must match.
        self.assertIn("Architecture: x64", self.raw)

    def test_manifest_version_is_modern(self) -> None:
        # winget v1.6+ format. Older formats are accepted but use
        # different field names; staying current avoids a future
        # forced migration.
        self.assertIn("ManifestType: installer", self.raw)
        self.assertIn("ManifestVersion: 1.6.0", self.raw)


class WingetLocaleTemplateTests(unittest.TestCase):
    """Phase 21.8 — winget default-locale manifest sanity."""

    def setUp(self) -> None:
        self.assertTrue(
            WINGET_LOCALE_TEMPLATE.is_file(),
            f"winget locale template missing at {WINGET_LOCALE_TEMPLATE}",
        )
        self.raw = WINGET_LOCALE_TEMPLATE.read_text(encoding="utf-8")

    def test_declares_required_placeholders(self) -> None:
        self.assertIn("__VERSION__", self.raw)
        self.assertIn("__RELEASE_NOTES_URL__", self.raw)

    def test_substitution_removes_all_placeholders(self) -> None:
        rendered = self.raw.replace(
            "__VERSION__", SAMPLE_VERSION
        ).replace(
            "__RELEASE_NOTES_URL__", SAMPLE_RELEASE_NOTES_URL
        )
        leftover = re.findall(r"__[A-Z0-9_]+__", rendered)
        self.assertEqual(
            leftover, [],
            f"unrendered placeholders in locale manifest: {leftover}",
        )

    def test_declares_apache_license(self) -> None:
        self.assertIn("License: Apache-2.0", self.raw)

    def test_includes_publisher_metadata(self) -> None:
        # winget-pkgs review checks publisher, support, and homepage
        # URLs; missing fields fail validation.
        self.assertIn("Publisher: Mythic Vibe Contributors", self.raw)
        self.assertIn("PublisherUrl:", self.raw)
        self.assertIn("PackageName: Mythic Vibe CLI", self.raw)

    def test_manifest_version_is_modern(self) -> None:
        self.assertIn("ManifestType: defaultLocale", self.raw)
        self.assertIn("PackageLocale: en-US", self.raw)
        self.assertIn("ManifestVersion: 1.6.0", self.raw)


class WingetVersionTemplateTests(unittest.TestCase):
    """Phase 21.8 — winget version manifest sanity (the top-level
    pointer file)."""

    def setUp(self) -> None:
        self.assertTrue(
            WINGET_VERSION_TEMPLATE.is_file(),
            f"winget version template missing at {WINGET_VERSION_TEMPLATE}",
        )
        self.raw = WINGET_VERSION_TEMPLATE.read_text(encoding="utf-8")

    def test_declares_required_placeholders(self) -> None:
        self.assertIn("__VERSION__", self.raw)

    def test_substitution_removes_all_placeholders(self) -> None:
        rendered = self.raw.replace("__VERSION__", SAMPLE_VERSION)
        leftover = re.findall(r"__[A-Z0-9_]+__", rendered)
        self.assertEqual(
            leftover, [],
            f"unrendered placeholders in version manifest: {leftover}",
        )

    def test_default_locale_matches_locale_template(self) -> None:
        # The version manifest's DefaultLocale must point at the
        # locale file's PackageLocale. Drift here breaks the
        # manifest set's internal references.
        self.assertIn("DefaultLocale: en-US", self.raw)

    def test_manifest_version_is_modern(self) -> None:
        self.assertIn("ManifestType: version", self.raw)
        self.assertIn("ManifestVersion: 1.6.0", self.raw)


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

    def test_references_aur_templates(self) -> None:
        # Phase 21.7 — AUR maintainer-repo update job.
        self.assertIn(
            "packaging/aur/PKGBUILD.template", self.raw
        )
        self.assertIn(
            "packaging/aur/.SRCINFO.template", self.raw
        )

    def test_aur_job_uses_aur_bump_token(self) -> None:
        # Match the secret-naming convention TAP_BUMP_TOKEN /
        # BUCKET_BUMP_TOKEN already use.
        self.assertIn("AUR_BUMP_TOKEN", self.raw)

    def test_references_winget_templates(self) -> None:
        # Phase 21.8 — winget channel.
        self.assertIn(
            "packaging/winget/mythic-vibe.installer.yaml.template", self.raw
        )
        self.assertIn(
            "packaging/winget/mythic-vibe.locale.en-US.yaml.template", self.raw
        )
        self.assertIn(
            "packaging/winget/mythic-vibe.yaml.template", self.raw
        )

    def test_winget_job_uses_winget_bump_token(self) -> None:
        self.assertIn("WINGET_BUMP_TOKEN", self.raw)

    def test_winget_resolves_windows_binary_from_release_assets(self) -> None:
        # The job must look up the Windows binary in the release
        # assets, not assume a hardcoded URL — that lets us refactor
        # PH-21.2 naming without breaking PH-21.8.
        self.assertIn("mythic-vibe-${VERSION}-windows-x86_64.exe", self.raw)

    def test_signs_artifacts_with_sigstore(self) -> None:
        # Phase 21.5 — keyless signing over wheel + sdist + sbom.
        self.assertIn("sigstore/gh-action-sigstore-python", self.raw)
        # The action must reference all three artifact families.
        self.assertIn("dist/*.whl", self.raw)
        self.assertIn("dist/*.tar.gz", self.raw)
        self.assertIn("dist/sbom.json", self.raw)

    def test_uploads_sigstore_bundles_to_release(self) -> None:
        # The .sigstore bundles must ship to operators alongside the
        # artifacts they sign — a signature stored only inside CI
        # is useless for verification.
        self.assertIn("dist/*.sigstore", self.raw)

    def test_runs_sbom_regen(self) -> None:
        self.assertIn("scripts/regenerate_sbom.py", self.raw)

    def test_validates_distributions_with_twine(self) -> None:
        self.assertIn("twine check", self.raw)

    def test_builds_wheelhouse(self) -> None:
        self.assertIn("wheelhouse", self.raw)
        self.assertIn("pip wheel", self.raw)


if __name__ == "__main__":
    unittest.main()
