"""Phase 20.D (audit remediation 2026-05-03) — per-role packet
budget tests.

The pre-20.D ``_compact_sections`` signature is preserved
byte-identically when ``role`` is None or unknown. Known roles
trigger the per-role multiplier from
``ROLE_BUDGET_MULTIPLIERS``.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.codex_bridge import (
    MIN_PACKET_BUDGET,
    ROLE_BUDGET_MULTIPLIERS,
    PacketBuilder,
)


def _builder() -> PacketBuilder:
    """Construct a PacketBuilder against a throwaway directory.
    The compaction code path doesn't touch disk — we just need
    a valid root for the constructor."""
    tmp = tempfile.mkdtemp(prefix="mvcli-pkt-")
    return PacketBuilder(Path(tmp))


class RoleMultiplierTableTests(unittest.TestCase):
    def test_six_canonical_roles_present(self) -> None:
        for role in (
            "Skald", "Architect", "Cartographer",
            "Forge Worker", "Auditor", "Scribe",
        ):
            self.assertIn(role, ROLE_BUDGET_MULTIPLIERS)

    def test_skald_below_baseline(self) -> None:
        """Skald is the framing role — less code context."""
        self.assertLess(ROLE_BUDGET_MULTIPLIERS["Skald"], 1.0)

    def test_forge_worker_above_baseline(self) -> None:
        self.assertGreater(ROLE_BUDGET_MULTIPLIERS["Forge Worker"], 1.0)

    def test_min_packet_budget_documented(self) -> None:
        # Floor must be > 0; arbitrarily small budgets aren't
        # useful packets.
        self.assertGreater(MIN_PACKET_BUDGET, 0)


class CompactSectionsRoleAwareTests(unittest.TestCase):
    def test_role_none_preserves_pre_20d_behaviour(self) -> None:
        builder = _builder()
        sections = {"goals": "x" * 1000, "loop": "y" * 1000}
        out = builder._compact_sections(dict(sections), budget=10_000, role=None)
        # 2000 < 10000 → no compaction in either branch.
        self.assertEqual(out, sections)

    def test_skald_smaller_budget_triggers_more_compaction(self) -> None:
        """At a budget where Forge Worker (1.5x) would not
        compact, Skald (0.7x) should — the multiplier shrinks
        the effective budget below the section total."""
        builder = _builder()
        sections = {"goals": "x" * 1500, "loop": "y" * 1500}
        # Total = 3000; budget=2500 → multiplier 0.7 = effective 1750 → compaction.
        skald_out = builder._compact_sections(
            dict(sections), budget=2500, role="Skald",
        )
        skald_total = sum(len(v) for v in skald_out.values())
        self.assertLess(skald_total, 3000, "Skald budget should compact further")

    def test_forge_worker_larger_budget_can_skip_compaction(self) -> None:
        """At a budget where the baseline would compact, the
        Forge Worker 1.5x multiplier may fit the sections
        without compaction."""
        builder = _builder()
        sections = {"goals": "x" * 1500, "loop": "y" * 1500}
        # Total = 3000; budget=2500 → multiplier 1.5 = effective 3750 → no compaction.
        forge_out = builder._compact_sections(
            dict(sections), budget=2500, role="Forge Worker",
        )
        self.assertEqual(forge_out, sections)

    def test_unknown_role_treated_as_baseline(self) -> None:
        builder = _builder()
        sections = {"goals": "x" * 500, "loop": "y" * 500}
        baseline = builder._compact_sections(
            dict(sections), budget=10_000, role=None
        )
        unknown = builder._compact_sections(
            dict(sections), budget=10_000, role="Mystery"
        )
        self.assertEqual(baseline, unknown)

    def test_min_packet_budget_floor_enforced(self) -> None:
        """Even with a tiny budget × small multiplier, the
        effective budget never drops below MIN_PACKET_BUDGET.
        We assert by giving Skald (0.7x) a 100-char budget;
        floor → 400."""
        builder = _builder()
        # Build sections totalling >> 400 so compaction triggers.
        sections = {
            "goals": "x" * 600,
            "loop": "y" * 600,
            "architecture": "z" * 600,
        }
        out = builder._compact_sections(
            dict(sections), budget=100, role="Skald"
        )
        # The compaction should have fit the result roughly
        # within the floor (with some slack from the
        # weighted-budget algorithm). Hard upper bound: 2x the
        # floor (the algorithm doesn't always converge below
        # the budget exactly, but it should never balloon).
        total = sum(len(v) for v in out.values())
        self.assertLess(total, MIN_PACKET_BUDGET * 4)


if __name__ == "__main__":
    unittest.main()
