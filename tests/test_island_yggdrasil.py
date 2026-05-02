"""Tests for Island B (Yggdrasil) adapter — PH-09 Slice 9.1."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from mythic_vibe_cli.ai.providers.yggdrasil import (
    ISLAND_ENABLED_ENV,
    YggdrasilProvider,
    is_island_enabled,
)
from mythic_vibe_cli.ai.registry import ProviderRegistry


# ---- env gate ---------------------------------------------------------


class IsIslandEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_default_off(self) -> None:
        self.assertFalse(is_island_enabled())

    def test_truthy_values(self) -> None:
        for raw in ("1", "true", "yes", "on", "TRUE"):
            os.environ[ISLAND_ENABLED_ENV] = raw
            self.assertTrue(is_island_enabled(), f"failed for {raw!r}")

    def test_falsy_values(self) -> None:
        for raw in ("0", "false", "no", "", "off", "garbage"):
            os.environ[ISLAND_ENABLED_ENV] = raw
            self.assertFalse(is_island_enabled(), f"failed for {raw!r}")


# ---- validate_config --------------------------------------------------


class ValidateConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_unconfigured_when_dep_missing(self) -> None:
        provider = YggdrasilProvider()
        provider._module = None
        status = provider.validate_config()
        self.assertFalse(status.configured)
        self.assertTrue(any("not installed" in d for d in status.details))
        self.assertTrue(any("Install hint" in d for d in status.details))

    def test_unconfigured_when_flag_off_even_with_dep(self) -> None:
        provider = YggdrasilProvider()
        provider._module = mock.MagicMock()  # simulate dep present
        status = provider.validate_config()
        self.assertFalse(status.configured)
        self.assertTrue(any("import OK" in d for d in status.details))
        self.assertTrue(
            any(ISLAND_ENABLED_ENV in d for d in status.details)
        )

    def test_configured_when_flag_on_and_dep_present(self) -> None:
        os.environ[ISLAND_ENABLED_ENV] = "1"
        provider = YggdrasilProvider()
        provider._module = mock.MagicMock()
        status = provider.validate_config()
        self.assertTrue(status.configured)


# ---- run() ------------------------------------------------------------


class RunStubPathTests(unittest.TestCase):
    """When unconfigured, run() returns a stub response — never
    raises. The slice 8.3 fallback runtime relies on this."""

    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_stub_response_when_dep_missing(self) -> None:
        provider = YggdrasilProvider()
        provider._module = None
        response = provider.run({"text": "hello", "packet_id": "PKT-X"})
        self.assertEqual(response.provider, "yggdrasil")
        self.assertEqual(response.content, "")
        self.assertTrue(response.dry_run)
        self.assertFalse(response.metadata.get("configured", True))
        self.assertEqual(response.metadata.get("source"), "yggdrasil-stub")

    def test_stub_response_when_flag_off(self) -> None:
        provider = YggdrasilProvider()
        provider._module = mock.MagicMock()
        response = provider.run({"text": "hello", "packet_id": "PKT-X"})
        self.assertTrue(response.dry_run)
        self.assertEqual(response.metadata.get("source"), "yggdrasil-stub")


class RunRealPathTests(unittest.TestCase):
    """When configured, run() invokes the yggdrasil package's
    routing entry point and wraps the result in a ProviderResponse."""

    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)
        os.environ[ISLAND_ENABLED_ENV] = "1"

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_route_attribute_invoked(self) -> None:
        fake = mock.MagicMock()
        fake.route.return_value = "Yggdrasil reply"

        provider = YggdrasilProvider()
        provider._module = fake
        response = provider.run({"text": "hello", "packet_id": "PKT-X"})

        fake.route.assert_called_once_with("hello")
        self.assertEqual(response.content, "Yggdrasil reply")
        self.assertEqual(response.metadata.get("source"), "yggdrasil")
        self.assertEqual(response.metadata.get("agent_bias"), "architect")

    def test_router_route_attribute_invoked_when_top_level_missing(self) -> None:
        fake = mock.MagicMock(spec=["router"])
        fake.router.route.return_value = "router.route reply"

        provider = YggdrasilProvider()
        provider._module = fake
        response = provider.run({"text": "hi", "packet_id": "PKT-X"})

        fake.router.route.assert_called_once_with("hi")
        self.assertEqual(response.content, "router.route reply")

    def test_ask_attribute_invoked_when_others_missing(self) -> None:
        fake = mock.MagicMock(spec=["ask"])
        fake.ask.return_value = "ask reply"

        provider = YggdrasilProvider()
        provider._module = fake
        response = provider.run({"text": "ping", "packet_id": "PKT-X"})

        fake.ask.assert_called_once_with("ping")
        self.assertEqual(response.content, "ask reply")

    def test_no_known_entry_point_returns_error_metadata(self) -> None:
        """The adapter must not crash if the upstream package
        doesn't expose any of the known entry-point shapes."""

        class _Empty:
            pass

        provider = YggdrasilProvider()
        provider._module = _Empty()
        response = provider.run({"text": "x", "packet_id": "PKT-X"})
        # Error contained in metadata, not raised.
        self.assertEqual(response.content, "")
        self.assertIn("error", response.metadata)

    def test_route_exception_does_not_crash(self) -> None:
        fake = mock.MagicMock()
        fake.route.side_effect = RuntimeError("router blew up")

        provider = YggdrasilProvider()
        provider._module = fake
        response = provider.run({"text": "x", "packet_id": "PKT-X"})

        self.assertEqual(response.content, "")
        self.assertEqual(response.metadata.get("error"), "router blew up")


