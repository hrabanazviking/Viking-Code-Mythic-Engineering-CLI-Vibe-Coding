"""Tests for ``mythic_vibe_cli.plugins.dispatcher.PluginHookDispatcher``."""

from __future__ import annotations

import importlib
import io
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from mythic_vibe_cli.plugins import PluginHookDispatcher, PluginRegistry


class _SyntheticPluginHarness:
    """Helper that materializes a synthetic plugin module in a temp dir."""

    def __init__(self, name: str, body: str) -> None:
        self.name = name
        self.body = textwrap.dedent(body)
        self._tempdir: tempfile.TemporaryDirectory | None = None
        self.module_path: Path | None = None

    def __enter__(self) -> "_SyntheticPluginHarness":
        self._tempdir = tempfile.TemporaryDirectory()
        plugin_dir = Path(self._tempdir.name)
        plugin_file = plugin_dir / f"{self.name}.py"
        plugin_file.write_text(self.body, encoding="utf-8")
        self.module_path = plugin_file
        sys.path.insert(0, str(plugin_dir))
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._tempdir is None:
            return
        try:
            sys.path.remove(str(self._tempdir.name))
        except ValueError:
            pass
        sys.modules.pop(self.name, None)
        self._tempdir.cleanup()
        self._tempdir = None


