import os

base_dir = "/home/volmarr/.gemini/antigravity/scratch/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/docs"

files = {
    "INTERACTIVE_SHELL.md": """# Interactive Shell

Mythic operates as an interactive terminal-based coding companion. The primary interface is the interactive shell.

## Starting the Shell

To start the interactive shell, simply run:
```bash
mythic
```

## The Conversation Loop

Once the shell is active, it begins a continuous conversation loop:
1. **Input:** You type natural language requests, questions, or instructions.
2. **Context:** Mythic quietly inspects your current repository, reads tracked files, checks git branch status, and looks up relevant project memory.
3. **Reasoning:** Mythic processes your request along with the gathered context to formulate a plan or a code patch.
4. **Action:** Mythic may propose file modifications, run tests, create branches, or summarize knowledge. For sensitive or persistent actions, it will ask for your approval.
5. **Memory:** The interaction and resulting changes are written to local project memory (`.mythic/memory.sqlite`) so Mythic can recall this session later.

The companion shell acts as your pair programmer, minimizing the need to manually invoke dozens of complex CLI subcommands.
""",
    "SLASH_COMMANDS.md": """# Slash Commands

While natural language is the primary interaction mode in the interactive shell, **slash commands** provide explicit secondary controls. They act as shortcuts, overrides, or escape hatches when you need to force a specific behavior.

## Core Slash Commands

| Command | Purpose |
|---|---|
| `/help` | Display the shell help menu and list of available slash commands. |
| `/status` | View the current project directory, git branch, and system status. |
| `/model` | Inspect or change the active LLM provider and model (`/model set <provider>`). |
| `/context` | Inspect the context (files, summaries) Mythic has built for the current prompt. |
| `/memory` | Query the local memory spine or manually record a fact. |
| `/knowledge` | Trigger a search against private knowledge SQLite databases. |
| `/files` | Inspect which files are currently loaded into context. |
| `/diff` | View proposed file modifications (patches) before they are applied. |
| `/apply` | Approve and apply the currently staged patch. |
| `/reject` | Reject the currently staged patch. |
| `/test` | Run the project test suite or inspect recent test failures. |
| `/branch` | Manage Git branches safely through the shell. |
| `/commit` | Commit approved changes with an auto-generated semantic message. |
| `/pr` | Draft a pull request based on current branch changes. |
| `/tui` | Launch the visual Cockpit Terminal UI (Textual interface). |
| `/exit` | Cleanly close the interactive shell. |

Use slash commands when you know exactly what you want Mythic to do, without needing natural language parsing.
""",
    "INTERNAL_TOOLS.md": """# Internal Tools

Mythic began as a complex subcommand-based CLI tool. As it evolved into an interactive coding companion, these legacy commands were preserved and repurposed as **internal tools**.

## Legacy Commands as Machinery

The companion shell is powered by the same battle-tested code that drove the original `mythic` commands. When you ask the interactive shell to "Find the memory subsystem," it translates your intent into an execution of the `mythic scan` machinery.

The old command catalog has been shifted to the `admin` namespace to keep the default `mythic --help` clean and focused on the interactive shell workflow.

## The `admin` Namespace

If you prefer to run legacy commands manually, or need them for CI/CD scripting, they are fully accessible by prefixing them with `admin`:

```bash
mythic admin scan .
mythic admin packet create
mythic admin workflow run .mythic/workflows/deploy.yml
mythic admin patch apply staged.patch
mythic admin reflect
```

By design, **no code was casually deleted** during the transition to an interactive shell. The raw primitives remain available for those who need them, while the typical user interacts safely through the conversation loop.
""",
    "MEMORY.md": """# Project Memory

Mythic utilizes a local SQLite database to maintain a persistent **Memory Spine** across all of your interactive sessions.

## The Memory Spine

Located by default at `.mythic/memory.sqlite` in your project root, the memory spine records:
- **Session Summaries:** What was accomplished during an interaction.
- **Decisions:** Architectural choices and why they were made.
- **File Edits:** Which files were modified and the nature of the changes.
- **Failures & Fixes:** Bugs encountered and how they were patched.

## Utilizing Memory

The interactive shell automatically queries the memory spine. You can simply ask:
> "What were we doing last time?"

Mythic will retrieve the most recent session summaries and re-orient itself (and you) to the task at hand.

You can also use slash commands to interact with memory directly:
- `/memory` queries the spine.
- `mythic admin memory spine` allows raw inspection.
""",
    "KNOWLEDGE.md": """# Private Knowledge

Mythic can read from external, read-only private knowledge sources to supplement its understanding of your domain.

## SQLite Knowledge Sources

You can configure Mythic to search pre-compiled SQLite databases. This is useful for proprietary API documentation, internal engineering guidelines, or massive research compendiums.

## Configuration

Set the `MYTHIC_KNOWLEDGE_SQLITE_PATH` environment variable or define `knowledge.sources` in your project configuration.

## Searching Knowledge

In the interactive shell, you can request knowledge lookups naturally:
> "Search my knowledge database for guidelines on Hermes memory."

Mythic will parse the query, retrieve matching excerpts from the SQLite database, and inject them into the active LLM context before answering your question.

For manual inspection, use:
- `/knowledge` in the interactive shell.
- `mythic admin knowledge search <query>` via the command line.
""",
    "GITHUB_WORKSPACE.md": """# GitHub Workspace Manager

Mythic includes an integrated workspace manager for handling repositories, branching, and pull requests directly from the interactive shell.

## Workspace Root

By default, workspaces are managed under `~/.mythic-vibe/workspaces/` (overridable via `MYTHIC_WORKSPACE_ROOT`).

## Safe Git Operations

The shell leverages this manager to propose Git actions safely:
- **Dry-Run by Default:** Actions like branching and cloning are planned but not executed until explicitly confirmed.
- **Conversational Git:** You can say *"Commit this and make a PR"*. Mythic will stage the changes, draft an auto-generated semantic commit message and PR description, and ask for your approval before writing to the local Git state or communicating with GitHub.

## Slash Commands

You can trigger workspace actions via the `/branch`, `/commit`, and `/pr` slash commands.

Manual legacy commands remain available via `mythic admin workspace`.
""",
    "TUI.md": """# Terminal UI (CockpitScreen)

For users who prefer a structured, visual interface over a scrolling REPL, Mythic provides a Textual-based **Terminal UI (TUI)** known as the Cockpit.

## Launching the TUI

You can enter the TUI directly from the interactive shell by typing:
```bash
/tui
```

## TUI Layout

The Cockpit is a tabbed interface offering several distinct views of your project and session state:
- **Chat:** The primary conversation view, bridging the standard REPL loop into a visual chat window using asynchronous worker threads.
- **Files:** A tree view of the files currently tracked or loaded in context.
- **Diff:** A dedicated visual review screen for staging and approving patch proposals.
- **Memory:** A timeline of the SQLite memory spine.
- **Knowledge:** Status and search interface for attached private knowledge sources.
- **Tasks:** An overview of active workflows or tasks.
- **Model:** Status of the active LLM provider, token usage, and connection health.

The TUI provides a dashboard experience while retaining the core natural language workflow.
""",
    "DAILY_WORKFLOW.md": """# Daily Workflow

This document outlines a standard daily workflow using the Mythic interactive companion shell.

## 1. Start the Day

Navigate to your project repository and launch Mythic:
```bash
mythic
```
You will be greeted with a status banner confirming your branch, LLM provider, and active memory store.

## 2. Re-orient

Ask Mythic to recall your previous session:
> "What were we working on yesterday?"

Mythic will read the `.mythic/memory.sqlite` spine and summarize the last known state, failures, and pending next steps.

## 3. Discuss the Task

Explain what you want to achieve:
> "Let's fix the bug in the authentication module where tokens expire prematurely."

Mythic will inspect the repo, locate the authentication module, and load it into context.

## 4. Review and Apply Patches

Mythic will propose a patch to fix the issue. You can review the changes:
```bash
/diff
```
If the code looks correct, approve and apply it:
```bash
/apply
```

## 5. Verify

Run the test suite through Mythic:
```bash
/test
```
If tests fail, Mythic will automatically ingest the failure output and propose a subsequent fix.

## 6. Commit and Reflect

Once satisfied, ask Mythic to commit:
> "Commit these changes."

Mythic will draft a semantic commit message, request approval, and execute the commit. The session details and decisions will be written back to the memory spine, ready for tomorrow.
"""
}

for filename, content in files.items():
    with open(os.path.join(base_dir, filename), "w") as f:
        f.write(content.strip() + "\\n")
print("Files created.")
