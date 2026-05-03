"""Phase 19.5 (audit remediation 2026-05-02) — committed-SBOM
sanity tests.

The SBOM at ``docs/security/sbom.json`` is the reference artifact
operators and auditors use to understand what packages ship with
Mythic Vibe CLI. We don't regenerate it inside CI on every PR
(that would require a clean venv build per run and slow CI down
without much value), but we DO assert that the committed file is
well-formed and contains the project root component plus a
plausible number of dependencies.

The goal: catch "someone hand-edited the file into garbage" or
"someone deleted half of it" before a release goes out.

Regeneration is the operator's responsibility and is done via
``python scripts/regenerate_sbom.py``. The release workflow
(PH-19.7) re-runs that script and fails the release if the file
diff is non-trivial — that's where freshness is enforced.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path


SBOM_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs" / "security" / "sbom.json"
)


class CommittedSbomTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            SBOM_PATH.is_file(),
            f"SBOM missing at {SBOM_PATH}. "
            "Run `python scripts/regenerate_sbom.py` to recreate it.",
        )
        try:
            self.payload = json.loads(SBOM_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self.fail(f"SBOM is not valid JSON: {exc}")

    def test_uses_cyclonedx_format(self) -> None:
        """We standardise on CycloneDX. Anything else means
        someone swapped tooling without updating the docs."""
        self.assertEqual(self.payload.get("bomFormat"), "CycloneDX")

    def test_spec_version_is_recent(self) -> None:
        """CycloneDX 1.x — accept any 1.x because spec versions
        bump every few months and we don't want to chase them
        with a test on every regen. Reject 0.x or unknown."""
        spec = self.payload.get("specVersion", "")
        self.assertTrue(
            spec.startswith("1."),
            f"unexpected CycloneDX specVersion: {spec!r}",
        )

    def test_root_component_is_mythic_vibe_cli(self) -> None:
        """The metadata.component block is the SBOM's "what is
        this an SBOM of?" pointer. If it's missing or wrong,
        downstream tooling can't tell which project the SBOM
        describes."""
        component = self.payload.get("metadata", {}).get("component", {})
        self.assertEqual(component.get("name"), "mythic-vibe-cli")

    def test_components_list_is_non_trivial(self) -> None:
        """The current SBOM has ~85 components (project + ai +
        otel + ux + tui + transitives). Any number under 20 means
        the file was truncated, generated against the wrong
        environment, or generated from a venv that didn't install
        the expected extras."""
        components = self.payload.get("components", [])
        self.assertIsInstance(components, list)
        self.assertGreaterEqual(
            len(components), 20,
            f"SBOM only has {len(components)} components — likely "
            "regenerated against the wrong environment. Re-run "
            "scripts/regenerate_sbom.py.",
        )

    def test_every_component_has_name_and_version(self) -> None:
        """A component without a name+version pair is useless for
        downstream vulnerability matching. Catch it here rather
        than waiting for a security-scanner to silently skip it."""
        components = self.payload.get("components", [])
        broken: list[str] = []
        for entry in components:
            if not entry.get("name") or not entry.get("version"):
                broken.append(entry.get("bom-ref", "<no-bom-ref>"))
        self.assertEqual(
            broken, [],
            f"components missing name/version: {broken[:5]}",
        )


if __name__ == "__main__":
    unittest.main()
