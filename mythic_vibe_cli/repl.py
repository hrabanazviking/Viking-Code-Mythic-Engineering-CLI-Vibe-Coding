"""Minimal interactive REPL for Mythic Vibe CLI.

This module ships the first interactive surface for the CLI. It is not a TUI
(no Textual, no rendering library, no live regions). The loop reads command
lines from stdin via ``input()``, dispatches them by re-entering
``app.main(argv)``, and handles a small set of slash directives directly
(``/help``, ``/quit``, ``/exit``).

Design notes:

- The function signature accepts ``stdin``/``stdout``/``stderr`` as injected
  file-likes so tests can drive the loop without monkey-patching ``sys.*``.
- ``shlex.split()`` is used for line parsing so quoted arguments work.
- ``app.main`` re-entrance is the dispatch mechanism. Each command runs
  through the full argparse + handler stack so the ``--json`` guard, plugin
  dispatcher, and timing primitives all behave exactly as they do at the
  top-level CLI.
- Plugin-contributed slash commands surface in ``/help`` (via the
  slash-commands discovery hook) but are not dispatched in this slice;
  dispatching by plugin-contributed name needs design work that belongs in
  a follow-on.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import IO, Callable

from .exit_codes import SUCCESS, USER_INPUT_ERROR
from .runtime.slash_commands import BUILTIN_SLASH_COMMANDS


PROMPT = "mythic-vibe> "
BANNER = (
    "mythic-vibe shell — type a command or /help. /quit or Ctrl+D exits."
)
QUIT_TOKENS = frozenset({"/quit", "/exit"})
HELP_TOKENS = frozenset({"/help", "/?"})


def _print_help(stdout: IO[str], project_root: Path) -> None:
    """Print the slash-command catalog (builtin + plugin-contributed)."""
    print("Builtin slash commands:", file=stdout)
    for entry in BUILTIN_SLASH_COMMANDS:
        print(f"  /{entry.name}\t{entry.description}", file=stdout)

    # Late-import the dispatcher so the REPL module stays cheap to import.
    try:
        from .plugins.dispatcher import PluginHookDispatcher
    except ImportError:
        return

    try:
        with PluginHookDispatcher(project_root) as dispatcher:
            dispatcher.load_and_subscribe()
            contributed = dispatcher.discover_slash_commands()
    except Exception:  # noqa: BLE001 - help should never crash the REPL
        return

    if not contributed:
        return
    print("Contributed slash commands:", file=stdout)
    for item in contributed:
        description = item.description or "(no description)"
        print(f"  /{item.name}\t{description}\t[{item.source}]", file=stdout)


def _print_help_for_name(
    name: str,
    *,
    stdout: IO[str],
    stderr: IO[str],
    project_root: Path,
    main: Callable[[list[str]], int],
) -> None:
    """Route ``/help <name>`` to ``slash inspect <name>`` so help text
    comes from the same source as the CLI's introspection surface."""
    code = main(["slash", "inspect", "--path", str(project_root), name])
    if code != SUCCESS:
        print(f"(slash inspect exit code: {code})", file=stderr)


def run_shell(
    *,
    stdin: IO[str] | None = None,
    stdout: IO[str] | None = None,
    stderr: IO[str] | None = None,
    main: Callable[[list[str]], int] | None = None,
    project_root: Path | None = None,
) -> int:
    """Run the REPL loop until EOF or ``/quit``.

    Returns ``SUCCESS`` (0) on clean exit. The loop never propagates command
    failures — they are reported inline and the prompt continues.
    """
    in_stream = stdin if stdin is not None else sys.stdin
    out_stream = stdout if stdout is not None else sys.stdout
    err_stream = stderr if stderr is not None else sys.stderr
    project_path = project_root if project_root is not None else Path.cwd()

    if main is None:
        from .app import main as app_main

        main = app_main

    print(BANNER, file=out_stream)

    while True:
        print(PROMPT, end="", file=out_stream, flush=True)
        try:
            line = in_stream.readline()
        except KeyboardInterrupt:
            print("(interrupted; type /quit to exit)", file=out_stream)
            continue

        if line == "":  # EOF
            print("", file=out_stream)
            return SUCCESS

        stripped = line.strip()
        if not stripped:
            continue

        if stripped in QUIT_TOKENS:
            return SUCCESS

        if stripped in HELP_TOKENS:
            _print_help(out_stream, project_path)
            continue

        # /help <name> routes to `slash inspect <name>` so the operator
        # sees the canonical introspection output (description, source,
        # argparse --help) rather than just the catalog.
        first_token, _, rest = stripped.partition(" ")
        if first_token in HELP_TOKENS and rest.strip():
            target = rest.strip().lstrip("/")
            _print_help_for_name(
                target,
                stdout=out_stream,
                stderr=err_stream,
                project_root=project_path,
                main=main,
            )
            continue

        # Strip a single leading slash if present so /scan and scan are equivalent.
        argv_text = stripped[1:] if stripped.startswith("/") and not stripped.startswith("//") else stripped
        try:
            argv = shlex.split(argv_text)
        except ValueError as exc:
            print(f"Parse error: {exc}", file=err_stream)
            continue
        if not argv:
            continue

        try:
            code = main(argv)
        except SystemExit as exc:
            # argparse may sys.exit(2) on a bad command; surface the code, do not exit the loop.
            code = int(exc.code) if isinstance(exc.code, int) else USER_INPUT_ERROR
        except KeyboardInterrupt:
            print("(command interrupted)", file=out_stream)
            continue
        except Exception as exc:  # noqa: BLE001 - REPL should never crash on a bad command
            print(f"Command failed: {exc}", file=err_stream)
            continue

        if code != SUCCESS:
            print(f"(exit code: {code})", file=out_stream)
