# OpenAI Codex CLI Plundering Guide

## Purpose

This guide explains how to lawfully and strategically reuse, study, adapt, or “plunder” parts of **OpenAI Codex CLI** for your own Apache-2.0 CLI project.

Codex CLI is OpenAI’s local terminal coding agent. The official README describes it as a coding agent that runs locally on your computer, installable through `npm`, Homebrew, or platform-specific GitHub releases. ([GitHub][1])

This guide is practical open-source hygiene, not legal advice.

---

# 1. Core Legal Position

## License Match

OpenAI Codex CLI is licensed under **Apache License 2.0**. ([GitHub][1])

That means you can generally:

* Copy code.
* Modify code.
* Merge code into your own project.
* Redistribute modified versions.
* Use it commercially.
* Build your own Apache-2.0 project from adapted pieces.

Apache-2.0 allows redistribution of the work or derivative works in source or object form, with or without modifications, as long as the license conditions are followed. ([GitHub][2])

In plain Viking terms:

> Take the steel.
> Keep the maker’s mark.
> Forge your own blade.

---

# 2. Required Source Links

Use these as the canonical references when documenting your work.

## Main Project Links

* **OpenAI Codex GitHub Repo** — main source repository for Codex CLI. ([GitHub][1])
* **README** — install notes, quickstart, and official description. ([GitHub][1])
* **LICENSE** — Apache-2.0 license terms. ([GitHub][2])
* **NOTICE** — required attribution file. ([GitHub][3])
* **AGENTS.md** — repo-specific agent instructions and development guidance. ([GitHub][4])

## Official Documentation Links

* **Codex Configuration Reference** — full `config.toml` and `requirements.toml` reference. ([OpenAI Developers][5])
* **Codex CLI Command Reference** — command-line flags, options, and command behavior. ([OpenAI Developers][6])
* **Codex MCP Documentation** — how Codex connects to MCP servers. ([OpenAI Developers][7])
* **Codex Sandboxing Documentation** — how Codex constrains commands and file access. ([OpenAI Developers][8])
* **Codex Repo Config Docs** — repo-local config notes, MCP notes, notification hooks, JSON schema, SQLite state DB, and custom CA certificate notes. ([GitHub][9])

## Important Source Directories

* **`codex-rs/`** — maintained Rust implementation and core CLI architecture. ([GitHub][10])
* **`codex-cli/`** — npm wrapper / install packaging layer. ([GitHub][11])
* **`sdk/`** — SDK material, currently including Python runtime, Python, and TypeScript folders. ([GitHub][12])

---

# 3. Required Attribution Rules

## 3.1 Keep Apache-2.0 License

Your project should include:

```text
LICENSE
```

The file should contain the Apache License 2.0 text.

Apache-2.0 requires that recipients of redistributed work or derivative works receive a copy of the license. ([GitHub][2])

---

## 3.2 Mark Modified Files

Apache-2.0 requires modified files to carry prominent notices stating that you changed them. ([GitHub][2])

Use headers like this.

### Rust

```rust
// Portions adapted from OpenAI Codex CLI.
// Original work Copyright 2025 OpenAI.
// Modified by Volmarr / RuneForgeAI, 2026.
// Licensed under the Apache License, Version 2.0.
```

### Python

```python
# Portions adapted from OpenAI Codex CLI.
# Original work Copyright 2025 OpenAI.
# Modified by Volmarr / RuneForgeAI, 2026.
# Licensed under the Apache License, Version 2.0.
```

### TypeScript

```ts
// Portions adapted from OpenAI Codex CLI.
// Original work Copyright 2025 OpenAI.
// Modified by Volmarr / RuneForgeAI, 2026.
// Licensed under the Apache License, Version 2.0.
```

### Markdown

```md
<!--
Portions adapted from OpenAI Codex CLI.
Original work Copyright 2025 OpenAI.
Modified by Volmarr / RuneForgeAI, 2026.
Licensed under the Apache License, Version 2.0.
-->
```

