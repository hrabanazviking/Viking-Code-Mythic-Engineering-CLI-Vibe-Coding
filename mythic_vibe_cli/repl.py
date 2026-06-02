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

from .config import ConfigStore
from .exit_codes import SUCCESS, USER_INPUT_ERROR
from .patch import PatchManager
from .runtime.slash_commands import BUILTIN_SLASH_COMMANDS


PROMPT = "mythic-vibe> "
BANNER = (
    "Mythic Vibe CLI — companion shell. Type naturally, or use /help."
)
QUIT_TOKENS = frozenset({"/quit", "/exit"})
HELP_TOKENS = frozenset({"/help", "/?"})
MODEL_TOKENS = frozenset({"/model"})
PATCH_TOKENS = frozenset({"/diff", "/apply", "/reject"})


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

    loaded_config = ConfigStore(root).load()
    model_provider = loaded_config.config.ai_provider or "copy-paste"
    model_name = loaded_config.config.ai_model or "manual"
    try:
        from .ai.registry import ProviderRegistry

        provider = ProviderRegistry(root=root).providers().get(model_provider)
        if provider is not None and model_name == "manual" and model_provider != "copy-paste":
            model_name = str(getattr(provider, "model", model_name) or model_name)
    except Exception:  # noqa: BLE001 - shell startup should degrade, not crash
        pass

    knowledge_status = "not connected"
    if (root / "mythic" / "project_index.json").exists():
        knowledge_status = "local project index present"
    try:
        from .knowledge.reader import knowledge_status as _knowledge_status

        statuses = _knowledge_status(root)
        configured = [status for status in statuses if status.configured]
        searchable = [status for status in statuses if status.searchable]
        if searchable:
            knowledge_status = f"{len(searchable)} private source(s) searchable"
        elif configured:
            knowledge_status = f"{len(configured)} private source(s) configured"
    except Exception:
        pass

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
    print("  Routing: selected provider with copy-paste fallback", file=stdout)


def _print_model_list(stdout: IO[str], context: ShellContext) -> None:
    print("Model providers", file=stdout)
    try:
        from .ai.registry import ProviderRegistry

        providers = ProviderRegistry(root=context.project_root).providers()
    except Exception as exc:  # noqa: BLE001 - listing should degrade, not crash
        print(f"  Provider registry unavailable: {exc}", file=stdout)
        return

    for name, provider in providers.items():
        try:
            status = provider.validate_config()
        except Exception as exc:  # noqa: BLE001
            configured = False
            details = [f"status check failed: {exc}"]
        else:
            configured = status.configured
            details = status.details
        model = str(getattr(provider, "model", "") or "")
        marker = " *" if name == context.model_provider else ""
        state = "configured" if configured else "not configured"
        print(f"  {name}{marker}: {state} ({model or 'default'})", file=stdout)
        for detail in details[:2]:
            print(f"    - {detail}", file=stdout)