class PluginHookDispatcherTests(unittest.TestCase):
    def test_dispatcher_emits_to_subscribed_plugin(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_plugin_a",
                """
                class Plugin:
                    received = []

                    @classmethod
                    def before_scan(cls, payload):
                        cls.received.append(("before", payload))

                    @classmethod
                    def after_scan(cls, payload):
                        cls.received.append(("after", payload))
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add("synth_plugin_a:Plugin", hooks=["before_scan", "after_scan"])

                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    loaded = dispatcher.load_and_subscribe()
                    dispatcher.emit("before_scan", {"path": project_root})
                    dispatcher.emit("after_scan", {"path": project_root, "ok": True})

                module = importlib.import_module("synth_plugin_a")
                received = module.Plugin.received
                self.assertEqual(loaded, 1)
                self.assertEqual(len(received), 2)
                self.assertEqual(received[0][0], "before")
                self.assertEqual(received[1][0], "after")
                self.assertEqual(received[1][1]["ok"], True)
                module.Plugin.received.clear()

    def test_disabled_plugin_is_not_subscribed(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_plugin_b",
                """
                class Plugin:
                    received = []

                    @classmethod
                    def before_scan(cls, payload):
                        cls.received.append(payload)
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add("synth_plugin_b:Plugin", hooks=["before_scan"])
                registry.disable("synth_plugin_b:Plugin")

                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    loaded = dispatcher.load_and_subscribe()
                    dispatcher.emit("before_scan", {"path": project_root})

                module = importlib.import_module("synth_plugin_b")
                self.assertEqual(loaded, 0)
                self.assertEqual(module.Plugin.received, [])
                module.Plugin.received.clear()

    def test_broken_plugin_entrypoint_is_skipped_silently(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            registry = PluginRegistry(Path(project_root))
            registry.add("nonexistent_module:Whatever", hooks=["before_scan"])

            with PluginHookDispatcher(Path(project_root)) as dispatcher:
                loaded = dispatcher.load_and_subscribe()
                dispatcher.emit("before_scan", {"path": project_root})  # must not raise

            self.assertEqual(loaded, 0)

    def test_emit_unknown_hook_raises_value_error(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with PluginHookDispatcher(Path(project_root)) as dispatcher:
                dispatcher.load_and_subscribe()
                with self.assertRaises(ValueError):
                    dispatcher.emit("not_a_hook", None)

    def test_subscribed_hooks_introspection(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_plugin_c",
                """
                class Plugin:
                    @staticmethod
                    def before_scan(payload):
                        return None

                    @staticmethod
                    def after_packet(payload):
                        return None
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add(
                    "synth_plugin_c:Plugin",
                    hooks=["before_scan", "after_packet"],
                )

                dispatcher = PluginHookDispatcher(Path(project_root))
                try:
                    dispatcher.load_and_subscribe()
                    self.assertCountEqual(
                        dispatcher.subscribed_hooks,
                        ["before_scan", "after_packet"],
                    )
                    self.assertEqual(len(dispatcher.loaded_plugins), 1)
                    self.assertEqual(
                        dispatcher.loaded_plugins[0].entrypoint,
                        "synth_plugin_c:Plugin",
                    )
                finally:
                    dispatcher.teardown()

                self.assertEqual(dispatcher.subscribed_hooks, [])
                self.assertEqual(dispatcher.loaded_plugins, [])

    def test_handler_exception_does_not_break_dispatcher(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_plugin_d",
                """
                class BoomPlugin:
                    @staticmethod
                    def before_scan(payload):
                        raise RuntimeError("plugin-explodes")

                class TameplePlugin:
                    received = []

                    @classmethod
                    def before_scan(cls, payload):
                        cls.received.append(payload)
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add("synth_plugin_d:BoomPlugin", hooks=["before_scan"])
                registry.add("synth_plugin_d:TameplePlugin", hooks=["before_scan"])

                buffer = io.StringIO()
                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    dispatcher.load_and_subscribe()
                    with redirect_stderr(buffer):
                        dispatcher.emit("before_scan", {"path": project_root})

                module = importlib.import_module("synth_plugin_d")
                self.assertEqual(len(module.TameplePlugin.received), 1)
                self.assertIn("plugin-explodes", buffer.getvalue())
                # PH-11 wire-in: the sandbox now catches plugin
                # exceptions before the event bus sees them, so the
                # log line is the slice-10.2 sandbox message rather
                # than the bus's "Event handler error" line.
                self.assertIn("Plugin sandbox", buffer.getvalue())
                self.assertIn("before_scan", buffer.getvalue())
                module.TameplePlugin.received.clear()

    def test_sandbox_wire_in_isolates_handler_exceptions(self) -> None:
        """PH-11 sandbox wire-in: a plugin that raises does not
        propagate into the dispatcher; the SandboxResult captures
        the failure and the next emit() proceeds normally."""
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_plugin_sandbox_iso",
                """
                class Plugin:
                    crashes = 0

                    @classmethod
                    def before_scan(cls, payload):
                        cls.crashes += 1
                        raise RuntimeError(f"boom {cls.crashes}")
                """,
            ):
                PluginRegistry(Path(project_root)).add(
                    "synth_plugin_sandbox_iso:Plugin", hooks=["before_scan"]
                )
                buffer = io.StringIO()
                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    dispatcher.load_and_subscribe()
                    with redirect_stderr(buffer):
                        # First emit raises but sandbox swallows.
                        dispatcher.emit("before_scan", {"path": project_root})
                        # Second emit must still work — sandbox per-call.
                        dispatcher.emit("before_scan", {"path": project_root})

                module = importlib.import_module("synth_plugin_sandbox_iso")
                self.assertEqual(module.Plugin.crashes, 2)  # both calls fired
                # Both failures logged via the sandbox path.
                self.assertEqual(buffer.getvalue().count("Plugin sandbox"), 2)

    def test_sandbox_wire_in_enforces_timeout(self) -> None:
        """When MYTHIC_PLUGIN_TIMEOUT_SEC is set, slow plugins are
        flagged as timed_out via the sandbox layer."""
        import os
        import time

        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_plugin_sandbox_timeout",
                """
                import time

                class Plugin:
                    @classmethod
                    def before_scan(cls, payload):
                        time.sleep(0.5)
                """,
            ):
                PluginRegistry(Path(project_root)).add(
                    "synth_plugin_sandbox_timeout:Plugin",
                    hooks=["before_scan"],
                )
                previous = os.environ.pop("MYTHIC_PLUGIN_TIMEOUT_SEC", None)
                os.environ["MYTHIC_PLUGIN_TIMEOUT_SEC"] = "0.05"
                buffer = io.StringIO()
                try:
                    started = time.monotonic()
                    with PluginHookDispatcher(Path(project_root)) as dispatcher:
                        dispatcher.load_and_subscribe()
                        with redirect_stderr(buffer):
                            dispatcher.emit(
                                "before_scan", {"path": project_root}
                            )
                    elapsed = time.monotonic() - started
                finally:
                    os.environ.pop("MYTHIC_PLUGIN_TIMEOUT_SEC", None)
                    if previous is not None:
                        os.environ["MYTHIC_PLUGIN_TIMEOUT_SEC"] = previous
                # Soft deadline fired quickly — total elapsed should
                # be well under the plugin's intended 0.5s sleep
                # because the sandbox returned on timeout.
                self.assertLess(elapsed, 0.4)
                self.assertIn("timed out", buffer.getvalue())

    def test_discover_slash_commands_aggregates_from_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_slash_a",
                """
                class Plugin:
                    @staticmethod
                    def slash_commands():
                        from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo
                        from mythic_vibe_cli.runtime.source_info import synthetic_source_info
                        return [
                            SlashCommandInfo(
                                name="audit",
                                source="plugin",
                                source_info=synthetic_source_info(
                                    "synth_slash_a:Plugin",
                                    source="synth_slash_a",
                                    scope="project",
                                ),
                                description="Audit plugin slash command",
                            )
                        ]
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add("synth_slash_a:Plugin", hooks=[])

                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    dispatcher.load_and_subscribe()
                    discovered = dispatcher.discover_slash_commands()

                self.assertEqual(len(discovered), 1)
                self.assertEqual(discovered[0].name, "audit")
                self.assertEqual(discovered[0].source, "plugin")
                self.assertEqual(discovered[0].source_info.scope, "project")

    def test_discover_slash_commands_skips_plugin_without_method(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_slash_b",
                """
                class Plugin:
                    @classmethod
                    def before_scan(cls, payload):
                        pass
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add("synth_slash_b:Plugin", hooks=["before_scan"])

                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    dispatcher.load_and_subscribe()
                    discovered = dispatcher.discover_slash_commands()

                self.assertEqual(discovered, [])

    def test_discover_slash_commands_isolates_method_exceptions(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_slash_c",
                """
                class BoomPlugin:
                    @staticmethod
                    def slash_commands():
                        raise RuntimeError("slash-explodes")

                class GoodPlugin:
                    @staticmethod
                    def slash_commands():
                        from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo
                        from mythic_vibe_cli.runtime.source_info import synthetic_source_info
                        return [
                            SlashCommandInfo(
                                name="good",
                                source="plugin",
                                source_info=synthetic_source_info(
                                    "synth_slash_c:GoodPlugin",
                                    source="synth_slash_c",
                                ),
                                description="Survivor",
                            )
                        ]
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add("synth_slash_c:BoomPlugin", hooks=[])
                registry.add("synth_slash_c:GoodPlugin", hooks=[])

                buffer = io.StringIO()
                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    dispatcher.load_and_subscribe()
                    with redirect_stderr(buffer):
                        discovered = dispatcher.discover_slash_commands()

                self.assertEqual(len(discovered), 1)
                self.assertEqual(discovered[0].name, "good")
                self.assertIn("slash-explodes", buffer.getvalue())
                self.assertIn("Plugin slash_commands error", buffer.getvalue())

    def test_emit_persists_event_to_project_event_log(self) -> None:
        import json as json_module
        from mythic_vibe_cli.runtime.event_log import event_log_path_for

        with tempfile.TemporaryDirectory() as project_root:
            with PluginHookDispatcher(Path(project_root)) as dispatcher:
                dispatcher.load_and_subscribe()
                dispatcher.emit("before_scan", {"path": project_root})
                dispatcher.emit("after_scan", {"path": project_root, "languages": 0})

            log_path = event_log_path_for(Path(project_root))
            self.assertTrue(log_path.exists())
            with log_path.open("r", encoding="utf-8") as fh:
                lines = [json_module.loads(line) for line in fh if line.strip()]

            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[0]["channel"], "before_scan")
            self.assertEqual(lines[1]["channel"], "after_scan")

    def test_discover_slash_commands_filters_non_slashcommand_items(self) -> None:
        with tempfile.TemporaryDirectory() as project_root:
            with _SyntheticPluginHarness(
                "synth_slash_d",
                """
                class Plugin:
                    @staticmethod
                    def slash_commands():
                        from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo
                        from mythic_vibe_cli.runtime.source_info import synthetic_source_info
                        return [
                            SlashCommandInfo(
                                name="real",
                                source="plugin",
                                source_info=synthetic_source_info("p", source="p"),
                            ),
                            "not-a-slashcommandinfo",
                            42,
                            None,
                        ]
                """,
            ):
                registry = PluginRegistry(Path(project_root))
                registry.add("synth_slash_d:Plugin", hooks=[])

                with PluginHookDispatcher(Path(project_root)) as dispatcher:
                    dispatcher.load_and_subscribe()
                    discovered = dispatcher.discover_slash_commands()

                self.assertEqual(len(discovered), 1)
                self.assertEqual(discovered[0].name, "real")


if __name__ == "__main__":
    unittest.main()