---

## 3.3 Preserve the NOTICE File Attribution

OpenAI Codex has a `NOTICE` file. It identifies:

```text
OpenAI Codex
Copyright 2025 OpenAI
```

It also says the project includes code derived from **Ratatui** under MIT and parser assets from **Meriyah** under ISC. ([GitHub][3])

Your project should include a readable NOTICE attribution when you distribute derivative work using copied or adapted Codex material.

Suggested `NOTICE` template:

```md
# NOTICE

[Your CLI Project Name]

Copyright 2026 Volmarr / RuneForgeAI

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts portions of software from:

## OpenAI Codex CLI

OpenAI Codex  
Copyright 2025 OpenAI

Licensed under the Apache License, Version 2.0.

Original project: openai/codex

The upstream OpenAI Codex NOTICE file also identifies derived or included components from:

## Ratatui

Licensed under the MIT License.

Copyright (c) 2016-2022 Florian Dehau  
Copyright (c) 2023-2025 The Ratatui Developers

## Meriyah

Licensed under the ISC License.

Copyright (c) 2019 and later, KFlash and others.
```

---

# 4. Branding Warning

Apache-2.0 lets you reuse code, but it does **not** give you ownership of OpenAI’s name, Codex branding, logos, service marks, or product identity.

Safe wording:

```md
This project includes code adapted from OpenAI Codex CLI.
```

Unsafe wording:

```md
This is the official OpenAI Codex CLI.
```

Avoid naming your tool things like:

* OpenAI Codex Fork
* Official Codex
* Codex Pro
* OpenAI CLI
* ChatGPT Codex Engine

Unless the wording is clearly just attribution and not branding.

---

# 5. What Is Most Worth Plundering

## 5.1 `codex-rs/` — Main Rust CLI Architecture

This is the richest target.

The repo identifies the Rust implementation as the maintained Codex CLI and the default experience. It also notes that the Rust CLI includes features the legacy TypeScript CLI did not support. ([GitHub][10])

Likely interesting areas:

| Path / Area                    | Why It Is Worth Studying                                            |
| ------------------------------ | ------------------------------------------------------------------- |
| `codex-rs/cli`                 | Main CLI command structure and argument routing.                    |
| `codex-rs/core`                | Core agent loop and task orchestration.                             |
| `codex-rs/tui`                 | Terminal UI patterns, interaction design, keyboard-driven workflow. |
| `codex-rs/protocol`            | Message/event protocol between agent, UI, tools, and services.      |
| `codex-rs/tools`               | Tool invocation structure.                                          |
| `codex-rs/exec`                | Command execution logic.                                            |
| `codex-rs/execpolicy`          | Execution permission model.                                         |
| `codex-rs/shell-command`       | Shell command handling.                                             |
| `codex-rs/shell-escalation`    | Escalation flow when commands need higher permission.               |
| `codex-rs/sandboxing`          | General sandbox boundary abstraction.                               |
| `codex-rs/linux-sandbox`       | Linux sandbox implementation ideas.                                 |
| `codex-rs/windows-sandbox-rs`  | Windows sandbox implementation ideas.                               |
| `codex-rs/apply-patch`         | Patch application logic.                                            |
| `codex-rs/git-utils`           | Git-aware helper logic.                                             |
| `codex-rs/file-search`         | Repo search and file discovery patterns.                            |
| `codex-rs/thread-store`        | Conversation/thread storage design.                                 |
| `codex-rs/state`               | State persistence model.                                            |
| `codex-rs/model-provider`      | Provider abstraction.                                               |
| `codex-rs/model-provider-info` | Model metadata / provider configuration.                            |
| `codex-rs/models-manager`      | Model management patterns.                                          |
| `codex-rs/codex-mcp`           | MCP client integration.                                             |
| `codex-rs/mcp-server`          | Exposing Codex itself as an MCP server.                             |
| `codex-rs/config`              | Config parsing and layering.                                        |
| `codex-rs/features`            | Feature flag structure.                                             |
| `codex-rs/secrets`             | Secret handling patterns.                                           |
| `codex-rs/keyring-store`       | Credential storage strategy.                                        |
| `codex-rs/hooks`               | Hook system for notifications and lifecycle events.                 |
| `codex-rs/skills`              | Skill system architecture.                                          |
| `codex-rs/core-skills`         | Built-in skill implementation patterns.                             |
| `codex-rs/agent-identity`      | Agent identity and role structure.                                  |
| `codex-rs/rollout`             | Session rollout / persistence patterns.                             |
| `codex-rs/rollout-trace`       | Debug trace patterns.                                               |
| `codex-rs/otel`                | Telemetry architecture.                                             |
| `codex-rs/process-hardening`   | Process safety and hardening ideas.                                 |

