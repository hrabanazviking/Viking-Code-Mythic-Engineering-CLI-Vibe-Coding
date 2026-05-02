"""Tests for PH-02 slice 2.6 — plugin slash dispatch contract.

The slice extends ``SlashCommandInfo`` with an optional ``argv``
field. A plugin that contributes a slash entry can supply the
exact argv list it wants subprocess-launched; the TUI picker uses
that list to dispatch via ``RunningCommandScreen`` instead of the
"plugin dispatch not yet implemented" fallback.

Tested in three layers:

1. Pure dataclass — ``SlashCommandInfo`` round-trip with and
   without an argv field, default is empty tuple.
2. ``PickerEntry`` propagation — `from_contributed` copies argv
   through; `is_dispatchable` flips True only when argv non-empty
   (or source == "builtin").
3. Headless TUI — pressing `r` on a contributed entry with argv
   pushes a `RunningCommandScreen`; pressing `r` on a contributed
   entry without argv is a no-op (stays on the preview screen).
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path


textual_unavailable = False
try:
    import textual  # noqa: F401
except ImportError:
    textual_unavailable = True


from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo  # noqa: E402
from mythic_vibe_cli.runtime.source_info import synthetic_source_info  # noqa: E402


def _src(path: str) -> object:
    """Build a SourceInfo for tests via the synthetic helper, matching the
    pattern the plugin dispatcher uses when contributing slash entries."""
    return synthetic_source_info(path, source="test")


# ---- Layer 1: SlashCommandInfo dataclass ------------------------------


class SlashCommandInfoArgvTests(unittest.TestCase):
    def test_default_argv_is_empty_tuple(self) -> None:
        info = SlashCommandInfo(
            name="hello",
            source="plugin",
            source_info=_src("myplugin:HelloPlugin"),
            description="say hi",
        )
        self.assertEqual(info.argv, ())

    def test_argv_round_trips_through_to_dict(self) -> None:
        info = SlashCommandInfo(
            name="ritual",
            source="extension",
            source_info=_src("ritual_ext.py"),
            description="run a ritual",
            argv=("python", "-m", "myritual", "go"),
        )
        payload = info.to_dict()
        self.assertEqual(payload["argv"], ["python", "-m", "myritual", "go"])
        # Roundtrip retains tuple semantics on the dataclass; the
        # serialised form is a list (JSON-friendly).
        self.assertEqual(info.argv, ("python", "-m", "myritual", "go"))

    def test_argv_is_immutable_via_frozen_dataclass(self) -> None:
        info = SlashCommandInfo(
            name="x",
            source="plugin",
            source_info=_src("x:Plugin"),
        )
        with self.assertRaises(Exception):
            info.argv = ("nope",)  # type: ignore[misc]


# ---- Layer 2: PickerEntry propagation ---------------------------------


class PickerEntryDispatchAuditTests(unittest.TestCase):
    def test_builtin_entry_is_always_dispatchable(self) -> None:
        from mythic_vibe_cli.runtime.slash_commands import BuiltinSlashCommand
        from mythic_vibe_cli.tui.picker import PickerEntry

        entry = PickerEntry.from_builtin(BuiltinSlashCommand("scan", "scan project"))
        self.assertTrue(entry.is_dispatchable)
        self.assertEqual(entry.argv, ())

    def test_contributed_without_argv_is_not_dispatchable(self) -> None:
        from mythic_vibe_cli.tui.picker import PickerEntry

        info = SlashCommandInfo(
            name="ritual",
            source="extension",
            source_info=_src("ritual.py"),
            description="alpha",
        )
        entry = PickerEntry.from_contributed(info)
        self.assertEqual(entry.argv, ())
        self.assertFalse(entry.is_dispatchable)

    def test_contributed_with_argv_is_dispatchable(self) -> None:
        from mythic_vibe_cli.tui.picker import PickerEntry

        info = SlashCommandInfo(
            name="ritual",
            source="plugin",
            source_info=_src("ritual:Plugin"),
            description="alpha",
            argv=("python", "-c", "print('ok')"),
        )
        entry = PickerEntry.from_contributed(info)
        self.assertEqual(entry.argv, ("python", "-c", "print('ok')"))
        self.assertTrue(entry.is_dispatchable)


# ---- Layer 3: Headless TUI dispatch -----------------------------------


@unittest.skipIf(textual_unavailable, "textual not installed")
class CommandPreviewScreenDispatchTests(unittest.TestCase):
    """`r` from the preview screen runs only when the entry is
    dispatchable. Slice 2.6 widens that gate from `source == "builtin"`
    to `is_dispatchable` — covering plugin entries that registered an
    argv."""

    def test_contributed_entry_with_argv_runs_via_runner(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import CommandPreviewScreen, PickerEntry
        from mythic_vibe_cli.tui.runner import RunningCommandScreen

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    entry = PickerEntry(
                        name="quickexit",
                        description="A plugin slash that exits cleanly",
                        source="plugin",
                        source_info_path="quickexit:Plugin",
                        argv=(sys.executable, "-c", "import sys; sys.exit(0)"),
                    )
                    app.push_screen(
                        CommandPreviewScreen(entry, project_root=Path(tmp))
                    )
                    await pilot.pause()
                    await pilot.press("r")
                    for _ in range(5):
                        await pilot.pause()
                    return isinstance(app.screen, RunningCommandScreen)

        self.assertTrue(asyncio.run(run_test()))

    def test_contributed_entry_without_argv_is_a_noop(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import CommandPreviewScreen, PickerEntry

        async def run_test() -> bool:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    entry = PickerEntry(
                        name="undispatchable",
                        description="plugin without registered argv",
                        source="plugin",
                        source_info_path="undisp:Plugin",
                        argv=(),
                    )
                    app.push_screen(
                        CommandPreviewScreen(entry, project_root=Path(tmp))
                    )
                    await pilot.pause()
                    await pilot.press("r")
                    await pilot.pause()
                    # The preview screen stays on top — no runner pushed.
                    return type(app.screen).__name__ == "CommandPreviewScreen"

        self.assertTrue(asyncio.run(run_test()))

    def test_preview_body_changes_hint_when_dispatchable(self) -> None:
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import CommandPreviewScreen, PickerEntry

        async def run_test() -> tuple[str, str]:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    await pilot.pause()
                    dispatchable = PickerEntry(
                        name="goes",
                        description="dispatchable",
                        source="plugin",
                        argv=(sys.executable, "-c", "pass"),
                    )
                    not_dispatchable = PickerEntry(
                        name="stays",
                        description="not yet",
                        source="plugin",
                        argv=(),
                    )
                    app.push_screen(
                        CommandPreviewScreen(dispatchable, project_root=Path(tmp))
                    )
                    await pilot.pause()
                    a = str(app.screen.query_one("#preview-card").render())
                    app.pop_screen()
                    await pilot.pause()
                    app.push_screen(
                        CommandPreviewScreen(
                            not_dispatchable, project_root=Path(tmp)
                        )
                    )
                    await pilot.pause()
                    b = str(app.screen.query_one("#preview-card").render())
                    return a, b

        runnable, gated = asyncio.run(run_test())
        self.assertIn("Press r", runnable)
        self.assertIn("not yet implemented", gated)


# ---- Plugin dispatcher round-trip -------------------------------------


class PluginDispatcherSlashArgvRoundTripTests(unittest.TestCase):
    """A plugin whose ``slash_commands()`` returns
    ``SlashCommandInfo(... argv=...)`` must have its argv survive
    discovery and land in the picker as a dispatchable entry."""

    def test_dispatcher_preserves_argv_through_discovery(self) -> None:
        import textwrap

        from mythic_vibe_cli.plugins import PluginHookDispatcher, PluginRegistry

        plugin_module_text = textwrap.dedent(
            """
            from mythic_vibe_cli.runtime.slash_commands import SlashCommandInfo
            from mythic_vibe_cli.runtime.source_info import synthetic_source_info

            class Plugin:
                @classmethod
                def slash_commands(cls):
                    return [
                        SlashCommandInfo(
                            name="unit-test-slash",
                            source="plugin",
                            source_info=synthetic_source_info(
                                "synth_slash_plugin:Plugin", source="plugin"
                            ),
                            description="unit-test slash",
                            argv=("python", "-c", "print(1)"),
                        ),
                    ]
            """
        )

        with tempfile.TemporaryDirectory() as project_root:
            plugin_dir = tempfile.mkdtemp()
            try:
                plugin_file = Path(plugin_dir) / "synth_slash_plugin.py"
                plugin_file.write_text(plugin_module_text, encoding="utf-8")
                sys.path.insert(0, plugin_dir)
                try:
                    registry = PluginRegistry(Path(project_root))
                    registry.add("synth_slash_plugin:Plugin", hooks=[])

                    with PluginHookDispatcher(Path(project_root)) as dispatcher:
                        dispatcher.load_and_subscribe()
                        discovered = dispatcher.discover_slash_commands()
                finally:
                    try:
                        sys.path.remove(plugin_dir)
                    except ValueError:
                        pass
                    sys.modules.pop("synth_slash_plugin", None)
            finally:
                import shutil

                shutil.rmtree(plugin_dir, ignore_errors=True)

        names = [info.name for info in discovered]
        self.assertIn("unit-test-slash", names)
        match = next(info for info in discovered if info.name == "unit-test-slash")
        self.assertEqual(match.argv, ("python", "-c", "print(1)"))


# ---- Phase C 2026-05-02 (audit remediation): in-process run_slash ----
#
# A plugin can opt into in-process slash dispatch by:
#   1. Setting ``runnable=True`` on its SlashCommandInfo entries
#   2. Implementing a ``run_slash(name, args) -> SlashRunResult`` method
# The PluginHookDispatcher's new ``dispatch_slash(name, args)`` walks
# loaded plugins and returns the first ``handled=True`` result, or
# None if no plugin claims the slash. The TUI picker presses this for
# entries with dispatch_mode == "run_slash".


class SlashCommandInfoRunnableTests(unittest.TestCase):
    """``runnable`` is the additive Phase C field. Default False keeps
    pre-Phase-C plugins behaviour-identical; True opts the entry into
    the in-process run_slash dispatch path."""

    def test_default_runnable_is_false(self) -> None:
        info = SlashCommandInfo(
            name="hello",
            source="plugin",
            source_info=_src("myplugin:HelloPlugin"),
        )
        self.assertFalse(info.runnable)

    def test_runnable_round_trips_through_to_dict(self) -> None:
        info = SlashCommandInfo(
            name="ritual",
            source="plugin",
            source_info=_src("rp.py"),
            runnable=True,
        )
        payload = info.to_dict()
        self.assertEqual(payload["runnable"], True)


class PickerEntryRunnableTests(unittest.TestCase):
    """``PickerEntry.from_contributed`` reads the new field; the
    ``dispatch_mode`` property classifies entries into builtin / argv
    / run_slash / none for downstream dispatch routing."""

    def _info(
        self,
        *,
        argv: tuple[str, ...] = (),
        runnable: bool = False,
    ) -> SlashCommandInfo:
        return SlashCommandInfo(
            name="x",
            source="plugin",
            source_info=_src("p:Plugin"),
            description="x",
            argv=argv,
            runnable=runnable,
        )

    def test_from_contributed_propagates_runnable(self) -> None:
        from mythic_vibe_cli.tui.picker import PickerEntry

        entry = PickerEntry.from_contributed(self._info(runnable=True))
        self.assertTrue(entry.runnable)
        self.assertTrue(entry.is_dispatchable)

    def test_dispatch_mode_run_slash_when_runnable_only(self) -> None:
        from mythic_vibe_cli.tui.picker import PickerEntry

        entry = PickerEntry.from_contributed(self._info(runnable=True))
        self.assertEqual(entry.dispatch_mode, "run_slash")

    def test_dispatch_mode_argv_when_argv_only(self) -> None:
        from mythic_vibe_cli.tui.picker import PickerEntry

        entry = PickerEntry.from_contributed(
            self._info(argv=("python", "-c", "1"))
        )
        self.assertEqual(entry.dispatch_mode, "argv")

    def test_dispatch_mode_argv_takes_priority_over_run_slash(self) -> None:
        """If a plugin opts into BOTH argv and runnable, the argv
        subprocess path wins — it's the older contract and operators
        with both can fall back to the in-process path by clearing
        argv. Behaviour locked here so a future change is deliberate."""
        from mythic_vibe_cli.tui.picker import PickerEntry

        entry = PickerEntry.from_contributed(
            self._info(argv=("python", "-c", "1"), runnable=True)
        )
        self.assertEqual(entry.dispatch_mode, "argv")

    def test_dispatch_mode_none_when_neither(self) -> None:
        from mythic_vibe_cli.tui.picker import PickerEntry

        entry = PickerEntry.from_contributed(self._info())
        self.assertEqual(entry.dispatch_mode, "none")
        self.assertFalse(entry.is_dispatchable)

    def test_dispatch_mode_builtin_for_builtins(self) -> None:
        from mythic_vibe_cli.runtime.slash_commands import BuiltinSlashCommand
        from mythic_vibe_cli.tui.picker import PickerEntry

        entry = PickerEntry.from_builtin(
            BuiltinSlashCommand(name="status", description="builtin")
        )
        self.assertEqual(entry.dispatch_mode, "builtin")


class PluginDispatcherRunSlashTests(unittest.TestCase):
    """``PluginHookDispatcher.dispatch_slash`` walks loaded plugins,
    invokes their ``run_slash(name, args)`` via :func:`safe_call`, and
    returns the first ``SlashRunResult`` whose ``handled=True``."""

    def _make_loaded_plugin(self, plugin_obj: object, *, entrypoint: str = "p:Plugin"):
        """Construct a _LoadedPlugin record for a fake plugin object,
        bypassing the registry/loader so the test focuses on
        dispatch_slash semantics."""
        from mythic_vibe_cli.plugins.api import PluginRecord
        from mythic_vibe_cli.plugins.dispatcher import _LoadedPlugin

        return _LoadedPlugin(
            record=PluginRecord(entrypoint=entrypoint),
            plugin_obj=plugin_obj,
            hooks=[],
        )

    def _empty_dispatcher(self):
        from mythic_vibe_cli.plugins.dispatcher import PluginHookDispatcher

        return PluginHookDispatcher(Path("."))

    def test_returns_handled_result(self) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult

        captured: list[tuple[str, tuple[str, ...]]] = []

        class FakePlugin:
            @staticmethod
            def run_slash(name, args):
                captured.append((name, tuple(args)))
                return SlashRunResult(handled=True, output="ran ok", exit_code=0)

        dispatcher = self._empty_dispatcher()
        dispatcher._loaded.append(self._make_loaded_plugin(FakePlugin()))

        result = dispatcher.dispatch_slash("my-slash", ("--flag", "v"))
        self.assertIsNotNone(result)
        self.assertTrue(result.handled)
        self.assertEqual(result.output, "ran ok")
        self.assertEqual(captured, [("my-slash", ("--flag", "v"))])

    def test_returns_none_when_handled_false(self) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult

        class FakePlugin:
            @staticmethod
            def run_slash(name, args):
                return SlashRunResult(handled=False)

        dispatcher = self._empty_dispatcher()
        dispatcher._loaded.append(self._make_loaded_plugin(FakePlugin()))

        result = dispatcher.dispatch_slash("not-mine", ())
        self.assertIsNone(result)

    def test_returns_none_when_no_plugin_has_run_slash(self) -> None:
        class PluginWithoutRunSlash:
            pass

        dispatcher = self._empty_dispatcher()
        dispatcher._loaded.append(
            self._make_loaded_plugin(PluginWithoutRunSlash())
        )

        result = dispatcher.dispatch_slash("anything", ())
        self.assertIsNone(result)

    def test_first_handled_wins_over_subsequent_plugins(self) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult

        called: list[str] = []

        class FirstPlugin:
            @staticmethod
            def run_slash(name, args):
                called.append("first")
                return SlashRunResult(handled=True, output="from first")

        class SecondPlugin:
            @staticmethod
            def run_slash(name, args):
                called.append("second")
                return SlashRunResult(handled=True, output="from second")

        dispatcher = self._empty_dispatcher()
        dispatcher._loaded.append(
            self._make_loaded_plugin(FirstPlugin(), entrypoint="first:P")
        )
        dispatcher._loaded.append(
            self._make_loaded_plugin(SecondPlugin(), entrypoint="second:P")
        )

        result = dispatcher.dispatch_slash("a", ())
        self.assertEqual(result.output, "from first")
        self.assertEqual(called, ["first"])

    def test_handled_false_falls_through_to_next_plugin(self) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult

        class FirstDeclines:
            @staticmethod
            def run_slash(name, args):
                return SlashRunResult(handled=False)

        class SecondHandles:
            @staticmethod
            def run_slash(name, args):
                return SlashRunResult(handled=True, output="second handled")

        dispatcher = self._empty_dispatcher()
        dispatcher._loaded.append(
            self._make_loaded_plugin(FirstDeclines(), entrypoint="first:P")
        )
        dispatcher._loaded.append(
            self._make_loaded_plugin(SecondHandles(), entrypoint="second:P")
        )

        result = dispatcher.dispatch_slash("a", ())
        self.assertIsNotNone(result)
        self.assertEqual(result.output, "second handled")

    def test_plugin_that_raises_is_skipped_via_safe_call(self) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult

        class Misbehaving:
            @staticmethod
            def run_slash(name, args):
                raise RuntimeError("boom")

        class GoodPlugin:
            @staticmethod
            def run_slash(name, args):
                return SlashRunResult(handled=True, output="recovered")

        dispatcher = self._empty_dispatcher()
        dispatcher._loaded.append(
            self._make_loaded_plugin(Misbehaving(), entrypoint="bad:P")
        )
        dispatcher._loaded.append(
            self._make_loaded_plugin(GoodPlugin(), entrypoint="good:P")
        )

        result = dispatcher.dispatch_slash("a", ())
        self.assertIsNotNone(result)
        self.assertEqual(result.output, "recovered")

    def test_plugin_returning_non_slashrunresult_is_skipped(self) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult

        class WrongType:
            @staticmethod
            def run_slash(name, args):
                return "I should be a SlashRunResult"

        class GoodPlugin:
            @staticmethod
            def run_slash(name, args):
                return SlashRunResult(handled=True, output="recovered")

        dispatcher = self._empty_dispatcher()
        dispatcher._loaded.append(
            self._make_loaded_plugin(WrongType(), entrypoint="bad:P")
        )
        dispatcher._loaded.append(
            self._make_loaded_plugin(GoodPlugin(), entrypoint="good:P")
        )

        result = dispatcher.dispatch_slash("a", ())
        self.assertIsNotNone(result)
        self.assertEqual(result.output, "recovered")


@unittest.skipIf(textual_unavailable, "textual not installed")
class PluginSlashRunScreenTests(unittest.TestCase):
    """Headless TUI integration: pressing 'r' on a runnable=True
    contributed entry pushes ``PluginSlashRunScreen``, which dispatches
    via the plugin dispatcher and renders the result. Plugin failures
    surface as clean error text rather than crashes."""

    def test_run_slash_screen_renders_handled_result(self) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult
        from mythic_vibe_cli.plugins.dispatcher import PluginHookDispatcher
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import PickerEntry, PluginSlashRunScreen
        from unittest.mock import patch

        entry = PickerEntry(
            name="hello-plugin",
            description="say hi",
            source="plugin",
            source_info_path="myplugin:Plugin",
            runnable=True,
        )

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    # Patch dispatch_slash to return a known result.
                    with patch.object(
                        PluginHookDispatcher,
                        "dispatch_slash",
                        return_value=SlashRunResult(
                            handled=True, output="hi from plugin", exit_code=0
                        ),
                    ):
                        app.push_screen(
                            PluginSlashRunScreen(entry, project_root=Path(tmp))
                        )
                        await pilot.pause()
                        rendered = str(
                            app.screen.query_one("#plugin-slash-card").render()
                        )
            return rendered

        rendered = asyncio.run(run_test())
        self.assertIn("hi from plugin", rendered)
        self.assertIn("Exit code", rendered)

    def test_run_slash_screen_renders_no_handler_message_when_none(self) -> None:
        from mythic_vibe_cli.plugins.dispatcher import PluginHookDispatcher
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import PickerEntry, PluginSlashRunScreen
        from unittest.mock import patch

        entry = PickerEntry(
            name="orphan",
            description="no handler",
            source="plugin",
            source_info_path="orphan:Plugin",
            runnable=True,
        )

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    with patch.object(
                        PluginHookDispatcher, "dispatch_slash", return_value=None
                    ):
                        app.push_screen(
                            PluginSlashRunScreen(entry, project_root=Path(tmp))
                        )
                        await pilot.pause()
                        rendered = str(
                            app.screen.query_one("#plugin-slash-card").render()
                        )
            return rendered

        rendered = asyncio.run(run_test())
        self.assertIn("no plugin claimed this slash", rendered)

    def test_run_slash_screen_renders_error_when_dispatcher_raises(self) -> None:
        from mythic_vibe_cli.plugins.dispatcher import PluginHookDispatcher
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import PickerEntry, PluginSlashRunScreen
        from unittest.mock import patch

        entry = PickerEntry(
            name="boom",
            description="raises",
            source="plugin",
            source_info_path="boom:Plugin",
            runnable=True,
        )

        async def run_test() -> str:
            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    with patch.object(
                        PluginHookDispatcher,
                        "dispatch_slash",
                        side_effect=RuntimeError("dispatcher exploded"),
                    ):
                        app.push_screen(
                            PluginSlashRunScreen(entry, project_root=Path(tmp))
                        )
                        await pilot.pause()
                        rendered = str(
                            app.screen.query_one("#plugin-slash-card").render()
                        )
            return rendered

        rendered = asyncio.run(run_test())
        self.assertIn("Error", rendered)
        self.assertIn("dispatcher exploded", rendered)


@unittest.skipIf(textual_unavailable, "textual not installed")
class PreviewScreenRunSlashRoutingTests(unittest.TestCase):
    """Pressing 'r' on a plugin entry with ``runnable=True`` (no argv)
    pushes ``PluginSlashRunScreen``, not ``RunningCommandScreen``."""

    def test_preview_screen_routes_runnable_entry_to_plugin_slash_screen(
        self,
    ) -> None:
        from mythic_vibe_cli.plugins.api import SlashRunResult
        from mythic_vibe_cli.plugins.dispatcher import PluginHookDispatcher
        from mythic_vibe_cli.tui.app import MythicTuiApp
        from mythic_vibe_cli.tui.picker import (
            CommandPreviewScreen,
            PickerEntry,
            PluginSlashRunScreen,
        )
        from unittest.mock import patch

        entry = PickerEntry(
            name="run-slash-only",
            description="protocol-only",
            source="plugin",
            source_info_path="proto:Plugin",
            runnable=True,
        )

        async def run_test() -> tuple[str, list[type]]:
            screen_classes: list[type] = []

            with tempfile.TemporaryDirectory() as tmp:
                app = MythicTuiApp(Path(tmp))
                async with app.run_test() as pilot:
                    with patch.object(
                        PluginHookDispatcher,
                        "dispatch_slash",
                        return_value=SlashRunResult(
                            handled=True, output="ok"
                        ),
                    ):
                        app.push_screen(
                            CommandPreviewScreen(
                                entry, project_root=Path(tmp)
                            )
                        )
                        await pilot.pause()
                        rendered = str(
                            app.screen.query_one("#preview-card").render()
                        )
                        # Trigger the run action.
                        app.screen.action_run_command()
                        await pilot.pause()
                        # The screen now on top should be the plugin-slash one.
                        screen_classes.append(type(app.screen))
            return rendered, screen_classes

        rendered, screen_classes = asyncio.run(run_test())
        self.assertIn("Press r", rendered)
        self.assertIn("in-process", rendered)
        self.assertIn(PluginSlashRunScreen, screen_classes)


if __name__ == "__main__":
    unittest.main()
