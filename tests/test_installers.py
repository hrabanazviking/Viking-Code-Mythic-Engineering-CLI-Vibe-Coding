from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstallerSmokeTests(unittest.TestCase):
    def test_unix_installers_pass_shell_syntax_check(self) -> None:
        shell = shutil.which("sh")
        if shell is None:
            self.skipTest("sh is not available")

        for script_name in ("install_linux.sh", "install_macos.sh"):
            with self.subTest(script=script_name):
                result = subprocess.run(
                    [shell, "-n", str(ROOT / script_name)],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_linux_installer_finds_versioned_python_and_sets_path_command(self) -> None:
        text = (ROOT / "install_linux.sh").read_text(encoding="utf-8")

        self.assertIn("python3.14 python3.13 python3.12 python3.11 python3.10 python3", text)
        self.assertIn('PYTHON_VERSION="$($PYTHON_CMD --version 2>&1)"', text)
        self.assertIn('--install-bin)', text)
        self.assertIn('for command_name in mythic mythic-vibe; do', text)
        self.assertIn('PATH_LINE=', text)
        self.assertIn('mythic --version', text)

    def test_unix_installers_quarantine_broken_existing_venv(self) -> None:
        for script_name in ("install_linux.sh", "install_macos.sh"):
            with self.subTest(script=script_name):
                text = (ROOT / script_name).read_text(encoding="utf-8")
                self.assertIn("quarantine_broken_venv()", text)
                self.assertIn('broken="${VENV_DIR}.broken.${stamp}"', text)
                self.assertIn('mv "$VENV_DIR" "$broken"', text)
                self.assertIn('echo "Virtual environment repaired."', text)

    def test_windows_installer_repairs_venv_and_installs_mythic_path_command(self) -> None:
        text = (ROOT / "install_windows.bat").read_text(encoding="utf-8")

        self.assertIn('set "INSTALL_BIN=%LOCALAPPDATA%\\Programs\\MythicVibeCLI\\bin"', text)
        self.assertIn('if not exist "!VENV_DIR!\\Scripts\\python.exe" set "NEEDS_VENV_CREATE=1"', text)
        self.assertIn('if not exist "!VENV_DIR!\\Scripts\\activate.bat" set "NEEDS_VENV_CREATE=1"', text)
        self.assertIn("call :quarantine_venv", text)
        self.assertIn('call :write_launcher "mythic" "!VENV_ABS!\\Scripts\\mythic.exe"', text)
        self.assertIn("[Environment]::SetEnvironmentVariable('Path'", text)
        self.assertIn("mythic --version", text)

    def test_windows_generated_launcher_preserves_retry_status(self) -> None:
        text = (ROOT / "install_windows.bat").read_text(encoding="utf-8")

        self.assertIn('echo :retry', text)
        self.assertIn('echo set "STATUS=%%ERRORLEVEL%%"', text)
        self.assertIn('echo exit /b %%STATUS%%', text)
        self.assertNotIn('echo exit /b 0', text)


class ActiveScriptGuardCoverageTests(unittest.TestCase):
    def test_active_python_scripts_use_script_guard(self) -> None:
        script_paths = [
            *sorted((ROOT / "scripts").glob("*.py")),
            *sorted((ROOT / "tools").glob("*.py")),
            ROOT / "packaging" / "nuitka" / "build.py",
            ROOT / "packaging" / "wasi" / "build.py",
        ]

        missing_guard: list[str] = []
        for path in script_paths:
            text = path.read_text(encoding="utf-8")
            if 'if __name__ == "__main__"' in text and "guarded_main(" not in text:
                missing_guard.append(path.relative_to(ROOT).as_posix())

        self.assertEqual(missing_guard, [])


if __name__ == "__main__":
    unittest.main()