# ---- registry integration --------------------------------------------


class RegistryIntegrationTests(unittest.TestCase):
    def test_registry_includes_yggdrasil(self) -> None:
        registry = ProviderRegistry()
        providers = registry.providers()
        self.assertIn("yggdrasil", providers)
        self.assertIsInstance(providers["yggdrasil"], YggdrasilProvider)

    def test_registry_yggdrasil_default_unconfigured(self) -> None:
        # Ensure the default (no flag, no dep) is unconfigured.
        previous = os.environ.pop(ISLAND_ENABLED_ENV, None)
        try:
            registry = ProviderRegistry()
            yggdrasil = registry.providers()["yggdrasil"]
            status = yggdrasil.validate_config()
            self.assertFalse(status.configured)
        finally:
            if previous is not None:
                os.environ[ISLAND_ENABLED_ENV] = previous


# ---- Phase F.2 (audit remediation 2026-05-02, finding #8) ------------
#
# Documented entry-point detection: the resolver tries the canonical
# wyrdforge package first, then the legacy yggdrasil alias. Each
# successful dispatch labels itself with the resolved module +
# attribute path so operators can see which entry point fired in
# the response metadata.


class WyrdforgeImportPriorityTests(unittest.TestCase):
    """``__post_init__`` prefers wyrdforge over yggdrasil when both
    are reachable. When neither resolves, ``_module`` is None."""

    def test_wyrdforge_wins_when_both_resolve(self) -> None:
        from mythic_vibe_cli.ai.providers import yggdrasil as _yg

        fake_wyrdforge = mock.MagicMock(name="wyrdforge")
        fake_yggdrasil = mock.MagicMock(name="yggdrasil")
        with mock.patch.object(
            _yg, "_try_import_wyrdforge", return_value=fake_wyrdforge
        ), mock.patch.object(
            _yg, "_try_import_yggdrasil", return_value=fake_yggdrasil
        ):
            provider = YggdrasilProvider()
        self.assertIs(provider._module, fake_wyrdforge)

    def test_falls_back_to_yggdrasil_when_wyrdforge_missing(self) -> None:
        from mythic_vibe_cli.ai.providers import yggdrasil as _yg

        fake_yggdrasil = mock.MagicMock(name="yggdrasil-only")
        with mock.patch.object(
            _yg, "_try_import_wyrdforge", return_value=None
        ), mock.patch.object(
            _yg, "_try_import_yggdrasil", return_value=fake_yggdrasil
        ):
            provider = YggdrasilProvider()
        self.assertIs(provider._module, fake_yggdrasil)

    def test_module_none_when_neither_resolves(self) -> None:
        from mythic_vibe_cli.ai.providers import yggdrasil as _yg

        with mock.patch.object(
            _yg, "_try_import_wyrdforge", return_value=None
        ), mock.patch.object(
            _yg, "_try_import_yggdrasil", return_value=None
        ):
            provider = YggdrasilProvider()
        self.assertIsNone(provider._module)