The `codex-rs` folder list shows a large modular Rust architecture with separate crates or modules for CLI, TUI, config, MCP, sandboxing, shell handling, tools, state, skills, model providers, and more. ([GitHub][10])

---

## 5.2 Sandboxing and Approvals

This is one of the best parts to study.

Codex docs explain that the sandbox is the boundary that lets Codex act autonomously without unrestricted access to the machine. Commands run in a constrained environment by default, and Codex falls back to approval flow when it needs to exceed those boundaries. ([OpenAI Developers][8])

Plunder-worthy concepts:

* Workspace write boundaries.
* Approval policy separation from sandbox policy.
* Low-risk autonomous command execution.
* Human approval only for boundary-crossing actions.
* Platform-native sandbox design.
* Command inheritance of sandbox rules.
* “YOLO mode” only for hardened external environments.

Possible design adaptation for your CLI:

```md
## Permission Model

The CLI separates two concerns:

1. **Sandbox Boundary**
   - What the agent is technically allowed to touch.

2. **Approval Policy**
   - When the agent must ask the human before acting.

Routine work should proceed freely inside the approved workspace.
Boundary-crossing work should require explicit approval.
```

---

## 5.3 CLI Flags and Command UX

Codex has a detailed command-line reference. It documents global flags such as `--add-dir`, `--ask-for-approval`, `--cd`, `--config`, and `--dangerously-bypass-approvals-and-sandbox`. ([OpenAI Developers][6])

Worth studying:

* `--cd` working directory control.
* `--config key=value` overrides.
* Approval-policy CLI options.
* Sandboxing override design.
* Safe names for dangerous flags.
* Non-interactive execution modes.
* Separation between defaults and one-off overrides.

Your own CLI could adapt this pattern:

```bash
mythic-cli --cd ./repo "fix failing tests"
mythic-cli --profile architect "review architecture boundaries"
mythic-cli --ask-for-approval on-request "refactor this module"
mythic-cli exec "summarize this codebase"
```

---

## 5.4 `config.toml` System

Codex uses `~/.codex/config.toml` for user-level configuration and supports project-scoped `.codex/config.toml` files for trusted projects. ([OpenAI Developers][5])

This is very plunder-worthy.

Useful ideas:

* User-level config.
* Project-level config.
* Trust-gated project config.
* Profiles.
* Role-specific agent config.
* Sandbox and approval config.
* MCP server config.
* Model-provider config.
* Notification hook config.
* SQLite location config.
* Enterprise proxy / CA certificate config.

Potential adaptation:

```toml
# ~/.mythic-cli/config.toml

default_profile = "balanced"

[profiles.architect]
model = "gpt-5.5-thinking"
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[profiles.forge_worker]
model = "qwen3.5-coder"
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[agents.architect]
description = "Defines boundaries, ownership, and long-range structure."
config_file = "agents/architect.toml"

[agents.auditor]
description = "Finds defects, inconsistencies, and unsafe changes."
config_file = "agents/auditor.toml"
```

