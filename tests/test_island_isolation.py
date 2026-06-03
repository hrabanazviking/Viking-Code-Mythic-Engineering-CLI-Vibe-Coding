"""Cross-island isolation tests — PH-09 Slice 9.5.

Locks the master-roadmap invariant: each of the four islands
(Yggdrasil / MindSpark / WYRD / Chatterbox) can be enabled or
disabled independently, and a missing dep on any single island
never breaks the core CLI or any other island.

These tests deliberately exercise the cross-product: each island
× (flag on/off) × (dep present/absent) = 4 axes per island, and
toggling one must never bleed into the others.
"""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest import mock


# Centralised env-var registry so the tests stay declarative.
ISLAND_ENV_VARS = (
    "MYTHIC_ISLAND_YGGDRASIL_ENABLED",
    "MYTHIC_ISLAND_MINDSPARK_ENABLED",
    "MYTHIC_ISLAND_WYRD_ENABLED",
    "MYTHIC_ISLAND_CHATTERBOX_ENABLED",
    # The broader voice gate isn't an island flag itself but it
    # interacts with chatterbox; clear it for hermetic island tests.
    "MYTHIC_VOICE_TTS_ENABLED",
)


class _IslandEnvBase(unittest.TestCase):
    """Captures + restores all island env vars per test so flag
    interactions stay hermetic."""

    def setUp(self) -> None:
        self._previous: dict[str, str | None] = {
            name: os.environ.pop(name, None) for name in ISLAND_ENV_VARS
        }

    def tearDown(self) -> None:
        for name in ISLAND_ENV_VARS:
            os.environ.pop(name, None)
        for name, value in self._previous.items():
            if value is not None:
                os.environ[name] = value


# ---- Default-off invariant -------------------------------------------


class AllIslandsDefaultOffTests(_IslandEnvBase):
    """With NO env vars set, every island reports as not enabled.
    This is the master-roadmap guarantee that PH-09 changes nothing
    for projects that don't opt in."""

    def test_yggdrasil_default_off(self) -> None:
        from mythic_vibe_cli.ai.providers.yggdrasil import is_island_enabled
        self.assertFalse(is_island_enabled())

    def test_mindspark_default_off(self) -> None:
        from mythic_vibe_cli.ai.providers.mindspark import is_island_enabled
        self.assertFalse(is_island_enabled())

    def test_wyrd_default_off(self) -> None:
        from mythic_vibe_cli.verify.wyrd_oracle import is_island_enabled
        self.assertFalse(is_island_enabled())

    def test_chatterbox_default_off(self) -> None:
        from mythic_vibe_cli.voice.tts import is_chatterbox_island_enabled
        self.assertFalse(is_chatterbox_island_enabled())


# ---- Independence: toggling one doesn't bleed into the others --------


