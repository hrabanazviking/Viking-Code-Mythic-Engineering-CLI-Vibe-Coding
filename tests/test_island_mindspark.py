"""Tests for Island C (MindSpark) adapter — PH-09 Slice 9.2."""

from __future__ import annotations

import os
import unittest
from unittest import mock

from mythic_vibe_cli.ai.providers.mindspark import (
    INSTALL_HINT,
    ISLAND_ENABLED_ENV,
    MindSparkProvider,
    is_island_enabled,
)
from mythic_vibe_cli.ai.registry import ProviderRegistry


class IsIslandEnabledTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_default_off(self) -> None:
        self.assertFalse(is_island_enabled())

    def test_truthy_on(self) -> None:
        os.environ[ISLAND_ENABLED_ENV] = "1"
        self.assertTrue(is_island_enabled())


class ValidateConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_unconfigured_when_dep_missing(self) -> None:
        provider = MindSparkProvider()
        provider._module = None
        status = provider.validate_config()
        self.assertFalse(status.configured)
        self.assertTrue(any("not installed" in d for d in status.details))
        self.assertTrue(any("mindspark" in d.lower() for d in status.details))

    def test_install_hint_surfaces_extras(self) -> None:
        provider = MindSparkProvider()
        provider._module = None
        status = provider.validate_config()
        hint_lines = [d for d in status.details if "Install hint" in d]
        self.assertEqual(len(hint_lines), 1)
        self.assertIn("thoughtforge", hint_lines[0])
        self.assertIn("mindspark", hint_lines[0])  # mentions the extra

    def test_unconfigured_when_flag_off_even_with_dep(self) -> None:
        provider = MindSparkProvider()
        provider._module = mock.MagicMock()
        status = provider.validate_config()
        self.assertFalse(status.configured)
        self.assertTrue(any("import OK" in d for d in status.details))

    def test_configured_when_flag_on_and_dep_present(self) -> None:
        os.environ[ISLAND_ENABLED_ENV] = "1"
        provider = MindSparkProvider()
        provider._module = mock.MagicMock()
        status = provider.validate_config()
        self.assertTrue(status.configured)


class RunStubPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_stub_response_when_dep_missing(self) -> None:
        provider = MindSparkProvider()
        provider._module = None
        response = provider.run({"text": "plan a feature", "packet_id": "PKT-X"})
        self.assertEqual(response.provider, "mindspark")
        self.assertEqual(response.content, "")
        self.assertTrue(response.dry_run)
        self.assertEqual(response.metadata.get("source"), "mindspark-stub")
        self.assertFalse(response.metadata.get("configured", True))


class RunRealPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._previous = os.environ.pop(ISLAND_ENABLED_ENV, None)
        os.environ[ISLAND_ENABLED_ENV] = "1"

    def tearDown(self) -> None:
        os.environ.pop(ISLAND_ENABLED_ENV, None)
        if self._previous is not None:
            os.environ[ISLAND_ENABLED_ENV] = self._previous

    def test_top_level_plan_invoked(self) -> None:
        fake = mock.MagicMock()
        fake.plan.return_value = "MindSpark plan: ..."

        provider = MindSparkProvider()
        provider._module = fake
        response = provider.run({"text": "scope a refactor", "packet_id": "PKT-X"})

        fake.plan.assert_called_once_with("scope a refactor")
        self.assertEqual(response.content, "MindSpark plan: ...")
        self.assertEqual(response.metadata.get("source"), "mindspark")
        self.assertEqual(response.metadata.get("agent_bias"), "planner")

    def test_cognition_plan_attribute_invoked(self) -> None:
        fake = mock.MagicMock(spec=["cognition"])
        fake.cognition.plan.return_value = "cognition.plan reply"

        provider = MindSparkProvider()
        provider._module = fake
        response = provider.run({"text": "x", "packet_id": "PKT-X"})

        fake.cognition.plan.assert_called_once_with("x")
        self.assertEqual(response.content, "cognition.plan reply")

    def test_unknown_shape_returns_error_metadata(self) -> None:
        class _Empty:
            pass

        provider = MindSparkProvider()
        provider._module = _Empty()
        response = provider.run({"text": "x", "packet_id": "PKT-X"})
        self.assertEqual(response.content, "")
        self.assertIn("error", response.metadata)

    def test_plan_exception_does_not_crash(self) -> None:
        fake = mock.MagicMock()
        fake.plan.side_effect = ValueError("planner blew up")

        provider = MindSparkProvider()
        provider._module = fake
        response = provider.run({"text": "x", "packet_id": "PKT-X"})
        self.assertEqual(response.content, "")
        self.assertEqual(response.metadata.get("error"), "planner blew up")


class RegistryIntegrationTests(unittest.TestCase):
    def test_registry_includes_mindspark(self) -> None:
        registry = ProviderRegistry()
        providers = registry.providers()
        self.assertIn("mindspark", providers)
        self.assertIsInstance(providers["mindspark"], MindSparkProvider)

    def test_registry_mindspark_default_unconfigured(self) -> None:
        previous = os.environ.pop(ISLAND_ENABLED_ENV, None)
        try:
            registry = ProviderRegistry()
            mindspark = registry.providers()["mindspark"]
            status = mindspark.validate_config()
            self.assertFalse(status.configured)
        finally:
            if previous is not None:
                os.environ[ISLAND_ENABLED_ENV] = previous


class InstallHintConstantTests(unittest.TestCase):
    def test_constant_mentions_extras(self) -> None:
        # Tests that the public INSTALL_HINT string is informative.
        self.assertIn("thoughtforge", INSTALL_HINT)
        self.assertIn("mindspark", INSTALL_HINT)


if __name__ == "__main__":
    unittest.main()