---

## 5.5 MCP Support

Codex supports MCP servers through `config.toml`. The docs say it supports local STDIO servers and streamable HTTP servers, including bearer token auth and OAuth for supported servers. ([OpenAI Developers][7])

Plunder-worthy concepts:

* `codex mcp add`
* `codex mcp login`
* `/mcp` TUI command
* Shared config between CLI and IDE extension
* STDIO MCP servers
* HTTP MCP servers
* OAuth callback flow
* Per-tool approval modes
* Parallel tool call safety flags

Useful adaptation for your Mythic CLI:

```toml
[mcp_servers.docs]
command = "docs-server"
default_tools_approval_mode = "prompt"

[mcp_servers.github]
url = "https://example.com/mcp/github"
bearer_token_env_var = "GITHUB_TOKEN"

[mcp_servers.local_knowledge]
command = "python"
args = ["-m", "mythic_knowledge_mcp"]
supports_parallel_tool_calls = true
```

Design principle to steal:

> MCP tools should not all have the same trust level. Some can be auto-approved. Some should prompt. Some should be forbidden unless explicitly enabled.

---

## 5.6 `codex exec` Pattern

The Rust README says `codex exec PROMPT` runs Codex non-interactively and can accept input from stdin; it also supports an ephemeral mode to avoid persisting session rollout files. ([GitHub][10])

Very useful for your project.

Plunder-worthy ideas:

* Interactive TUI mode.
* Non-interactive automation mode.
* `stdin` ingestion.
* Ephemeral no-persistence mode.
* Direct terminal output.
* Scriptable agent execution.

Possible adaptation:

```bash
mythic exec "audit this repo for architectural drift"

cat error.log | mythic exec "explain this failure and suggest the smallest safe fix"

mythic exec --ephemeral "summarize this repository without saving session memory"
```

---

## 5.7 `AGENTS.md` Development Instructions

Codex itself uses `AGENTS.md` to guide repo-specific agent behavior. The file includes concrete development instructions for the Rust codebase, including crate naming conventions, formatting expectations, and sandbox-related warnings. ([GitHub][4])

This is directly aligned with your Mythic Engineering style.

Plunder-worthy ideas:

* Repo-local agent law.
* Style rules.
* Test rules.
* Safety constraints.
* “Never modify this unless you know why” warnings.
* Tooling assumptions.
* Development environment notes.
* Subdirectory-specific instructions.

For your own repo, this maps beautifully to:

```text
AGENTS.md
DOMAIN_MAP.md
ARCHITECTURE.md
INTERFACE.md
GOALS.md
MYTHIC_ENGINEERING.md
```

Suggested pattern:

```md
# AGENTS.md

## Global Law

All agents must preserve architectural boundaries, obey DOMAIN_MAP.md, and update relevant README.md / INTERFACE.md files when changing public behavior.

## Architect

Owns boundaries, module ownership, refactor plans, and architectural drift detection.

## Forge Worker

Owns implementation, test execution, and small safe patches.

## Auditor

Owns defect detection, regression risk, and consistency checks.

## Scribe

Owns documentation, changelog notes, and preservation of design decisions.
```

---

## 5.8 Skills System

The repo has `.codex/skills`, `codex-rs/skills`, and `codex-rs/core-skills` areas visible in the repository structure. ([GitHub][1])

This is especially relevant to your work because your Mythic Engineering ecosystem already thinks in reusable skill packets.

Worth studying:

* How skills are discovered.
* How skills are represented.
* How core skills differ from user/project skills.
* How skills are invoked.
* How skill instructions are packaged.
* How skill-specific context is injected.
* How skills interact with tools and approvals.

Potential adaptation:

```text
.mythic/skills/
  architecture-audit/
    SKILL.md
  repo-cartography/
    SKILL.md
  test-forge/
    SKILL.md
  continuity-check/
    SKILL.md
  documentation-scribe/
    SKILL.md
```

