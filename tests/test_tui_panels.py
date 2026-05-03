"""Phase 20.I (audit remediation 2026-05-03) — opt-in TUI panel
data builder tests.

Pure data-layer tests; do NOT spin up Textual. The actual TUI
widget rendering is exercised by existing TUI tests that are
gated on the [tui] extra.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.tui_panels import (
    KNOWN_PANELS,
    build_heatmap_data,
    build_plugin_risk_data,
    parse_panels,
)


class ParsePanelsTests(unittest.TestCase):
    def test_empty_string_yields_empty_tuple(self) -> None:
        self.assertEqual(parse_panels(""), ())

    def test_single_known_panel(self) -> None:
        self.assertEqual(parse_panels("heatmap"), ("heatmap",))

    def test_two_known_panels_order_preserved(self) -> None:
        self.assertEqual(
            parse_panels("risk,heatmap"),
            ("risk", "heatmap"),
        )

    def test_case_insensitive(self) -> None:
        self.assertEqual(parse_panels("HEATMAP"), ("heatmap",))

    def test_unknown_panels_dropped_silently(self) -> None:
        self.assertEqual(
            parse_panels("heatmap,bogus,risk"),
            ("heatmap", "risk"),
        )

    def test_duplicates_collapsed(self) -> None:
        self.assertEqual(
            parse_panels("heatmap,heatmap,risk"),
            ("heatmap", "risk"),
        )

    def test_known_panels_locked(self) -> None:
        self.assertEqual(KNOWN_PANELS, ("heatmap", "risk"))


class BuildHeatmapDataTests(unittest.TestCase):
    def test_empty_project_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = build_heatmap_data(Path(tmp))
        self.assertEqual(data.total, 0)
        self.assertEqual(data.cells, [])

    def test_to_dict_serialisable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = build_heatmap_data(Path(tmp))
        json.dumps(data.to_dict())


class BuildPluginRiskDataTests(unittest.TestCase):
    def _seed_registry(
        self,
        root: Path,
        plugin_records: list[dict[str, object]],
    ) -> None:
        manifest = {
            "schema_version": 2,
            "hooks_version": 1,
            "available_hooks": [],
            "plugins": [r["entrypoint"] for r in plugin_records],
            "plugin_records": plugin_records,
        }
        path = root / "mythic" / "plugins.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_no_plugins_yields_empty_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = build_plugin_risk_data(Path(tmp))
        self.assertEqual(data.rows, [])

    def test_low_risk_when_no_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_registry(Path(tmp), [
                {
                    "entrypoint": "p1",
                    "enabled": True,
                    "hooks": [],
                    "version": "1.0",
                    "added_at": "2026-01-01T00:00:00Z",
                    "capabilities": [],
                },
            ])
            data = build_plugin_risk_data(Path(tmp))
        self.assertEqual(data.rows[0].risk_level, "low")

    def test_medium_risk_with_network_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_registry(Path(tmp), [
                {
                    "entrypoint": "p1",
                    "enabled": True,
                    "hooks": [],
                    "version": "1.0",
                    "added_at": "2026-01-01T00:00:00Z",
                    "capabilities": ["network"],
                },
            ])
            data = build_plugin_risk_data(Path(tmp))
        self.assertEqual(data.rows[0].risk_level, "medium")

    def test_high_risk_with_network_plus_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_registry(Path(tmp), [
                {
                    "entrypoint": "p1",
                    "enabled": True,
                    "hooks": [],
                    "version": "1.0",
                    "added_at": "2026-01-01T00:00:00Z",
                    "capabilities": ["network", "subprocess"],
                },
            ])
            data = build_plugin_risk_data(Path(tmp))
        self.assertEqual(data.rows[0].risk_level, "high")

    def test_high_risk_with_unknown_capability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_registry(Path(tmp), [
                {
                    "entrypoint": "p1",
                    "enabled": True,
                    "hooks": [],
                    "version": "1.0",
                    "added_at": "2026-01-01T00:00:00Z",
                    "capabilities": ["moonshine"],
                },
            ])
            data = build_plugin_risk_data(Path(tmp))
        row = data.rows[0]
        self.assertEqual(row.risk_level, "high")
        self.assertIn("moonshine", row.unknown_capabilities)

    def test_to_dict_serialisable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._seed_registry(Path(tmp), [
                {
                    "entrypoint": "p1",
                    "enabled": True,
                    "hooks": [],
                    "version": "1.0",
                    "added_at": "2026-01-01T00:00:00Z",
                    "capabilities": ["read"],
                },
            ])
            data = build_plugin_risk_data(Path(tmp))
        payload = data.to_dict()
        json.dumps(payload)
        self.assertEqual(len(payload["rows"]), 1)


class ParserAttachmentTests(unittest.TestCase):
    """Verify the argparse layer wires --panels into the tui
    command without hitting the actual TUI runtime."""

    def test_panels_flag_present_on_tui_parser(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["tui", "--panels", "heatmap"])
        self.assertEqual(ns.panels, "heatmap")

    def test_panels_default_empty(self) -> None:
        from mythic_vibe_cli.app import build_parser

        parser = build_parser()
        ns = parser.parse_args(["tui"])
        self.assertEqual(ns.panels, "")


if __name__ == "__main__":
    unittest.main()
