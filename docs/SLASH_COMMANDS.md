# Slash Commands

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

Use slash commands when you know exactly what you want Mythic to do, without needing natural language parsing.\n