---

## 5.9 Patch Application

`codex-rs/apply-patch` is one of the most interesting plunder targets because reliable file editing is central to any coding agent. ([GitHub][10])

Worth studying:

* Patch format.
* Patch validation.
* Failure handling.
* File creation/deletion/modification.
* Conflict detection.
* Human-readable patch previews.
* Testable edit operations.

Your CLI should treat patching as sacred infrastructure.

Suggested principle:

```md
All agent edits should pass through a patch layer when possible.

The patch layer should:

- Show what changed.
- Fail safely.
- Preserve encoding.
- Avoid partial corruption.
- Support dry runs.
- Be testable without model calls.
```

---

## 5.10 Git Utilities

`codex-rs/git-utils` is worth study because coding agents need strong Git awareness. ([GitHub][10])

Likely useful patterns:

* Detect dirty working tree.
* Detect untracked files.
* Determine changed files.
* Read diffs.
* Protect user changes.
* Avoid overwriting work.
* Produce review summaries.
* Separate agent changes from pre-existing changes.

Suggested adaptation:

```md
## Git Safety Law

Before making edits, the CLI should identify:

- Current branch.
- Dirty files.
- Untracked files.
- Files already modified by the user.
- Whether the repo has pending conflicts.

The agent must not silently overwrite user work.
```

---

## 5.11 Model Provider Architecture

The `codex-rs` tree includes areas such as `model-provider`, `model-provider-info`, and `models-manager`. ([GitHub][10])

This is highly relevant if your CLI will support:

* OpenRouter
* OpenAI
* Anthropic-compatible providers
* Local LM Studio
* Ollama
* Qwen
* Mistral
* Multiple model roles

Worth studying:

* Provider abstraction.
* Model catalog.
* Model capability metadata.
* Routing by task type.
* Configurable model selection.
* Fallback design.
* Local vs remote providers.

Potential Mythic CLI design:

```toml
[models.architect]
provider = "openrouter"
model = "anthropic/claude-opus-4.5"

[models.forge_worker]
provider = "openrouter"
model = "qwen/qwen3.5-coder"

[models.auditor]
provider = "openai"
model = "gpt-5.5-thinking"

[models.local_roleplay]
provider = "lmstudio"
model = "stheno-8b"
```

---

## 5.12 TUI Design

`codex-rs/tui` is valuable if your CLI needs a serious terminal interface. ([GitHub][10])

Worth studying:

* Message rendering.
* Streaming output.
* Approval prompts.
* Tool call display.
* Keyboard shortcuts.
* Session navigation.
* Error display.
* Terminal notifications.
* Diff previews.
* Long-running command progress.

For your Cyber-Viking CLI aesthetic, this could become:

```md
## Mythic TUI Goals

The terminal UI should feel:

- Fast.
- Dark.
- Structured.
- Keyboard-native.
- Agent-aware.
- Approval-safe.
- Beautiful without becoming cluttered.
```

---

## 5.13 State, Thread, and Rollout Storage

The repo has `state`, `thread-store`, `rollout`, and `rollout-trace` areas. ([GitHub][10])

Codex config docs also mention a SQLite-backed state DB under `sqlite_home` or `CODEX_SQLITE_HOME`. ([GitHub][9])

Worth studying:

* Session persistence.
* Conversation replay.
* Thread storage.
* Debug traces.
* Ephemeral sessions.
* SQLite-backed local state.
* Separation between session memory and project files.

For your CLI, this maps directly to your continuity obsession.

Suggested adaptation:

```text
.mythic/state/
  sessions.sqlite
  rollouts/
  traces/
  thread-store/
  run-ledger/
```

---

## 5.14 Hooks and Notifications

Codex config docs mention notification hooks that can run when the agent finishes a turn. ([GitHub][9])

Worth plundering:

* Completion hooks.
* Approval-needed hooks.
* Failure hooks.
* Desktop notifications.
* Sound hooks.
* Logging hooks.
* Scriptable lifecycle events.

