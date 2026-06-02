# Product Intent

**Status:** Active product-intent record for the reforge roadmap
**Created:** 2026-06-02
**Roadmap:** `../Mythic_Vibe_CLI_Reforge_Roadmap.md`
**Scope:** User-facing product direction for `mythic` and `mythic-vibe`

This document states what Mythic is being reforged into. It is the first reference to read before changing entrypoints, shell behavior, slash commands, model routing, memory, knowledge lookup, patching, testing, GitHub workflow support, or the TUI.

## 1. What Mythic Is

Mythic is a terminal-based coding companion CLI.

The primary experience should be:

```bash
mythic
```

Then the user talks naturally to the model.

The companion shell should inspect the current repository, gather context, read memory, search configured knowledge sources, propose a plan, suggest patches, request approval when actions are risky or persistent, apply approved edits, run tests, and remember what happened.

Mythic should feel closer to a coding partner shell than a command catalog. A user should be able to say:

> Fix the memory holes in this repo and write tests for the fix.

The product should then do the internal tool work needed to support that request.

## 2. What Mythic Is Not

Mythic is not primarily a DevOps-style subcommand toolkit.

Commands such as these may remain available:

```bash
mythic packet create
mythic workflow run
mythic knowledge search
mythic branch create
mythic reflect
mythic patch apply
```

They are not the main user experience. If ordinary coding work requires the user to memorize a large command catalog, the product direction has failed.

## 3. Primary Entrypoint

The corrected default is:

```bash
mythic
```

Default invocation should open the interactive coding companion shell.

The startup view should quickly identify:

- current project or repository
- current Git branch when available
- configured model or fallback mode
- memory availability
- knowledge availability

The user should then type normal requests in natural language.

## 4. Slash Commands

Slash commands are secondary controls inside the companion shell.

They should exist for direct control, inspection, or escape hatches, not as the primary workflow. The expected control set begins with:

| Command | Purpose |
|---|---|
| `/help` | Show shell help |
| `/status` | Show current project and system status |
| `/model` | Show or manage the active model |
| `/context` | Inspect current context |
| `/memory` | Query or update local project memory |
| `/knowledge` | Trigger private knowledge retrieval |
| `/files` | Inspect or adjust tracked files |
| `/diff` | View proposed modifications |
| `/apply` | Apply an approved patch |
| `/reject` | Reject the current patch proposal |
| `/test` | Run or inspect test commands |
| `/branch` | Manage Git branches with approval gates |
| `/commit` | Commit approved changes |
| `/pr` | Draft a pull request |
| `/tui` | Open the terminal UI |
| `/exit` | Close the shell cleanly |

## 5. Preservation Rule

Existing coded features must not be deleted casually.

Older commands, workflow tools, packet builders, patch helpers, Git helpers, doctor checks, memory surfaces, knowledge surfaces, provider code, and TUI code should be preserved and turned into internal tools behind the companion shell where possible.

If a feature is not part of the first working companion shell, it may be hidden from the default path, documented as advanced/admin behavior, or left dormant until integrated. It should not be removed merely because the default UX changed.

## 6. Internal Tool Direction

The old command-catalog pieces become machinery the shell can call:

| Existing system | New role |
|---|---|
| Packet commands | Context and prompt builder |
| Workflow commands | Planning engine |
| Reflect commands | Session memory recorder |
| Knowledge commands | Retrieval tool |
| Branch commands | Git tool with approval |
| Patch commands | Edit proposal and approval system |
| Doctor commands | Health check |
| Status commands | Project state reader |
| TUI | Visual cockpit for the companion workflow |

## 7. Phase Alignment

The reforge roadmap starts with these gates:

1. Phase 0: make product intent unambiguous.
2. Phase 1: make `mythic` launch the companion shell by default.
3. Phase 2: provide the minimal useful shell loop.
4. Phase 3: build automatic repository context.

Later phases should continue in roadmap order and update this product-intent record if the corrected product definition changes.

## 8. Success Criteria

Phase 0 is complete when a future coding agent can read the repository and understand these truths without guessing:

- Mythic is being reforged into a coding companion CLI.
- `mythic` is the primary entrypoint.
- Natural language conversation is the main interaction.
- Slash commands are support controls.
- Existing command code is preserved as internal machinery where useful.
- The roadmap in `../Mythic_Vibe_CLI_Reforge_Roadmap.md` governs the phase order.
