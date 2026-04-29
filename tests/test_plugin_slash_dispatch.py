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


if __name__ == "__main__":
    unittest.main()
