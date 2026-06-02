from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from mythic_vibe_cli.runtime.script_guard import guarded_main
from scripts.fix_absolute_paths import fix_file


class ScriptGuardTests(unittest.TestCase):
    def test_unexpected_exception_writes_crash_report_and_returns_failure(self) -> None:
        old_state = os.environ.get("MYTHIC_STATE_HOME")
        try:
            with tempfile.TemporaryDirectory() as tmp:
                os.environ["MYTHIC_STATE_HOME"] = tmp
                stderr = io.StringIO()

                def boom() -> int:
                    raise RuntimeError("script failed")

                with redirect_stderr(stderr):
                    code = guarded_main(boom, script_name="test-script.py")

                reports = list((Path(tmp) / "script-crashes").glob("test-script.py-*.log"))
                self.assertEqual(code, 1)
                self.assertEqual(len(reports), 1)
                self.assertIn("RuntimeError: script failed", reports[0].read_text(encoding="utf-8"))
                self.assertIn("crash report", stderr.getvalue())
        finally:
            if old_state is None:
                os.environ.pop("MYTHIC_STATE_HOME", None)
            else:
                os.environ["MYTHIC_STATE_HOME"] = old_state

    def test_keyboard_interrupt_returns_standard_interrupt_code(self) -> None:
        stderr = io.StringIO()

        def interrupted() -> int:
            raise KeyboardInterrupt

        with redirect_stderr(stderr):
            code = guarded_main(interrupted, script_name="test-script.py")

        self.assertEqual(code, 130)
        self.assertIn("interrupted", stderr.getvalue())


class FixAbsolutePathsTests(unittest.TestCase):
    def test_dry_run_reports_change_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inside = root / "docs" / "note.md"
            inside.parent.mkdir()
            inside.write_text("path=C:/repo/docs/file.md\n", encoding="utf-8")

            result = fix_file(inside, root, dry_run=True, backup=False)

            self.assertTrue(result.changed)
            self.assertEqual(result.replacements, 1)
            self.assertEqual(inside.read_text(encoding="utf-8"), "path=C:/repo/docs/file.md\n")

    def test_write_mode_can_backup_and_remove_external_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "config.yaml"
            target.write_text('bad: "C:/outside/secret.txt"\n', encoding="utf-8")

            result = fix_file(target, root, dry_run=False, backup=True)

            self.assertTrue(result.changed)
            self.assertTrue((root / "config.yaml.bak").is_file())
            self.assertEqual(target.read_text(encoding="utf-8"), 'bad: ""\n')


if __name__ == "__main__":
    unittest.main()