class InvokeYggdrasilLabelTests(unittest.TestCase):
    """``_invoke_yggdrasil`` returns ``(text, label)``. The label
    embeds both the module name and the attribute path so operators
    can trace which entry point fired."""

    def test_route_label_uses_module_name(self) -> None:
        from mythic_vibe_cli.ai.providers.yggdrasil import _invoke_yggdrasil
        import types

        module = types.ModuleType("wyrdforge")
        module.route = lambda prompt: f"routed:{prompt}"
        text, label = _invoke_yggdrasil(module, "hello")
        self.assertEqual(text, "routed:hello")
        self.assertEqual(label, "wyrdforge.route")

    def test_router_route_label(self) -> None:
        from mythic_vibe_cli.ai.providers.yggdrasil import _invoke_yggdrasil
        import types

        module = types.ModuleType("wyrdforge")
        module.router = types.SimpleNamespace(route=lambda p: f"sub:{p}")
        text, label = _invoke_yggdrasil(module, "x")
        self.assertEqual(text, "sub:x")
        self.assertEqual(label, "wyrdforge.router.route")

    def test_legacy_ask_label_preserved(self) -> None:
        from mythic_vibe_cli.ai.providers.yggdrasil import _invoke_yggdrasil
        import types

        module = types.ModuleType("yggdrasil")
        module.ask = lambda p: f"asked:{p}"
        text, label = _invoke_yggdrasil(module, "y")
        self.assertEqual(text, "asked:y")
        self.assertEqual(label, "yggdrasil.ask")

    def test_no_entry_point_raises_attribute_error_with_install_hint(
        self,
    ) -> None:
        from mythic_vibe_cli.ai.providers.yggdrasil import _invoke_yggdrasil
        import types

        module = types.ModuleType("any-module-no-shape")
        with self.assertRaises(AttributeError) as ctx:
            _invoke_yggdrasil(module, "z")
        msg = str(ctx.exception)
        self.assertIn("wyrdforge", msg)
        self.assertIn("route", msg)


class RunMetadataIncludesEntryPointTests(unittest.TestCase):
    """``run()`` propagates the entry-point label through to
    ``response.metadata['entry_point']`` so operators can audit
    which path was used."""

    def setUp(self) -> None:
        self._previous = os.environ.get(ISLAND_ENABLED_ENV)
        os.environ[ISLAND_ENABLED_ENV] = "1"

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop(ISLAND_ENABLED_ENV, None)
        else:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_metadata_records_entry_point_label(self) -> None:
        import types

        provider = YggdrasilProvider()
        fake = types.ModuleType("wyrdforge")
        fake.route = lambda prompt: f"answer:{prompt}"
        provider._module = fake
        response = provider.run({"text": "hi", "packet_id": "PKT-X"})
        self.assertEqual(response.content, "answer:hi")
        self.assertEqual(response.metadata.get("entry_point"), "wyrdforge.route")
        self.assertEqual(response.metadata.get("source"), "yggdrasil")
        self.assertEqual(response.metadata.get("agent_bias"), "architect")


if __name__ == "__main__":
    unittest.main()
