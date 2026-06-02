# GitHub Workspace Manager

Mythic includes an integrated workspace manager for handling repositories, branching, and pull requests directly from the interactive shell.

## Workspace Root

By default, workspaces are managed under `~/.mythic-vibe/workspaces/` (overridable via `MYTHIC_WORKSPACE_ROOT`).

## Safe Git Operations

The shell leverages this manager to propose Git actions safely:
- **Dry-Run by Default:** Actions like branching and cloning are planned but not executed until explicitly confirmed.
- **Conversational Git:** You can say *"Commit this and make a PR"*. Mythic will stage the changes, draft an auto-generated semantic commit message and PR description, and ask for your approval before writing to the local Git state or communicating with GitHub.

## Slash Commands

You can trigger workspace actions via the `/branch`, `/commit`, and `/pr` slash commands.

Manual legacy commands remain available via `mythic admin workspace`.\n