class IndependentToggleTests(_IslandEnvBase):
    """Each island flag operates independently. Setting one must
    never enable any other."""

    def test_yggdrasil_on_does_not_enable_others(self) -> None:
        from mythic_vibe_cli.ai.providers.mindspark import (
            is_island_enabled as ms_enabled,
        )
        from mythic_vibe_cli.ai.providers.yggdrasil import (
            is_island_enabled as ygg_enabled,
        )
        from mythic_vibe_cli.verify.wyrd_oracle import (
            is_island_enabled as wyrd_enabled,
        )
        from mythic_vibe_cli.voice.tts import is_chatterbox_island_enabled

        os.environ["MYTHIC_ISLAND_YGGDRASIL_ENABLED"] = "1"
        self.assertTrue(ygg_enabled())
        self.assertFalse(ms_enabled())
        self.assertFalse(wyrd_enabled())
        self.assertFalse(is_chatterbox_island_enabled())

    def test_mindspark_on_does_not_enable_others(self) -> None:
        from mythic_vibe_cli.ai.providers.mindspark import (
            is_island_enabled as ms_enabled,
        )
        from mythic_vibe_cli.ai.providers.yggdrasil import (
            is_island_enabled as ygg_enabled,
        )
        from mythic_vibe_cli.verify.wyrd_oracle import (
            is_island_enabled as wyrd_enabled,
        )
        from mythic_vibe_cli.voice.tts import is_chatterbox_island_enabled

        os.environ["MYTHIC_ISLAND_MINDSPARK_ENABLED"] = "1"
        self.assertTrue(ms_enabled())
        self.assertFalse(ygg_enabled())
        self.assertFalse(wyrd_enabled())
        self.assertFalse(is_chatterbox_island_enabled())

    def test_wyrd_on_does_not_enable_others(self) -> None:
        from mythic_vibe_cli.ai.providers.mindspark import (
            is_island_enabled as ms_enabled,
        )
        from mythic_vibe_cli.ai.providers.yggdrasil import (
            is_island_enabled as ygg_enabled,
        )
        from mythic_vibe_cli.verify.wyrd_oracle import (
            is_island_enabled as wyrd_enabled,
        )
        from mythic_vibe_cli.voice.tts import is_chatterbox_island_enabled

        os.environ["MYTHIC_ISLAND_WYRD_ENABLED"] = "1"
        self.assertTrue(wyrd_enabled())
        self.assertFalse(ygg_enabled())
        self.assertFalse(ms_enabled())
        self.assertFalse(is_chatterbox_island_enabled())

    def test_chatterbox_on_does_not_enable_others(self) -> None:
        from mythic_vibe_cli.ai.providers.mindspark import (
            is_island_enabled as ms_enabled,
        )
        from mythic_vibe_cli.ai.providers.yggdrasil import (
            is_island_enabled as ygg_enabled,
        )
        from mythic_vibe_cli.verify.wyrd_oracle import (
            is_island_enabled as wyrd_enabled,
        )
        from mythic_vibe_cli.voice.tts import is_chatterbox_island_enabled

        os.environ["MYTHIC_ISLAND_CHATTERBOX_ENABLED"] = "1"
        self.assertTrue(is_chatterbox_island_enabled())
        self.assertFalse(ygg_enabled())
        self.assertFalse(ms_enabled())
        self.assertFalse(wyrd_enabled())

    def test_all_islands_can_be_on_simultaneously(self) -> None:
        """Operators may legitimately enable every island at once."""
        from mythic_vibe_cli.ai.providers.mindspark import (
            is_island_enabled as ms_enabled,
        )
        from mythic_vibe_cli.ai.providers.yggdrasil import (
            is_island_enabled as ygg_enabled,
        )
        from mythic_vibe_cli.verify.wyrd_oracle import (
            is_island_enabled as wyrd_enabled,
        )
        from mythic_vibe_cli.voice.tts import is_chatterbox_island_enabled

        for env in (
            "MYTHIC_ISLAND_YGGDRASIL_ENABLED",
            "MYTHIC_ISLAND_MINDSPARK_ENABLED",
            "MYTHIC_ISLAND_WYRD_ENABLED",
            "MYTHIC_ISLAND_CHATTERBOX_ENABLED",
        ):
            os.environ[env] = "1"

        self.assertTrue(ygg_enabled())
        self.assertTrue(ms_enabled())
        self.assertTrue(wyrd_enabled())
        self.assertTrue(is_chatterbox_island_enabled())


# ---- Missing-dep isolation -------------------------------------------


