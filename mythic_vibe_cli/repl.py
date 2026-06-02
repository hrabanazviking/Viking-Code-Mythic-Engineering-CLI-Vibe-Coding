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

from dataclasses import dataclass
import shlex
import subprocess
import sys
from pathlib import Path
from typing import IO, Callable

from .exit_codes import SUCCESS, USER_INPUT_ERROR
from .runtime.slash_commands import BUILTIN_SLASH_COMMANDS


PROMPT = "mythic-vibe> "
BANNER = (
    "Mythic Vibe CLI — companion shell. Type naturally, or use /help."
)
QUIT_TOKENS = frozenset({"/quit", "/exit"})
HELP_TOKENS = frozenset({"/help", "/?"})
MODEL_TOKENS = frozenset({"/model"})


@dataclass(frozen=True)
class ShellContext:
    project_root: Path
    git_root: Path | None
    git_branch: str
    model_provider: str
    model_name: str
    knowledge_status: str
    memory_status: str

    @property
    def display_project(self) -> str:
        if self.git_root is not None:
            return str(self.git_root)
        return str(self.project_root)

    @property
    def display_branch(self) -> str:
        return self.git_branch or "(not a git repo)"

    @property
    def display_model(self) -> str:
        return f"{self.model_provider}/{self.model_name}"


def _git_output(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=1.0,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _detect_shell_context(project_root: Path) -> ShellContext:
    root = project_root.resolve()
    git_root_raw = _git_output(["rev-parse", "--show-toplevel"], root)
    git_root = Path(git_root_raw).resolve() if git_root_raw else None
    git_branch = _git_output(["branch", "--show-current"], root)
    if not git_branch and git_root is not None:
        git_branch = _git_output(["rev-parse", "--short", "HEAD"], root)

    model_provider = "copy-paste"
    model_name = "manual"
    try:
        from .ai.registry import ProviderRegistry

        provider = ProviderRegistry(root=root).providers().get(model_provider)
        if provider is not None:
            model_name = str(getattr(provider, "model", model_name) or model_name)
    except Exception:  # noqa: BLE001 - shell startup should degrade, not crash
        pass

    knowledge_status = "not connected"
    if (root / "mythic" / "project_index.json").exists():
        knowledge_status = "local project index present"

    memory_status = "not initialized"
    if (root / "mythic" / "conversations").exists() or (root / ".mythic" / "memory.sqlite").exists():
        memory_status = "local memory present"

    return ShellContext(
        project_root=root,
        git_root=git_root,
        git_branch=git_branch,
        model_provider=model_provider,
        model_name=model_name,
        knowledge_status=knowledge_status,
        memory_status=memory_status,
    )


def _print_banner(stdout: IO[str], context: ShellContext) -> None:
    print(BANNER, file=stdout)
    print(f"Project: {context.display_project}", file=stdout)
    print(f"Branch: {context.display_branch}", file=stdout)
    print(f"Model: {context.display_model}", file=stdout)
    print(f"Memory: {context.memory_status}", file=stdout)
    print(f"Knowledge: {context.knowledge_status}", file=stdout)


def _print_model(stdout: IO[str], context: ShellContext) -> None:
    print("Model", file=stdout)
    print(f"  Provider: {context.model_provider}", file=stdout)
    print(f"  Model: {context.model_name}", file=stdout)
    print("  Routing: local shell fallback until the model router phase is wired", file=stdout)


def _looks_like_command(stripped: str, main_commands: set[str]) -> bool:
    if stripped.startswith("/"):
        return True
    try:
        argv = shlex.split(stripped)
    except ValueError:
        return True
    return bool(argv and argv[0] in main_commands)


def _known_command_names(_main: Callable[[list[str]], int]) -> set[str]:
    try:
        from .commands import COMMAND_HANDLERS
    except Exception:  # noqa: BLE001 - natural prompts should still work
        return set()
    return set(COMMAND_HANDLERS)


def _answer_natural_prompt(prompt: str, stdout: IO[str], context: ShellContext) -> None:
    normalized = prompt.lower()
    wants_project = any(token in normalized for token in ("project", "repo", "repository", "where am i", "what directory"))
    wants_model = "model" in normalized or "provider" in normalized

    if wants_project:
        print("You are in this project context:", file=stdout)
        print(f"  Project: {context.display_project}", file=stdout)
        print(f"  Branch: {context.display_branch}", file=stdout)
        print(f"  Working directory: {context.project_root}", file=stdout)
        return

    if wants_model:
        _print_model(stdout, context)
        return

    print("I can work from this local context:", file=stdout)
    print(f"  Project: {context.display_project}", file=stdout)
    print(f"  Branch: {context.display_branch}", file=stdout)
    print(f"  Model: {context.display_model}", file=stdout)
    print("Ask about the project, or use /help to inspect available controls.", file=stdout)


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

    shell_context = _detect_shell_context(project_path)
    _print_banner(out_stream, shell_context)

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

        if stripped in MODEL_TOKENS:
            _print_model(out_stream, shell_context)
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

        if not _looks_like_command(stripped, _known_command_names(main)):
            _answer_natural_prompt(stripped, out_stream, shell_context)
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
