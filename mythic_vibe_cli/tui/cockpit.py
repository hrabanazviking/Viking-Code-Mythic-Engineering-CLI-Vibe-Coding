from __future__ import annotations

import io
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Header,
    Footer,
    TabbedContent,
    TabPane,
    Input,
    RichLog,
    DirectoryTree,
    Markdown,
    Static,
)
from textual import work

from ..patch import PatchManager
from ..runtime.exec import exec_command
from ..repl import (
    _detect_shell_context,
    _answer_natural_prompt,
    _answer_with_selected_model,
    _record_shell_memory,
)


class CockpitScreen(Screen):
    """The unified cockpit for the Mythic Vibe CLI companion shell."""

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+c", "quit", "Quit"),
    ]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root = root
        self.context = _detect_shell_context(self.root)

        # UI Components
        self.chat_log = RichLog(id="chat_log", wrap=True, markup=True)
        self.chat_input = Input(placeholder="Ask Mythic a question or give a command...", id="chat_input")
        self.file_tree = DirectoryTree(str(self.root), id="file_tree")
        self.diff_view = Static(id="diff_view", markup=True)
        self.memory_view = Static(id="memory_view", markup=True)
        self.knowledge_view = Static(id="knowledge_view", markup=True)
        self.git_view = Static(id="git_view", markup=True)
        self.tasks_view = Markdown(id="tasks_view")
        self.model_view = Static(id="model_view", markup=True)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="chat"):
            with TabPane("Chat", id="chat"):
                with Vertical():
                    yield self.chat_log
                    yield self.chat_input
            with TabPane("Files", id="files"):
                yield self.file_tree
            with TabPane("Diff", id="diff"):
                yield self.diff_view
            with TabPane("Memory", id="memory"):
                yield self.memory_view
            with TabPane("Knowledge", id="knowledge"):
                yield self.knowledge_view
            with TabPane("Git Status", id="git"):
                yield self.git_view
            with TabPane("Tasks", id="tasks"):
                yield self.tasks_view
            with TabPane("Model Status", id="model"):
                yield self.model_view
        yield Footer()

    def on_mount(self) -> None:
        self.chat_log.write(f"[b]Mythic Vibe CLI[/b] — companion shell.")
        self.chat_log.write(f"Project: {self.context.display_project}")
        self.chat_log.write(f"Branch: {self.context.display_branch}")
        self.chat_log.write(f"Model: {self.context.display_model}")
        self.chat_log.write(f"Knowledge: {self.context.knowledge_status}")
        self.chat_log.write(f"Memory: {self.context.memory_status}")
        self.chat_log.write("---")
        
        self.chat_input.focus()
        self._refresh_panels()

    def _refresh_panels(self) -> None:
        # Refresh Diff
        diff_text = PatchManager().get_diff()
        if not diff_text.strip():
            diff_text = "No active patch proposed."
        self.diff_view.update(f"```diff\n{diff_text}\n```")

        # Refresh Memory Status
        self.memory_view.update(f"Memory Status: {self.context.memory_status}")

        # Refresh Knowledge
        self.knowledge_view.update(f"Knowledge Status: {self.context.knowledge_status}")

        # Refresh Git Status
        res = exec_command("git", ["status"], self.root, timeout=5.0)
        if res.code == 0:
            self.git_view.update(res.stdout)
        else:
            self.git_view.update(f"Git status failed: {res.stderr or res.stdout}")

        # Refresh Tasks
        tasks_file = self.root / "tasks" / "current_GOALS.md"
        if tasks_file.exists():
            self.tasks_view.update(tasks_file.read_text())
        else:
            self.tasks_view.update("No current goals found at tasks/current_GOALS.md")

        # Refresh Model Status
        self.model_view.update(
            f"Provider: {self.context.model_provider}\nModel: {self.context.model_name}"
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return

        self.chat_input.value = ""
        self.chat_log.write(f"[b]You:[/b] {prompt}")
        
        # We need to dispatch to the model async so UI doesn't block
        self.dispatch_prompt(prompt)

    @work(exclusive=True, thread=True)
    def dispatch_prompt(self, prompt: str) -> None:
        """Run the AI prompt generation in a background thread."""
        try:
            # We create a string IO buffer to capture print output from the repl helpers
            buffer = io.StringIO()
            
            normalized = prompt.lower()
            wants_workspace = any(token in normalized for token in ("clone", "workspace", "github", "branch", "pull request", " pr ")) and any(token in normalized for token in ("clone", "branch", "workspace", "repo", "repository", "github"))
            wants_knowledge = "knowledge" in normalized and any(token in normalized for token in ("search", "find", "look up", "lookup", "earlier ideas", "ideas about"))
            wants_last_time = any(token in normalized for token in ("last time", "previous session", "what were we doing", "where did we leave off", "resume memory"))
            wants_context_scan = any(token in normalized for token in ("find", "search", "inspect", "scan", "where is", "show me"))
            wants_project = any(token in normalized for token in ("project", "repo", "repository", "where am i", "what directory"))
            wants_model = "model" in normalized or "provider" in normalized

            # We reuse the logic from repl.py
            if wants_workspace or wants_knowledge or wants_last_time or wants_context_scan or wants_project or wants_model:
                _answer_natural_prompt(prompt, buffer, self.context)
            else:
                context_lines = [
                    "I can work from this local context:",
                    f"  Project: {self.context.display_project}",
                    f"  Branch: {self.context.display_branch}",
                    f"  Model: {self.context.display_model}",
                ]
                print("\\n".join(context_lines), file=buffer)
                model_response = _answer_with_selected_model(prompt, buffer, self.context)
                response_text = "\\n".join([*context_lines, model_response]).strip()
                _record_shell_memory(prompt, response_text, self.context, "conversation")
            
            output = buffer.getvalue()
            # Push output back to UI thread
            self.app.call_from_thread(self._append_to_log, output)
            self.app.call_from_thread(self._refresh_panels)
            
        except Exception as e:
            self.app.call_from_thread(self._append_to_log, f"[red]Error:[/red] {e}")

    def _append_to_log(self, text: str) -> None:
        self.chat_log.write(text)
