"""Coverage tests for the four ritual scaffold commands.

These commands (`weave`, `prune`, `heal`, `oath`) are deliberately
scaffold-only today — see PHASE1_RUNTIME_AUDIT.md findings F-001/2/4/5.
They will grow real implementations in PH-13 (heal/prune as
drift/self-healing) and PH-14 (oath as the policy engine constraint
store). Until then we lock in their current public contracts so any
later change is observable in CI.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import tempfile
import unittest
from pathlib import Path

from mythic_vibe_cli import app, commands
from mythic_vibe_cli.exit_codes import SUCCESS, USER_INPUT_ERROR


class RitualScaffoldTests(unittest.TestCase):
    def _init_project(self, root: Path) -> None:
        """Create a minimal Mythic project so weave's check_in succeeds."""
        with redirect_stdout(io.StringIO()):
            app.main(["init", "--goal", "ritual-test", "--path", str(root)])

    # ----- prune -----

    def test_cmd_prune_prints_scaffold_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = commands.cmd_prune(ns)
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("Prune ritual scaffold ready", output)
            self.assertIn("linter/dead-code tool", output)

    # ----- heal (PH-13 slice 13.3 — Scribe reconciliation packet) -----

    def test_cmd_heal_writes_packet_and_prints_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, failing_test=None, json=False, dry_run=False)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = commands.cmd_heal(ns)
            self.assertEqual(code, SUCCESS)
            output = stdout.getvalue()
            self.assertIn("Scribe reconciliation packet", output)
            # Packet was written under mythic/heal/.
            heal_dir = Path(tmp) / "mythic" / "heal"
            self.assertTrue(heal_dir.is_dir())
            md_files = list(heal_dir.glob("*-reconciliation.md"))
            json_files = list(heal_dir.glob("*-reconciliation.json"))
            self.assertEqual(len(md_files), 1)
            self.assertEqual(len(json_files), 1)

    def test_cmd_heal_records_failing_test_when_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(
                path=tmp,
                failing_test="tests/test_x.py::test_y",
                json=False,
                dry_run=False,
            )
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = commands.cmd_heal(ns)
            self.assertEqual(code, SUCCESS)
            self.assertIn("tests/test_x.py::test_y", stdout.getvalue())
            md_files = list((Path(tmp) / "mythic" / "heal").glob("*-reconciliation.md"))
            self.assertIn(
                "tests/test_x.py::test_y",
                md_files[0].read_text(encoding="utf-8"),
            )

    def test_cmd_heal_dry_run_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ns = argparse.Namespace(path=tmp, failing_test=None, json=False, dry_run=True)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = commands.cmd_heal(ns)
            self.assertEqual(code, SUCCESS)
            self.assertIn("Dry run", stdout.getvalue())
            # Heal dir is not created on dry-run.
            self.assertFalse((Path(tmp) / "mythic" / "heal").exists())

    # ----- oath -----

    def test_cmd_oath_prints_oath_text_without_yes(self) -> None:
        ns = argparse.Namespace(yes=False)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = commands.cmd_oath(ns)
        self.assertEqual(code, SUCCESS)
        output = stdout.getvalue()
        self.assertIn("AI may generate incorrect", output)
        self.assertNotIn("Oath accepted", output)

    def test_cmd_oath_appends_acceptance_when_yes(self) -> None:
        ns = argparse.Namespace(yes=True)
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = commands.cmd_oath(ns)
        self.assertEqual(code, SUCCESS)
        output = stdout.getvalue()
        self.assertIn("AI may generate incorrect", output)
        self.assertIn("Oath accepted", output)

    # ----- weave -----

    def test_cmd_weave_dry_run_writes_no_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_project(root)
            mythic_dir = root / "mythic"
            status_before = (mythic_dir / "status.json").stat().st_mtime if (mythic_dir / "status.json").exists() else 0

            ns = argparse.Namespace(path=str(root), dry_run=True)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = commands.cmd_weave(ns)

            self.assertEqual(code, SUCCESS)
            self.assertIn("Dry run", stdout.getvalue())
            status_after = (mythic_dir / "status.json").stat().st_mtime if (mythic_dir / "status.json").exists() else 0
            self.assertEqual(status_before, status_after)

    def test_cmd_weave_blocked_by_reflect_gate_without_prior_verification(self) -> None:
        """Locks in current behaviour: weave delegates to check_in('reflect',
        ...), which now refuses to advance until a successful verification is
        recorded. Documented as new finding F-021 in PHASE1_SLICE_1_4 work —
        weave cannot succeed in a project that has not yet run `verify
        --record`. The real fix lives with PH-13 (heal/weave grow real
        drift-reconciliation behaviour); this test prevents accidental
        regression of the gate.
        """
        from contextlib import redirect_stderr

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_project(root)

            ns = argparse.Namespace(path=str(root), dry_run=False)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = commands.cmd_weave(ns)

            self.assertEqual(code, USER_INPUT_ERROR)
            self.assertIn("verify", stderr.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