Possible config:

```toml
[hooks]
on_turn_complete = "mythic-notify complete"
on_approval_needed = "mythic-notify approval"
on_error = "mythic-notify error"
```

---

# 6. Suggested Plunder Priority

## Tier 1 — Highest Value

Study these first:

1. `codex-rs/core`
2. `codex-rs/cli`
3. `codex-rs/tui`
4. `codex-rs/tools`
5. `codex-rs/exec`
6. `codex-rs/execpolicy`
7. `codex-rs/sandboxing`
8. `codex-rs/apply-patch`
9. `codex-rs/git-utils`
10. `codex-rs/config`

These are the load-bearing bones.

---

## Tier 2 — Strategic Power

Study next:

1. `codex-rs/codex-mcp`
2. `codex-rs/mcp-server`
3. `codex-rs/model-provider`
4. `codex-rs/models-manager`
5. `codex-rs/skills`
6. `codex-rs/core-skills`
7. `codex-rs/thread-store`
8. `codex-rs/state`
9. `codex-rs/rollout`
10. `codex-rs/hooks`

These are the expansion systems.

---

## Tier 3 — Useful Support Infrastructure

Study later:

1. `codex-cli`
2. `sdk/python`
3. `sdk/typescript`
4. `scripts`
5. `justfile`
6. `BUILD.bazel`
7. `flake.nix`
8. `deny.toml`
9. `.github/workflows`
10. `tools/argument-comment-lint`

These are build, packaging, SDK, and developer-experience supports.

---

# 7. What Not To Plunder Blindly

Be cautious with:

* OpenAI-specific auth flows.
* OpenAI-specific service endpoints.
* Product branding.
* Telemetry implementation.
* Cloud task clients.
* ChatGPT-account-specific logic.
* Internal protocol assumptions.
* Enterprise features tied to OpenAI infrastructure.
* Any generated OpenAPI models without understanding their license and purpose.
* Anything that would imply your tool is an official OpenAI product.

Better strategy:

> Copy architecture patterns freely.
> Copy implementation carefully.
> Rewrite service-specific integrations.

---

# 8. Recommended Local Study Workflow

## Step 1: Clone Upstream

```bash
git clone https://github.com/openai/codex.git external/openai-codex
cd external/openai-codex
```

## Step 2: Inspect Structure

```bash
find codex-rs -maxdepth 2 -type d | sort
```

## Step 3: Make a Plunder Map

Create this file in your own project:

```text
docs/plunder/OPENAI_CODEX_CLI_PLUNDER_MAP.md
```

Suggested format:

```md
# OpenAI Codex CLI Plunder Map

## Upstream

Project: OpenAI Codex CLI  
Repo: openai/codex  
License: Apache-2.0  
NOTICE required: Yes  

## Targeted Areas

| Upstream Path | Local Target | Status | Notes |
|---|---|---|---|
| codex-rs/apply-patch | mythic_cli/patching | studying | Need safe patch engine |
| codex-rs/git-utils | mythic_cli/git | planned | Need dirty-tree protection |
| codex-rs/config | mythic_cli/config | planned | Convert to Mythic config schema |
| codex-rs/tui | mythic_cli/tui | studying | Cyber-Viking terminal UX |
| codex-rs/skills | .mythic/skills | planned | Skill packet system |
```

## Step 4: Copy One Subsystem at a Time

Use branches.

```bash
git checkout -b adapt-codex-apply-patch
```

## Step 5: Commit With Attribution

```bash
git commit -m "Adapt patch architecture from OpenAI Codex CLI

- Adds Apache-2.0 attribution
- Preserves upstream NOTICE requirements
- Marks modified files
- Reworks module names for Mythic CLI architecture"
```

---

# 9. Recommended Repo Files For Your Project