def _set_model_selection(provider_name: str, model_name: str, context: ShellContext, stdout: IO[str], stderr: IO[str]) -> ShellContext:
    try:
        from .ai.registry import ProviderRegistry

        providers = ProviderRegistry(root=context.project_root).providers()
    except Exception as exc:  # noqa: BLE001
        print(f"Provider registry unavailable: {exc}", file=stderr)
        return context

    if provider_name not in providers:
        print(f"Unknown provider: {provider_name}", file=stderr)
        return context

    provider = providers[provider_name]
    resolved_model = model_name or str(getattr(provider, "model", "") or "")
    if not resolved_model:
        resolved_model = "manual" if provider_name == "copy-paste" else "default"

    try:
        path = ConfigStore(context.project_root).save_project_values(
            {
                "ai.provider": provider_name,
                "ai.model": resolved_model,
            }
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Could not save model selection: {exc}", file=stderr)
        return context

    print(f"Model set to {provider_name}/{resolved_model}", file=stdout)
    print(f"Saved: {path}", file=stdout)
    return _detect_shell_context(context.project_root)


def _handle_model_command(stripped: str, stdout: IO[str], stderr: IO[str], context: ShellContext) -> ShellContext:
    try:
        argv = shlex.split(stripped)
    except ValueError as exc:
        print(f"Parse error: {exc}", file=stderr)
        return context
    if not argv:
        return context

    if len(argv) == 1:
        _print_model(stdout, context)
        return context

    action = argv[1].lower()
    if action == "list":
        _print_model_list(stdout, context)
        return context
    if action == "set":
        if len(argv) < 3:
            print("Usage: /model set <provider> [model]", file=stderr)
            return context
        provider_name = argv[2]
        model_name = argv[3] if len(argv) > 3 else ""
        return _set_model_selection(provider_name, model_name, context, stdout, stderr)

    print("Usage: /model [list|set <provider> [model]]", file=stderr)
    return context


def _handle_patch_command(stripped: str, patch_manager: PatchManager, stdout: IO[str], stderr: IO[str]) -> None:
    action = stripped.lstrip("/")
    if action == "diff":
        print(patch_manager.get_diff(), file=stdout)
    elif action == "apply":
        if patch_manager.apply_active():
            print("Patch applied successfully.", file=stdout)
        else:
            print("No active patch to apply.", file=stderr)
    elif action == "reject":
        if patch_manager.reject_active():
            print("Patch rejected.", file=stdout)
        else:
            print("No active patch to reject.", file=stderr)


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
    wants_knowledge = "knowledge" in normalized and any(
        token in normalized for token in ("search", "find", "look up", "lookup", "earlier ideas", "ideas about")
    )
    wants_workspace = any(token in normalized for token in ("clone", "workspace", "github", "branch", "pull request", " pr "))
    wants_workspace = wants_workspace and any(token in normalized for token in ("clone", "branch", "workspace", "repo", "repository", "github"))
    wants_last_time = any(
        token in normalized
        for token in (
            "last time",
            "previous session",
            "what were we doing",
            "where did we leave off",
            "resume memory",
        )
    )
    wants_context_scan = any(token in normalized for token in ("find", "search", "inspect", "scan", "where is", "show me"))

    if wants_workspace:
        try:
            from .workspaces.manager import default_workspace_root, propose_workspace_plan

            rendered = propose_workspace_plan(prompt, workspace_root=default_workspace_root())
            print(rendered, file=stdout)
            _record_shell_memory(prompt, rendered, context, "workspace")
            return
        except Exception as exc:  # noqa: BLE001 - workspace planning should degrade, not crash
            print(f"Workspace planning failed: {exc}", file=stdout)
            return

    if wants_knowledge:
        try:
            from .knowledge.reader import render_search, search_knowledge

            query = _knowledge_query_from_prompt(prompt)
            result = search_knowledge(context.project_root, query, limit=5)
            rendered = render_search(result)
            print(rendered, file=stdout)
            _record_shell_memory(prompt, rendered, context, "knowledge")
            return
        except Exception as exc:  # noqa: BLE001 - private knowledge should degrade, not crash
            print(f"Knowledge search failed: {exc}", file=stdout)
            return

    if wants_last_time:
        try:
            from .memory.spine import render_last_time

            print(render_last_time(context.project_root), file=stdout)
            return
        except Exception as exc:  # noqa: BLE001 - memory recall should degrade, not crash
            print(f"Memory recall failed: {exc}", file=stdout)
            return

    if wants_context_scan:
        try:
            from .context.companion import build_companion_context, render_companion_context
            from .memory.spine import record_shell_exchange

            summary = build_companion_context(context.project_root, prompt)
            rendered = render_companion_context(summary)
            print(rendered, file=stdout)
            record_shell_exchange(
                context.project_root,
                prompt=prompt,
                response=rendered,
                provider=context.model_provider,
                model=context.model_name,
                context_kind="inspection",
            )
            return
        except Exception as exc:  # noqa: BLE001 - shell prompt handling should not crash
            print(f"Context scan failed: {exc}", file=stdout)
            return

    if wants_project:
        lines = [
            "You are in this project context:",
            f"  Project: {context.display_project}",
            f"  Branch: {context.display_branch}",
            f"  Working directory: {context.project_root}",
        ]
        print("\n".join(lines), file=stdout)
        _record_shell_memory(prompt, "\n".join(lines), context, "project")
        return

    if wants_model:
        lines = [
            "Model",
            f"  Provider: {context.model_provider}",
            f"  Model: {context.model_name}",
            "  Routing: selected provider with copy-paste fallback",
        ]
        print("\n".join(lines), file=stdout)
        _record_shell_memory(prompt, "\n".join(lines), context, "model")
        return

    context_lines = [
        "I can work from this local context:",
        f"  Project: {context.display_project}",
        f"  Branch: {context.display_branch}",
        f"  Model: {context.display_model}",
    ]
    print("\n".join(context_lines), file=stdout)
    model_response = _answer_with_selected_model(prompt, stdout, context)
    response_text = "\n".join([*context_lines, model_response]).strip()
    _record_shell_memory(prompt, response_text, context, "conversation")


def _knowledge_query_from_prompt(prompt: str) -> str:
    text = prompt.strip()
    lowered = text.lower()
    markers = (
        "knowledge database for",
        "knowledge base for",
        "knowledge for",
        "knowledge search",
        "search my knowledge database for",
        "search knowledge for",
    )
    for marker in markers:
        index = lowered.find(marker)
        if index >= 0:
            return text[index + len(marker):].strip(" .:?") or text
    return text


def _record_shell_memory(prompt: str, response: str, context: ShellContext, context_kind: str) -> None:
    try:
        from .memory.spine import record_shell_exchange

        record_shell_exchange(
            context.project_root,
            prompt=prompt,
            response=response,
            provider=context.model_provider,
            model=context.model_name,
            context_kind=context_kind,
        )
    except Exception:
        return


def _answer_with_selected_model(prompt: str, stdout: IO[str], context: ShellContext) -> str:
    packet = {
        "text": prompt,
        "packet_id": "shell",
        "source": "companion-shell",
    }
    try:
        from .ai.router import RouteDecision
        from .ai.routing_runtime import run_with_fallback
        from .ai.registry import ProviderRegistry

        providers = ProviderRegistry(root=context.project_root).providers()
        selected = providers.get(context.model_provider)
        if selected is not None and hasattr(selected, "model"):
            setattr(selected, "model", context.model_name)

        result = run_with_fallback(
            RouteDecision(
                provider=context.model_provider,
                model=context.model_name,
                rule_matched=None,
                fallbacks=("copy-paste",),
                role="Companion Shell",
                task_type="conversation",
            ),
            packet,
            resolver=lambda name: providers.get(name),
            root=context.project_root,
            dry_run=False,
        )
    except Exception as exc:  # noqa: BLE001
        rendered = f"Model call failed: {exc}"
        print(rendered, file=stdout)
        return rendered

    response = result.response
    lines: list[str] = []
    if result.fell_back:
        lines.append(f"  Fallback: {result.primary_provider} -> {result.used_provider}")
    if response.provider == "copy-paste":
        lines.append("  Provider-ready prompt:")
    else:
        lines.append(f"  Response from {response.provider}/{response.model}:")
    lines.append(response.content)
    rendered = "\n".join(lines)
    print(rendered, file=stdout)
    return rendered


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
    patch_manager = PatchManager()
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

        if stripped in MODEL_TOKENS or stripped.startswith("/model "):
            shell_context = _handle_model_command(stripped, out_stream, err_stream, shell_context)
            continue

        if stripped in PATCH_TOKENS:
            _handle_patch_command(stripped, patch_manager, out_stream, err_stream)
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
