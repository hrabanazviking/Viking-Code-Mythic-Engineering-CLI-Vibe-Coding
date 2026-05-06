"""Structural tests for the WASI browser playground (PH-23.16).

The page itself is HTML + JS; we can't drive it without a
browser harness. These tests confirm:
- The expected files exist at packaging/wasi/playground/.
- The HTML references the JS file (no orphan JS).
- The HTML lists each v2.0-supported command at least once.
- The JS implements stub_run for each supported command + the
  unsupported-fallback branch.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PLAYGROUND_DIR = REPO_ROOT / "packaging" / "wasi" / "playground"
INDEX_HTML = PLAYGROUND_DIR / "index.html"
PLAYGROUND_JS = PLAYGROUND_DIR / "playground.js"
PLAYGROUND_README = PLAYGROUND_DIR / "README.md"


# v2.0 WASI scope per packaging/wasi/README.md. Both the HTML
# (quick-pick buttons) and the JS (stub_run dispatcher) must
# reference each entry.
SUPPORTED_COMMANDS = (
    "--version",
    "--help",
    "doctor --json",
    "status --json",
    "packet list --json",
)


class PlaygroundFilesExistTests(unittest.TestCase):
    def test_index_html_present(self) -> None:
        self.assertTrue(
            INDEX_HTML.is_file(),
            f"index.html missing at {INDEX_HTML}",
        )

    def test_playground_js_present(self) -> None:
        self.assertTrue(
            PLAYGROUND_JS.is_file(),
            f"playground.js missing at {PLAYGROUND_JS}",
        )

    def test_readme_present(self) -> None:
        self.assertTrue(
            PLAYGROUND_README.is_file(),
            f"playground README missing at {PLAYGROUND_README}",
        )


class IndexHtmlContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = INDEX_HTML.read_text(encoding="utf-8")

    def test_loads_playground_js(self) -> None:
        # The JS file is the runtime; the HTML must reference it.
        self.assertIn("playground.js", self.text)

    def test_has_command_input_field(self) -> None:
        # The text input is the user-facing entry point.
        self.assertRegex(
            self.text,
            r'<input[^>]*id="cmd-input"',
        )

    def test_has_run_button(self) -> None:
        self.assertRegex(
            self.text,
            r'<button[^>]*id="run-btn"',
        )

    def test_has_output_panel(self) -> None:
        self.assertRegex(
            self.text,
            r'<pre[^>]*id="output"',
        )

    def test_lists_every_supported_command_in_quick_pick(self) -> None:
        # The quick-pick command buttons each have a data-cmd
        # attribute carrying one of the supported commands.
        # Extracting via regex — the buttons all share the
        # data-cmd="..." attribute pattern.
        cmds_in_buttons = re.findall(
            r'data-cmd="([^"]+)"', self.text,
        )
        for expected in SUPPORTED_COMMANDS:
            self.assertIn(
                expected, cmds_in_buttons,
                f"quick-pick missing command: {expected}",
            )

    def test_includes_download_anchors(self) -> None:
        # The page advertises both artifacts (.wasm + .pyz)
        # so operators see what the WASI release provides.
        self.assertIn('id="download-wasm"', self.text)
        self.assertIn('id="download-pyz"', self.text)

    def test_marks_status_as_experimental(self) -> None:
        # Operators must see the experimental + foundation-level
        # status upfront — the runtime is stub today.
        text_lower = self.text.lower()
        self.assertIn("experimental", text_lower)
        self.assertIn("foundation", text_lower)


class PlaygroundJsContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = PLAYGROUND_JS.read_text(encoding="utf-8")

    def test_declares_stub_run_function(self) -> None:
        self.assertRegex(
            self.text,
            r"function\s+stub_run\s*\(",
        )

    def test_handles_every_supported_command(self) -> None:
        # The dispatcher in stub_run uses literal-string
        # comparisons. Each supported command must appear in the
        # JS source as a quoted string.
        for expected in SUPPORTED_COMMANDS:
            self.assertIn(
                f'"{expected}"', self.text,
                f"stub_run missing branch for: {expected}",
            )

    def test_returns_unsupported_fallback(self) -> None:
        # Unknown commands surface a helpful error referencing
        # the supported set.
        self.assertIn("Unknown or unsupported", self.text)

    def test_run_button_event_listener_wired(self) -> None:
        # The Run button must trigger runCurrentCommand on click.
        self.assertRegex(
            self.text,
            r'runBtn\.addEventListener\(\s*["\']click["\']',
        )

    def test_enter_key_runs_command(self) -> None:
        # Pressing Enter inside the input runs the command —
        # standard CLI-feeling UX.
        self.assertIn('event.key === "Enter"', self.text)

    def test_disables_button_during_run(self) -> None:
        # Disable the Run button while a command is in flight
        # so double-clicks don't queue races.
        self.assertIn("runBtn.disabled", self.text)


class PlaygroundReadmeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = PLAYGROUND_README.read_text(encoding="utf-8")

    def test_describes_local_run_recipe(self) -> None:
        # Operators need the static-server recipe.
        self.assertIn("python -m http.server", self.text)

    def test_documents_supported_command_set(self) -> None:
        # The README should list each v2.0-supported command so
        # operators can see them without loading the page.
        for expected in SUPPORTED_COMMANDS:
            self.assertIn(
                expected, self.text,
                f"README missing command: {expected}",
            )

    def test_marks_runtime_stub_status(self) -> None:
        # Honesty about what's NOT real yet.
        text_lower = self.text.lower()
        self.assertIn("stub", text_lower)
        self.assertIn("foundation", text_lower)


if __name__ == "__main__":
    unittest.main()
