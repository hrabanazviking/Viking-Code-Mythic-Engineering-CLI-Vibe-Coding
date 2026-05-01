"""Tests for PH-10 Slice 10.3 — plugin extension-point Protocols."""

from __future__ import annotations

import unittest

from mythic_vibe_cli.plugins.extension_points import (
    EXTENSION_POINT_CATEGORIES,
    ArtifactTemplatePlugin,
    ProviderPlugin,
    RitualPlugin,
    ScannerPlugin,
    SlashCommandPlugin,
    VerificationGatePlugin,
    categorise_plugin,
)


# ---- Constant guarantees ---------------------------------------------


class CategoriesConstantTests(unittest.TestCase):
    def test_contains_six_categories(self) -> None:
        self.assertEqual(len(EXTENSION_POINT_CATEGORIES), 6)

    def test_canonical_order(self) -> None:
        self.assertEqual(
            EXTENSION_POINT_CATEGORIES,
            (
                "ritual",
                "provider",
                "scanner",
                "verification_gate",
                "artifact_template",
                "slash_command",
            ),
        )


# ---- Each Protocol is runtime_checkable ------------------------------


class _RitualImpl:
    def rituals(self):  # noqa: ANN001 — duck-typed
        return ["init", "checkin"]


class _ProviderImpl:
    def providers(self):  # noqa: ANN001
        return {"my_provider": object()}


class _ScannerImpl:
    def scanner_rules(self):  # noqa: ANN001
        return [{"pattern": "*.foo"}]


class _GateImpl:
    def verification_gates(self):  # noqa: ANN001
        return {"my_gate": lambda *_a, **_kw: None}


class _TemplateImpl:
    def artifact_templates(self):  # noqa: ANN001
        return {"my_template": "body"}


class _SlashImpl:
    def slash_commands(self):  # noqa: ANN001
        return []


class _NoExtensionsImpl:
    """Bare object — implements none of the protocols."""


class _AllExtensionsImpl(
    _RitualImpl,
    _ProviderImpl,
    _ScannerImpl,
    _GateImpl,
    _TemplateImpl,
    _SlashImpl,
):
    pass


class ProtocolMembershipTests(unittest.TestCase):
    def test_ritual_protocol(self) -> None:
        self.assertTrue(isinstance(_RitualImpl(), RitualPlugin))
        self.assertFalse(isinstance(_NoExtensionsImpl(), RitualPlugin))

    def test_provider_protocol(self) -> None:
        self.assertTrue(isinstance(_ProviderImpl(), ProviderPlugin))
        self.assertFalse(isinstance(_NoExtensionsImpl(), ProviderPlugin))

    def test_scanner_protocol(self) -> None:
        self.assertTrue(isinstance(_ScannerImpl(), ScannerPlugin))
        self.assertFalse(isinstance(_NoExtensionsImpl(), ScannerPlugin))

    def test_verification_gate_protocol(self) -> None:
        self.assertTrue(isinstance(_GateImpl(), VerificationGatePlugin))
        self.assertFalse(isinstance(_NoExtensionsImpl(), VerificationGatePlugin))

    def test_artifact_template_protocol(self) -> None:
        self.assertTrue(isinstance(_TemplateImpl(), ArtifactTemplatePlugin))
        self.assertFalse(isinstance(_NoExtensionsImpl(), ArtifactTemplatePlugin))

    def test_slash_command_protocol(self) -> None:
        self.assertTrue(isinstance(_SlashImpl(), SlashCommandPlugin))
        self.assertFalse(isinstance(_NoExtensionsImpl(), SlashCommandPlugin))


# ---- categorise_plugin ----------------------------------------------


class CategoriseTests(unittest.TestCase):
    def test_no_categories_for_bare_object(self) -> None:
        self.assertEqual(categorise_plugin(_NoExtensionsImpl()), [])

    def test_single_category(self) -> None:
        self.assertEqual(categorise_plugin(_RitualImpl()), ["ritual"])

    def test_all_six_categories(self) -> None:
        result = categorise_plugin(_AllExtensionsImpl())
        self.assertEqual(set(result), set(EXTENSION_POINT_CATEGORIES))
        # Order matches canonical EXTENSION_POINT_CATEGORIES.
        self.assertEqual(result, list(EXTENSION_POINT_CATEGORIES))

    def test_two_categories_in_canonical_order(self) -> None:
        class _Mix(_SlashImpl, _RitualImpl):
            pass

        # Even though _SlashImpl appears first in MRO, the
        # canonical category order should still place ritual
        # before slash_command.
        self.assertEqual(categorise_plugin(_Mix()), ["ritual", "slash_command"])


if __name__ == "__main__":
    unittest.main()