class MissingDepDoesNotBreakOthersTests(_IslandEnvBase):
    """A missing dep on any single island must never crash the core
    CLI or any other island's surface. We simulate missing deps via
    monkey-patching the try-import functions."""

    def test_missing_yggdrasil_dep_does_not_block_other_providers(self) -> None:
        from mythic_vibe_cli.ai.providers.yggdrasil import YggdrasilProvider
        from mythic_vibe_cli.ai.registry import ProviderRegistry

        # Force yggdrasil to think dep is missing.
        with mock.patch(
            "mythic_vibe_cli.ai.providers.yggdrasil._try_import_yggdrasil",
            return_value=None,
        ):
            registry = ProviderRegistry()
            providers = registry.providers()
            # Every provider in the registry should be constructible.
            for name, provider in providers.items():
                status = provider.validate_config()
                # Stub providers (copy-paste) are configured; islands
                # are not (without flag); other vendor providers
                # depend on env keys. Just assert validate_config()
                # doesn't crash.
                self.assertIsNotNone(status)
            # Yggdrasil is unconfigured (dep missing).
            ygg = providers["yggdrasil"]
            assert isinstance(ygg, YggdrasilProvider)
            self.assertFalse(ygg.validate_config().configured)
            # Other providers continue to work.
            self.assertIn("copy-paste", providers)
            self.assertTrue(providers["copy-paste"].validate_config().configured)

    def test_yggdrasil_try_import_does_not_load_dormant_repo_island(self) -> None:
        from mythic_vibe_cli.ai.providers.yggdrasil import _try_import_yggdrasil

        module = _try_import_yggdrasil()
        if module is None:
            return

        raw_path = getattr(module, "__file__", "")
        self.assertTrue(raw_path)
        module_path = Path(raw_path).resolve()
        repo_root = Path(__file__).resolve().parents[1]
        self.assertFalse(module_path.is_relative_to(repo_root / "yggdrasil"))

    def test_missing_mindspark_dep_does_not_block_other_providers(self) -> None:
        from mythic_vibe_cli.ai.providers.mindspark import MindSparkProvider
        from mythic_vibe_cli.ai.registry import ProviderRegistry

        with mock.patch(
            "mythic_vibe_cli.ai.providers.mindspark._try_import_thoughtforge",
            return_value=None,
        ):
            registry = ProviderRegistry()
            providers = registry.providers()
            ms = providers["mindspark"]
            assert isinstance(ms, MindSparkProvider)
            self.assertFalse(ms.validate_config().configured)
            self.assertTrue(providers["copy-paste"].validate_config().configured)

    def test_missing_wyrd_dep_does_not_break_default_auditor(self) -> None:
        """The WYRD oracle gate is opt-in via wyrd_gate_if_enabled().
        If it's not opted in, the default Auditor flow is unchanged
        regardless of whether wyrd is installed."""
        from mythic_vibe_cli.forge_verifier import DEFAULT_AUDITOR_GATES
        from mythic_vibe_cli.verify.wyrd_oracle import (
            GATE_NAME,
            wyrd_gate_if_enabled,
        )

        # Default registry never includes the WYRD gate.
        self.assertNotIn(GATE_NAME, DEFAULT_AUDITOR_GATES)

        # With flag off, the helper returns empty regardless of dep.
        gates = wyrd_gate_if_enabled()
        self.assertEqual(gates, {})

    def test_missing_chatterbox_dep_does_not_block_stub_engine(self) -> None:
        """Even when chatterbox isn't installed, the stub engine
        path still works. Verifies the import boundary."""
        from mythic_vibe_cli.voice.tts import (
            StubTTSEngine,
            TTS_ENABLED_ENV,
            say,
        )

        os.environ[TTS_ENABLED_ENV] = "1"
        # Island flag intentionally NOT set; we want stub path.
        import io as _io

        buf = _io.StringIO()
        result = say("hello", engine="stub", tts_engine=StubTTSEngine(stream=buf))
        # Stub path always works.
        self.assertIn("hello", buf.getvalue())
        # And the absence of MYTHIC_ISLAND_CHATTERBOX_ENABLED has no
        # effect on the stub call.
        self.assertNotIn("Chatterbox island disabled", result.skipped_reason or "")


# ---- Registry + verifier surface stays intact ------------------------


class CoreSurfaceIntactTests(_IslandEnvBase):
    """All four islands disabled (default) → CLI surface looks
    exactly like it did before PH-09 (apart from the two new
    provider-registry entries which are unconfigured)."""

    def test_all_existing_provider_keys_present(self) -> None:
        from mythic_vibe_cli.ai.registry import ProviderRegistry

        registry = ProviderRegistry()
        providers = registry.providers()
        for required in (
            "copy-paste",
            "local",
            "openai",
            "anthropic",
            "gemini",
            "openrouter",
            "ollama",
        ):
            self.assertIn(required, providers, f"missing {required}")

    def test_new_island_providers_present_but_unconfigured(self) -> None:
        from mythic_vibe_cli.ai.registry import ProviderRegistry

        registry = ProviderRegistry()
        providers = registry.providers()
        for name in ("yggdrasil", "mindspark"):
            self.assertIn(name, providers)
            self.assertFalse(providers[name].validate_config().configured)

    def test_default_auditor_gates_unchanged(self) -> None:
        """The default Auditor gate registry must still be exactly
        the three gates from slice 3.6 — no WYRD gate auto-added."""
        from mythic_vibe_cli.forge_verifier import DEFAULT_AUDITOR_GATES

        self.assertEqual(
            set(DEFAULT_AUDITOR_GATES.keys()),
            {
                "diff-reviewed-against-architecture",
                "no-invariant-violation",
                "test-evidence-recorded",
            },
        )


if __name__ == "__main__":
    unittest.main()
