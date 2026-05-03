"""Phase 20.A (audit remediation 2026-05-03) — persona preset
tests.

Two layers:

- **Pure model** — `get_preset` validates names; `apply_preset`
  writes/refuses-overwrite; `load_active_persona` is defensive
  (never raises).
- **CLI integration** — `persona apply` and `persona show`
  produce expected text and JSON output; unknown subcommand
  returns USER_INPUT_ERROR.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR
from mythic_vibe_cli.personas import (
    PRESET_NAMES,
    PRESETS,
    SCHEMA_VERSION,
    apply_preset,
    get_preset,
    load_active_persona,
    persona_path,
)


class PresetCatalogTests(unittest.TestCase):
    def test_three_presets_present(self) -> None:
        self.assertEqual(set(PRESETS.keys()), set(PRESET_NAMES))

    def test_known_preset_names_locked(self) -> None:
        # If we add or remove a preset, the docs and the
        # parser's --preset choices must follow.
        self.assertEqual(PRESET_NAMES, ("solo", "team-lead", "auditor"))

    def test_each_preset_has_required_fields(self) -> None:
        for name, preset in PRESETS.items():
            self.assertEqual(preset.name, name)
            self.assertTrue(preset.description)
            self.assertIn(preset.approval_mode, ("suggest", "auto", "partial"))
            self.assertIn(
                preset.audience,
                ("beginner", "intermediate", "advanced"),
            )
            self.assertGreater(preset.audit_cadence_days, 0)
            self.assertIsInstance(preset.require_plugin_review, bool)


class GetPresetTests(unittest.TestCase):
    def test_returns_preset_for_known_name(self) -> None:
        preset = get_preset("solo")
        self.assertEqual(preset.name, "solo")

    def test_case_insensitive(self) -> None:
        preset = get_preset("AUDITOR")
        self.assertEqual(preset.name, "auditor")

    def test_unknown_raises_value_error(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_preset("nonsense")
        self.assertIn("Valid:", str(ctx.exception))


class ApplyPresetTests(unittest.TestCase):
    def test_writes_persona_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            applied = apply_preset(Path(tmp), "team-lead")
            self.assertEqual(applied.preset.name, "team-lead")
            self.assertTrue(applied.path.is_file())
            payload = json.loads(applied.path.read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "team-lead")
            self.assertEqual(payload["schema_version"], SCHEMA_VERSION)

    def test_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apply_preset(Path(tmp), "solo")
            with self.assertRaises(FileExistsError):
                apply_preset(Path(tmp), "auditor")

    def test_force_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apply_preset(Path(tmp), "solo")
            applied = apply_preset(Path(tmp), "auditor", force=True)
            self.assertEqual(applied.preset.name, "auditor")
            payload = json.loads(applied.path.read_text(encoding="utf-8"))
            self.assertEqual(payload["name"], "auditor")


class LoadActivePersonaTests(unittest.TestCase):
    def test_returns_none_when_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = load_active_persona(Path(tmp))
            self.assertIsNone(state.preset)
            self.assertIsNone(state.error)

    def test_loads_applied_preset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            apply_preset(Path(tmp), "solo")
            state = load_active_persona(Path(tmp))
            self.assertIsNotNone(state.preset)
            self.assertEqual(state.preset.name, "solo")

    def test_malformed_json_returns_error_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = persona_path(Path(tmp))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{not valid json", encoding="utf-8")
            state = load_active_persona(Path(tmp))
            self.assertIsNone(state.preset)
            self.assertIsNotNone(state.error)

    def test_unknown_preset_name_in_file_returns_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = persona_path(Path(tmp))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps({"name": "ghost"}), encoding="utf-8"
            )
            state = load_active_persona(Path(tmp))
            self.assertIsNone(state.preset)
            self.assertIn("ghost", state.error or "")


class CmdPersonaIntegrationTests(unittest.TestCase):
    def _run(self, ns: argparse.Namespace) -> tuple[int, str]:
        from mythic_vibe_cli.commands import cmd_persona

        captured = io.StringIO()
        original = sys.stdout
        sys.stdout = captured
        try:
            code = cmd_persona(ns)
        finally:
            sys.stdout = original
        return code, captured.getvalue()

    def test_apply_solo_text_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                persona_command="apply",
                preset="solo",
                path=tmp,
                force=False,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("Applied persona preset: solo", output)

    def test_apply_invalid_preset_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, _ = self._run(argparse.Namespace(
                persona_command="apply",
                preset="bogus",
                path=tmp,
                force=False,
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_apply_refuses_overwrite_returns_user_input_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._run(argparse.Namespace(
                persona_command="apply",
                preset="solo",
                path=tmp,
                force=False,
                json=False,
            ))
            code, _ = self._run(argparse.Namespace(
                persona_command="apply",
                preset="auditor",
                path=tmp,
                force=False,
                json=False,
            ))
        self.assertEqual(code, USER_INPUT_ERROR)

    def test_apply_json_payload_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                persona_command="apply",
                preset="team-lead",
                path=tmp,
                force=False,
                json=True,
            ))
            payload = json.loads(output)
        self.assertEqual(code, SUCCESS)
        self.assertEqual(payload["preset"]["name"], "team-lead")

    def test_show_when_no_persona(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, output = self._run(argparse.Namespace(
                persona_command="show",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("none", output)

    def test_show_after_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self._run(argparse.Namespace(
                persona_command="apply",
                preset="auditor",
                path=tmp,
                force=False,
                json=False,
            ))
            code, output = self._run(argparse.Namespace(
                persona_command="show",
                path=tmp,
                json=False,
            ))
        self.assertEqual(code, SUCCESS)
        self.assertIn("auditor", output)

    def test_unknown_subcommand_returns_user_input_error(self) -> None:
        code, _ = self._run(argparse.Namespace(
            persona_command="bogus",
            path=tempfile.gettempdir(),
            json=False,
        ))
        self.assertEqual(code, USER_INPUT_ERROR)


if __name__ == "__main__":
    unittest.main()