Your CLI should include:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/OPENAI_CODEX_CLI_PLUNDER_GUIDE.md
docs/plunder/OPENAI_CODEX_CLI_PLUNDER_MAP.md
docs/architecture/AGENT_PERMISSION_MODEL.md
docs/architecture/SANDBOXING_AND_APPROVALS.md
docs/architecture/PATCH_ENGINE.md
docs/architecture/MCP_INTEGRATION.md
```

---

# 10. Suggested README Attribution

Add this to your README:

```md
## Third-Party Attribution

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected architectural patterns and code from OpenAI Codex CLI, also licensed under Apache-2.0.

OpenAI Codex  
Copyright 2025 OpenAI

This project is independent and is not affiliated with, endorsed by, or sponsored by OpenAI.
```

---

# 11. Suggested `THIRD_PARTY_NOTICES.md`

```md
# Third-Party Notices

This project includes or adapts material from third-party open-source projects.

## OpenAI Codex CLI

Project: OpenAI Codex CLI  
Repository: openai/codex  
License: Apache License 2.0  

Attribution:

OpenAI Codex  
Copyright 2025 OpenAI

Usage:

This project may include or adapt selected portions of OpenAI Codex CLI, especially architecture patterns related to:

- CLI command structure
- Terminal UI
- Agent execution loop
- Sandboxing and approvals
- Patch application
- Git utilities
- MCP integration
- Config management
- Skill loading
- Session and state storage

This project is independent and is not affiliated with, endorsed by, or sponsored by OpenAI.

## Ratatui

OpenAI Codex CLI’s NOTICE file identifies code derived from Ratatui.

License: MIT

Copyright (c) 2016-2022 Florian Dehau  
Copyright (c) 2023-2025 The Ratatui Developers

## Meriyah

OpenAI Codex CLI’s NOTICE file identifies Meriyah parser assets.

License: ISC

Copyright (c) 2019 and later, KFlash and others.
```

---

# 12. Mythic CLI Plunder Targets

For your own CLI project, these are the most strategically useful pieces.

## 12.1 Agent Loop

Goal:

```md
Create a disciplined agent loop that can:

- Read project context.
- Build a plan.
- Request approval when needed.
- Execute tools.
- Apply patches.
- Run tests.
- Summarize changes.
- Persist useful session state.
```

Best upstream areas:

```text
codex-rs/core
codex-rs/tools
codex-rs/protocol
codex-rs/rollout
codex-rs/thread-store
```

---

## 12.2 Mythic Permission System

Goal:

```md
Separate spiritual/creative autonomy from technical filesystem power.

The agent may think freely.
The agent may propose freely.
The agent may only act inside defined boundaries.
```

Best upstream areas:

```text
codex-rs/sandboxing
codex-rs/execpolicy
codex-rs/execpolicy-legacy
codex-rs/shell-escalation
codex-rs/linux-sandbox
codex-rs/windows-sandbox-rs
```

---

## 12.3 Patch Forge

Goal:

```md
All file modifications should move through a safe patch forge.

The patch forge should:

- Preview changes.
- Apply changes safely.
- Reject malformed patches.
- Protect user edits.
- Support dry runs.
- Integrate with Git state.
```

Best upstream areas:

```text
codex-rs/apply-patch
codex-rs/git-utils
```

---

## 12.4 Cyber-Viking TUI

Goal:

```md
Build a terminal UI that feels like a serious command sanctum:

- Fast.
- Dark.
- Keyboard-native.
- Minimal but beautiful.
- Clear about tool calls.
- Clear about approvals.
- Clear about risk.
```

Best upstream areas:

```text
codex-rs/tui
codex-rs/ansi-escape
codex-rs/terminal-detection
codex-rs/hooks
```

---

## 12.5 Multi-Agent Role System

Goal:

```md
Support named agent roles:

- Architect
- Forge Worker
- Auditor
- Cartographer
- Scribe
- Seer
- Warden
```

Best upstream areas:

```text
codex-rs/agent-identity
codex-rs/config
codex-rs/core
AGENTS.md
```

---

## 12.6 Skill System

Goal:

```md
Support reusable skill packets:

- Repo cartography
- Architecture audit
- Patch forge
- Test repair
- Documentation scribe
- Refactor planning
- Continuity recovery
```

Best upstream areas:

```text
.codex/skills
codex-rs/skills
codex-rs/core-skills
```

---

## 12.7 MCP Tool Layer

Goal:

```md
Allow external tools and local knowledge systems to be attached safely.

Examples:

- GitHub MCP
- Google Drive MCP
- Local docs MCP
- File search MCP
- D&D rules MCP
- Norse lore MCP
- Project memory MCP
```

Best upstream areas:

```text
codex-rs/codex-mcp
codex-rs/mcp-server
codex-rs/rmcp-client
```

---

## 12.8 Config Law

Goal:

```md
Use layered configuration:

- Global user config.
- Project config.
- Role config.
- Provider config.
- Tool config.
- Sandbox config.
- Skill config.
```

Best upstream areas:

```text
codex-rs/config
codex-rs/features
codex-rs/model-provider
codex-rs/models-manager
```

---

# 13. Final Checklist Before Publishing

Before pushing your adapted project publicly:

* [ ] Your repo has `LICENSE`.
* [ ] Your repo has `NOTICE`.
* [ ] Your repo credits OpenAI Codex.
* [ ] Your repo preserves relevant Ratatui and Meriyah notices if applicable.
* [ ] Modified files include change notices.
* [ ] Your README says the project is independent.
* [ ] You removed OpenAI/Codex branding from your own product identity.
* [ ] You did not copy secrets, credentials, or private configs.
* [ ] You understand every copied subsystem.
* [ ] You tested each adapted subsystem.
* [ ] You documented upstream paths in a plunder map.
* [ ] You avoided service-specific OpenAI assumptions unless intentionally integrating with OpenAI APIs.

---

# 14. Clean Rule

```text
Copy the architecture.
Respect the license.
Preserve the notices.
Mark your changes.
Do not steal the branding.
Rewrite what is service-specific.
Keep what is structurally brilliant.
```

OpenAI Codex CLI is not just code to copy. It is a working pattern-library for modern agentic CLI design: sandbox law, terminal ritual, tool execution, patch discipline, MCP gateways, state memory, and config sovereignty.

For your own CLI, the real treasure is not one file.

The treasure is the architecture.

[1]: https://github.com/openai/codex "GitHub - openai/codex: Lightweight coding agent that runs in your terminal · GitHub"
[2]: https://github.com/openai/codex/blob/main/LICENSE "codex/LICENSE at main · openai/codex · GitHub"
[3]: https://github.com/openai/codex/blob/main/NOTICE "codex/NOTICE at main · openai/codex · GitHub"
[4]: https://github.com/openai/codex/blob/main/AGENTS.md "codex/AGENTS.md at main · openai/codex · GitHub"
[5]: https://developers.openai.com/codex/config-reference "Configuration Reference – Codex | OpenAI Developers"
[6]: https://developers.openai.com/codex/cli/reference "Command line options – Codex CLI | OpenAI Developers"
[7]: https://developers.openai.com/codex/mcp "Model Context Protocol – Codex | OpenAI Developers"
[8]: https://developers.openai.com/codex/concepts/sandboxing "Sandbox – Codex | OpenAI Developers"
[9]: https://github.com/openai/codex/blob/main/docs/config.md "codex/docs/config.md at main · openai/codex · GitHub"
[10]: https://github.com/openai/codex/tree/main/codex-rs "codex/codex-rs at main · openai/codex · GitHub"
[11]: https://github.com/openai/codex/tree/main/codex-cli "codex/codex-cli at main · openai/codex · GitHub"
[12]: https://github.com/openai/codex/tree/main/sdk "codex/sdk at main · openai/codex · GitHub"
