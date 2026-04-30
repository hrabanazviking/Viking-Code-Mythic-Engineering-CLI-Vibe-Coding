"""Tests for the routing table (PH-08 slice 8.1)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.ai.router import (
    DEFAULT_RULES,
    ROUTING_FILE_DIR,
    ROUTING_FILENAME,
    RouteDecision,
    RoutingRule,
    RoutingTable,
    route,
)
from mythic_vibe_cli.hardware import HardwareProfile


# ---- RoutingRule -------------------------------------------------------


class RoutingRuleMatchTests(unittest.TestCase):
    def test_wildcards_always_match(self) -> None:
        rule = RoutingRule()
        self.assertTrue(
            rule.matches(role="anything", task_type="anything", hardware=None)
        )

    def test_role_filter_exact(self) -> None:
        rule = RoutingRule(role="Forge Worker")
        self.assertTrue(
            rule.matches(role="Forge Worker", task_type="x", hardware=None)
        )
        self.assertFalse(
            rule.matches(role="Architect", task_type="x", hardware=None)
        )

    def test_task_type_filter_exact(self) -> None:
        rule = RoutingRule(task_type="build")
        self.assertTrue(rule.matches(role="*", task_type="build", hardware=None))
        self.assertFalse(rule.matches(role="*", task_type="verify", hardware=None))

    def test_min_ram_predicate(self) -> None:
        rule = RoutingRule(min_ram_mb=8000)
        small = HardwareProfile(ram_total_mb=4000)
        big = HardwareProfile(ram_total_mb=16000)
        # No hardware supplied → predicate passes.
        self.assertTrue(
            rule.matches(role="*", task_type="*", hardware=None)
        )
        self.assertFalse(rule.matches(role="*", task_type="*", hardware=small))
        self.assertTrue(rule.matches(role="*", task_type="*", hardware=big))

    def test_min_logical_cpus_predicate(self) -> None:
        rule = RoutingRule(min_logical_cpus=8)
        small = HardwareProfile(logical_cpus=4)
        big = HardwareProfile(logical_cpus=16)
        self.assertFalse(rule.matches(role="*", task_type="*", hardware=small))
        self.assertTrue(rule.matches(role="*", task_type="*", hardware=big))

    def test_zero_floor_means_no_requirement(self) -> None:
        rule = RoutingRule(min_ram_mb=0, min_logical_cpus=0)
        small = HardwareProfile(ram_total_mb=100, logical_cpus=1)
        self.assertTrue(rule.matches(role="*", task_type="*", hardware=small))

    def test_unknown_hardware_fields_pass(self) -> None:
        # Hardware with 0 ram_total_mb (psutil unavailable case): the
        # rule's min_ram_mb predicate should not block — we treat
        # missing measurement as "pass".
        rule = RoutingRule(min_ram_mb=8000)
        unknown = HardwareProfile(ram_total_mb=0, logical_cpus=0)
        self.assertTrue(rule.matches(role="*", task_type="*", hardware=unknown))


class RoutingRuleSerialisationTests(unittest.TestCase):
    def test_to_dict_round_trip(self) -> None:
        rule = RoutingRule(
            role="Forge Worker",
            task_type="build",
            min_ram_mb=8000,
            min_logical_cpus=4,
            prefer_local=True,
            provider="ollama",
            model="llama3.2",
            fallbacks=("anthropic", "copy-paste"),
            description="forge build",
        )
        clone = RoutingRule.from_dict(rule.to_dict())
        self.assertEqual(clone, rule)

    def test_from_dict_tolerates_partial_payload(self) -> None:
        # Missing fields fall back to defaults.
        rule = RoutingRule.from_dict({"role": "Skald"})
        self.assertEqual(rule.role, "Skald")
        self.assertEqual(rule.task_type, "*")
        self.assertEqual(rule.fallbacks, ())

    def test_reason_string_format(self) -> None:
        rule = RoutingRule(
            role="Forge Worker", min_ram_mb=8000, prefer_local=True
        )
        # Match path.
        text = rule.reason(
            role="Forge Worker",
            task_type="*",
            hardware=HardwareProfile(ram_total_mb=16000),
        )
        self.assertTrue(text.startswith("match:"))
        self.assertIn("min_ram_mb=8000", text)
        self.assertIn("prefer_local", text)
        # Skip path.
        text_skip = rule.reason(
            role="Skald", task_type="*", hardware=None
        )
        self.assertTrue(text_skip.startswith("skip:"))


# ---- RoutingTable -----------------------------------------------------


class RoutingTableTests(unittest.TestCase):
    def test_from_default_includes_catch_all(self) -> None:
        table = RoutingTable.from_default()
        self.assertGreater(len(table.rules), 1)
        # Last rule must be the universal catch-all.
        last = table.rules[-1]
        self.assertEqual(last.role, "*")
        self.assertEqual(last.task_type, "*")
        self.assertEqual(last.provider, "copy-paste")

    def test_load_with_no_overlay_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            table = RoutingTable.load(Path(tmp))
        self.assertEqual(
            len(table.rules), len(DEFAULT_RULES)
        )

    def test_load_overlay_takes_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overlay_dir = root.joinpath(*ROUTING_FILE_DIR)
            overlay_dir.mkdir(parents=True, exist_ok=True)
            overlay = [
                {
                    "role": "Forge Worker",
                    "task_type": "*",
                    "provider": "openrouter",
                    "model": "openai/gpt-4o",
                    "fallbacks": ["anthropic", "copy-paste"],
                    "description": "user override: openrouter",
                }
            ]
            (overlay_dir / ROUTING_FILENAME).write_text(
                json.dumps(overlay), encoding="utf-8"
            )
            table = RoutingTable.load(root)
        # The override sits at index 0, ahead of the defaults.
        self.assertEqual(table.rules[0].provider, "openrouter")
        self.assertEqual(table.rules[0].description, "user override: openrouter")
        # Default catch-all still present at the end.
        self.assertEqual(table.rules[-1].provider, "copy-paste")

    def test_load_corrupt_overlay_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            overlay_dir = root.joinpath(*ROUTING_FILE_DIR)
            overlay_dir.mkdir(parents=True, exist_ok=True)
            (overlay_dir / ROUTING_FILENAME).write_text(
                "{not-json", encoding="utf-8"
            )
            table = RoutingTable.load(root)
        self.assertEqual(len(table.rules), len(DEFAULT_RULES))


# ---- route() ----------------------------------------------------------


class RouteFunctionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = RoutingTable.from_default()

    def test_returns_decision_for_forge_worker_with_big_ram(self) -> None:
        big = HardwareProfile(ram_total_mb=32_000, logical_cpus=8)
        decision = route(
            self.table,
            role="Forge Worker",
            task_type="build",
            hardware=big,
        )
        self.assertIsInstance(decision, RouteDecision)
        self.assertEqual(decision.provider, "anthropic")
        self.assertEqual(decision.model, "claude-sonnet-4")
        self.assertEqual(decision.role, "Forge Worker")
        self.assertEqual(decision.task_type, "build")
        self.assertEqual(decision.fallbacks, ("openai", "copy-paste"))

    def test_forge_worker_on_small_box_lands_on_local_ollama(self) -> None:
        small = HardwareProfile(ram_total_mb=4_000, logical_cpus=2)
        decision = route(
            self.table,
            role="Forge Worker",
            hardware=small,
        )
        # First rule (min_ram_mb=16000) skipped; second rule (local
        # Ollama, no floor) matches.
        self.assertEqual(decision.provider, "ollama")
        self.assertEqual(decision.model, "llama3.2")

    def test_unknown_role_lands_on_catch_all(self) -> None:
        decision = route(
            self.table, role="Mystery", hardware=HardwareProfile()
        )
        self.assertEqual(decision.provider, "copy-paste")

    def test_decision_reasons_are_populated(self) -> None:
        decision = route(
            self.table, role="Architect", hardware=HardwareProfile()
        )
        self.assertTrue(decision.reasons)
        # Architect rule sits among the first few; reasons[0..3]
        # should cover the Forge-Worker rules being skipped.
        self.assertTrue(any("skip:" in r for r in decision.reasons))
        self.assertTrue(any("match:" in r for r in decision.reasons))

    def test_decision_to_dict_round_trip(self) -> None:
        decision = route(self.table, role="Skald")
        payload = decision.to_dict()
        for key in {
            "provider",
            "model",
            "rule_matched",
            "fallbacks",
            "reasons",
            "role",
            "task_type",
        }:
            self.assertIn(key, payload)
        self.assertEqual(payload["provider"], "openai")


if __name__ == "__main__":
    unittest.main()
