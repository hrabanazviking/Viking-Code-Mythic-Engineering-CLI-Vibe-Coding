"""Tests for the slice-10.6 reference plugin.

The reference plugin lives outside the main package
(``examples/plugins/mythic_vibe_example_plugin``) and isn't on
``sys.path`` by default. We exercise it by adding the example
directory to ``sys.path`` for the test, importing the module
directly, then asserting it satisfies every Protocol + hook
contract.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_PLUGIN_SRC = (
    REPO_ROOT / "examples" / "plugins" / "mythic_vibe_example_plugin" / "src"
)


def _import_example_plugin():
    """Add the example plugin's ``src/`` to sys.path and import."""
    sys.path.insert(0, str(EXAMPLE_PLUGIN_SRC))
    try:
        import mythic_vibe_example_plugin

        return mythic_vibe_example_plugin
    finally:
        # Leave path inserted; subsequent test modules may also import it.
        pass


class ReferencePluginShapeTests(unittest.TestCase):
    def test_plugin_module_loads(self) -> None:
        module = _import_example_plugin()
        self.assertTrue(hasattr(module, "plugin"))
        self.assertTrue(hasattr(module, "ExamplePlugin"))

    def test_plugin_declares_all_eight_hooks(self) -> None:
        from mythic_vibe_cli.plugins.api import PLUGIN_HOOKS

        module = _import_example_plugin()
        plugin = module.plugin
        for hook in PLUGIN_HOOKS:
            self.assertTrue(
                callable(getattr(plugin, hook, None)),
                f"reference plugin missing hook {hook!r}",
            )

    def test_plugin_satisfies_all_six_extension_points(self) -> None:
        from mythic_vibe_cli.plugins.extension_points import (
            EXTENSION_POINT_CATEGORIES,
            categorise_plugin,
        )

        module = _import_example_plugin()
        categories = categorise_plugin(module.plugin)
        self.assertEqual(set(categories), set(EXTENSION_POINT_CATEGORIES))

    def test_plugin_version_string(self) -> None:
        module = _import_example_plugin()
        self.assertEqual(module.plugin.__version__, module.__version__)
        self.assertEqual(module.__version__, "0.1.0")


class ReferencePluginHookBehaviourTests(unittest.TestCase):
    """Exercise the hook implementations directly. Each hook
    appends one line to the project's plugin log; we use a temp
    project root and confirm the file lands."""

    def test_hook_writes_log_line(self) -> None:
        import tempfile

        module = _import_example_plugin()
        plugin = module.plugin
        with tempfile.TemporaryDirectory() as tmp:
            payload = {"path": tmp}
            plugin.before_scan(payload)
            plugin.after_verify(payload)
            log = Path(tmp) / "mythic" / "plugins" / "example.log"
            self.assertTrue(log.is_file())
            entries = log.read_text(encoding="utf-8").splitlines()
            self.assertIn("before_scan", entries)
            self.assertIn("after_verify", entries)

    def test_hook_swallows_filesystem_errors(self) -> None:
        """Hook calls must not raise even when the log path is
        unwritable. We mock log_dir to point at something
        guaranteed to fail on mkdir."""
        module = _import_example_plugin()
        plugin = module.plugin

        with mock.patch.object(
            module, "_log_dir", side_effect=OSError("read-only")
        ):
            # Must not raise.
            plugin.before_scan({"path": "/tmp"})


class ReferencePluginExtensionContributionsTests(unittest.TestCase):
    def test_rituals_returns_iterable(self) -> None:
        module = _import_example_plugin()
        rituals = list(module.plugin.rituals())
        self.assertIn("example_ritual", rituals)

    def test_verification_gate_passes(self) -> None:
        module = _import_example_plugin()
        gates = module.plugin.verification_gates()
        self.assertIn("example.always_pass", gates)
        gate_fn = gates["example.always_pass"]

        # Call the gate. With CLI on the test env's sys.path it
        # returns a real VerificationResult; otherwise None.
        result = gate_fn(None, None, None, None)
        if result is not None:
            self.assertTrue(getattr(result, "passed", False))

    def test_artifact_templates_returns_string(self) -> None:
        module = _import_example_plugin()
        templates = module.plugin.artifact_templates()
        self.assertIn("example_artefact", templates)
        body = templates["example_artefact"]
        self.assertIsInstance(body, str)
        self.assertIn("{title}", body)

    def test_slash_commands_returns_slash_command_infos(self) -> None:
        from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo

        module = _import_example_plugin()
        commands = list(module.plugin.slash_commands())
        self.assertEqual(len(commands), 1)
        self.assertIsInstance(commands[0], SlashCommandInfo)
        self.assertEqual(commands[0].name, "example")


if __name__ == "__main__":
    unittest.main()
