"""Textual TUI for Mythic Vibe CLI.

Optional dependency on ``textual``. Import the public surface lazily so the
rest of the CLI does not pay the import cost or fail when textual is not
installed.
"""

__all__ = ["build_status_data"]


def __getattr__(name: str):
    """Lazy-import picker / runner symbols so the missing-textual fallback test
    path keeps working — those modules import textual at top level."""
    picker_names = {
        "CommandPreviewScreen",
        "PickerEntry",
        "SlashPickerScreen",
        "filter_entries",
        "gather_picker_entries",
    }
    runner_names = {"RunningCommandScreen", "RunSpec", "command_for_builtin"}
    if name == "build_status_data":
        from .app import build_status_data

        return build_status_data
    if name in picker_names:
        from . import picker

        return getattr(picker, name)
    if name in runner_names:
        from . import runner

        return getattr(runner, name)
    raise AttributeError(name)
