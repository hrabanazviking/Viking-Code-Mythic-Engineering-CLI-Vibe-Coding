from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest

from mythic_vibe_cli import app
from mythic_vibe_cli.exit_codes import SUCCESS


class PluginCommandTests(unittest.TestCase):
    def test_grimoire_add_writes_versioned_registry_but_keeps_legacy_plugins_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with redirect_stdout(output):
                code = app.main(
                    [
                        "grimoire",
                        "add",
                        "my_pkg.plugin:Plugin",
                        "--path",
                        tmp,
                        "--hook",
                        "before_scan",
                        "--version",
                        "1.2.3",
                        "--json",
                    ]
                )

            payload = json.loads(output.getvalue())
            registry = json.loads((Path(tmp) / "mythic" / "plugins.json").read_text(encoding="utf-8"))

            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["plugins"], ["my_pkg.plugin:Plugin"])
            self.assertEqual(registry["schema_version"], 2)
            self.assertEqual(registry["plugins"], ["my_pkg.plugin:Plugin"])
            self.assertEqual(registry["plugin_records"][0]["hooks"], ["before_scan"])
            self.assertEqual(registry["plugin_records"][0]["version"], "1.2.3")

    def test_plugin_list_and_disable_expose_health_without_importing_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app.main(["grimoire", "add", "my_pkg.plugin:Plugin", "--path", tmp, "--hook", "after_verify"])

            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_code = app.main(["plugin", "list", "--path", tmp, "--json"])

            disable_output = io.StringIO()
            with redirect_stdout(disable_output):
                disable_code = app.main(["plugin", "disable", "my_pkg.plugin:Plugin", "--path", tmp, "--json"])

            list_after_output = io.StringIO()
            with redirect_stdout(list_after_output):
                list_after_code = app.main(["plugin", "list", "--path", tmp, "--all", "--json"])

            list_payload = json.loads(list_output.getvalue())
            disable_payload = json.loads(disable_output.getvalue())
            list_after_payload = json.loads(list_after_output.getvalue())

            self.assertEqual(list_code, SUCCESS)
            self.assertEqual(disable_code, SUCCESS)
            self.assertEqual(list_after_code, SUCCESS)
            self.assertEqual(list_payload["plugins"][0]["health"]["status"], "healthy")
            self.assertFalse(disable_payload["plugin"]["enabled"])
            self.assertEqual(list_after_payload["plugins"][0]["health"]["status"], "disabled")
            self.assertTrue((root / "mythic" / "plugins.json").exists())

    def test_plugin_inspect_imports_entrypoint_and_reports_declared_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module_dir = root / "local_plugins"
            module_dir.mkdir()
            (module_dir / "__init__.py").write_text("", encoding="utf-8")
            (module_dir / "sample.py").write_text(
                textwrap.dedent(
                    """
                    __version__ = "9.9.9"

                    class Plugin:
                        MYTHIC_HOOKS = ["before_scan", "after_reflect"]
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            sys.path.insert(0, str(root))
            try:
                app.main(["grimoire", "add", "local_plugins.sample:Plugin", "--path", tmp])

                output = io.StringIO()
                with redirect_stdout(output):
                    code = app.main(["plugin", "inspect", "local_plugins.sample:Plugin", "--path", tmp, "--json"])
            finally:
                try:
                    sys.path.remove(str(root))
                except ValueError:
                    pass

            payload = json.loads(output.getvalue())
            self.assertEqual(code, SUCCESS)
            self.assertEqual(payload["plugin"]["health"]["status"], "healthy")
            self.assertEqual(payload["plugin"]["version"], "9.9.9")
            self.assertEqual(payload["plugin"]["hooks"], ["before_scan", "after_reflect"])


if __name__ == "__main__":
    unittest.main()
