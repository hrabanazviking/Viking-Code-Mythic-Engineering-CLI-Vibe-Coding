# Goose Plundering Guide

## Purpose

This guide explains how to lawfully study, reuse, adapt, and “plunder” useful architecture from **goose** for your own Apache-2.0 CLI project.

goose is an open-source, local AI agent with a **desktop app, CLI, and API**, built for coding, workflows, research, writing, automation, data analysis, and general local-agent tasks. It is now under the **Agentic AI Foundation / AAIF** at the Linux Foundation, after moving from `block/goose` to `aaif-goose/goose`. ([GitHub][1])

This is practical open-source hygiene, not legal advice.

---

## 1. Core Legal Position

goose is licensed under **Apache License 2.0**. The GitHub repo lists the project as Apache-2.0 licensed, and its custom distribution guide explicitly says custom distributions must include original license/copyright notices, clearly indicate modifications, and avoid using Goose trademarks in ways that imply official endorsement. ([GitHub][1])

Under Apache-2.0, you can generally:

* copy code
* modify code
* redistribute modified versions
* use it commercially
* build a custom CLI or custom distribution
* adapt useful architecture into your own Apache-2.0 project

But you must preserve notices, mark modifications, and avoid false affiliation.

> Take the useful steel.
> Keep the maker’s mark.
> Forge your own blade.

---

## 2. Required Source Links

Use these as canonical upstream references in your repo docs.

### Main Links

* [goose GitHub Repository](https://github.com/aaif-goose/goose)
* [goose LICENSE](https://github.com/aaif-goose/goose/blob/main/LICENSE)
* [goose Documentation](https://goose-docs.ai/)
* [goose Quickstart](https://goose-docs.ai/docs/quickstart/)
* [goose Architecture](https://goose-docs.ai/docs/goose-architecture/)
* [goose CLI Commands](https://goose-docs.ai/docs/guides/goose-cli-commands/)
* [goose Permission Modes](https://goose-docs.ai/docs/guides/goose-permissions/)
* [goose Developer Extension](https://goose-docs.ai/docs/mcp/developer-mcp/)
* [goose Extensions](https://goose-docs.ai/docs/getting-started/using-extensions/)
* [goose Recipes](https://goose-docs.ai/docs/guides/recipes/)
* [Recipe Reference Guide](https://goose-docs.ai/docs/guides/recipes/recipe-reference/)
* [Reusable Recipes](https://goose-docs.ai/docs/guides/recipes/session-recipes/)
* [goose Subagents](https://goose-docs.ai/docs/guides/subagents/)
* [goose Skills](https://goose-docs.ai/docs/guides/context-engineering/using-skills/)
* [goose Hints / `.goosehints`](https://goose-docs.ai/docs/guides/context-engineering/using-goosehints/)
* [goose Configuration Files](https://goose-docs.ai/docs/guides/config-files/)
* [goose Prompt Templates](https://goose-docs.ai/docs/guides/prompt-templates/)
* [goose CLI Providers](https://goose-docs.ai/docs/guides/cli-providers/)
* [goose Security](https://goose-docs.ai/docs/guides/security/)
* [goose macOS Sandbox](https://goose-docs.ai/docs/guides/sandbox)
* [Custom Distributions of goose](https://github.com/aaif-goose/goose/blob/main/CUSTOM_DISTROS.md)
* [Goose in CI/CD](https://goose-docs.ai/docs/tutorials/cicd/)

---

## 3. Important Upstream Status

goose used to live under `block/goose`, but the current GitHub repository says the project has moved to the **Agentic AI Foundation / AAIF** at the Linux Foundation. Some references may still point to Block while the transition finishes. ([GitHub][1])

For attribution, use the current repo:

```text
aaif-goose/goose
```

But it is reasonable to mention historical Block origin if relevant:

```text
goose, originally developed by Block and now under AAIF / Linux Foundation governance.
```

---

## 4. Core Apache-2.0 Duties

### 4.1 Keep the License

Your project should include:

```text
LICENSE
```

Use Apache License 2.0 if your project is already Apache-2.0.

---

### 4.2 Preserve Notices

When copying files or meaningful chunks from goose:

* preserve upstream copyright/license headers
* preserve SPDX headers if present
* preserve relevant third-party notices
* do not claim copied code was written entirely from scratch
* do not remove references to goose upstream authorship

Suggested Rust header:

```rust
// Portions adapted from aaif-goose/goose.
// Upstream project: goose, licensed under Apache License 2.0.
// Modified by Volmarr / RuneForgeAI, 2026.
// Licensed under the Apache License, Version 2.0.
```

Suggested TypeScript header:

```ts
// Portions adapted from aaif-goose/goose.
// Upstream project: goose, licensed under Apache License 2.0.
// Modified by Volmarr / RuneForgeAI, 2026.
// Licensed under the Apache License, Version 2.0.
```

Suggested Markdown header:

```md
<!--
Portions adapted from aaif-goose/goose.
Upstream project: goose, licensed under Apache License 2.0.
Modified by Volmarr / RuneForgeAI, 2026.
Licensed under the Apache License, Version 2.0.
-->
```

---

### 4.3 Add Third-Party Notices

Recommended repo files:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/GOOSE_PLUNDER_GUIDE.md
docs/plunder/GOOSE_PLUNDER_MAP.md
```

Suggested `NOTICE`:

```md
# NOTICE

[Your CLI Project Name]

Copyright 2026 Volmarr / RuneForgeAI

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected portions of software from:

## goose

Project: goose  
Repository: aaif-goose/goose  
License: Apache License 2.0

goose is an open-source local AI agent with desktop, CLI, and API interfaces.

This project is independent and is not affiliated with, endorsed by, or sponsored by the Agentic AI Foundation, Linux Foundation, Block, or the goose project.
```

Suggested `THIRD_PARTY_NOTICES.md`:

```md
# Third-Party Notices

This project includes or adapts material from third-party open-source projects.

## goose

Project: goose  
Repository: aaif-goose/goose  
License: Apache License 2.0  

Usage:

This project may include or adapt selected portions of goose, especially architectural patterns related to:

- local AI agent architecture
- desktop / CLI / API split
- Rust agent core
- TypeScript desktop UI
- MCP extension integration
- ACP interoperability
- provider abstraction
- custom distributions
- recipes
- subagents
- skills
- permission modes
- prompt templates
- `.goosehints` project context
- Developer extension behavior
- session management
- REST API bridge
- tool permissions
- codebase analysis
- enhanced code editing
- security and sandboxing patterns

This project is independent and is not affiliated with, endorsed by, or sponsored by the Agentic AI Foundation, Linux Foundation, Block, or the goose project.
```

---

## 5. Branding Warning

Apache-2.0 lets you reuse code. It does **not** let you steal product identity.

Safe wording:

```md
This project includes code adapted from aaif-goose/goose.
```

Unsafe wording:

```md
This is the official goose CLI.
```

Avoid names like:

* Official Goose Fork
* Goose Pro
* Goose Mythic Edition
* AAIF Goose CLI
* Linux Foundation Goose Agent
* Block Goose Agent

Use “goose” only for attribution and source description.

---

## 6. What goose Is Architecturally

goose’s own architecture guide describes three main components:

1. **Interface** — desktop app or CLI.
2. **Agent** — core logic and interactive loop.
3. **Extensions** — MCP-connected tools that allow the agent to perform actions like running commands and managing files. ([Goose Docs][2])

That split is one of the most useful things to copy conceptually:

```text
Interface
  ↓
Agent Core
  ↓
Extensions / Tools
```

For your own CLI, that maps cleanly to:

```text
mythic_cli/
  interface/
  agent_core/
  tools/
  mcp/
  providers/
  recipes/
  permissions/
```

---

## 7. Repo Structure Worth Studying

The current goose repo is a Rust + TypeScript project. GitHub lists major top-level directories including:

```text
.agents/
.claude/
.codex/
.cursor/
bin/
crates/
documentation/
evals/
examples/
oidc-proxy/
recipe-scanner/
scripts/
services/
ui/
vendor/
workflow_recipes/
```

The repo also shows **Rust** and **TypeScript** as the two dominant languages. ([GitHub][1])

The `crates/` folder currently contains:

```text
crates/
  goose-acp-macros/
  goose-cli/
  goose-mcp/
  goose-sdk/
  goose-server/
  goose-test-support/
  goose-test/
  goose/
```

This is one of the most important structural maps for plundering because it separates CLI, MCP, SDK, server, tests, and the core goose crate. ([GitHub][3])

The `ui/` folder currently contains:

```text
ui/
  desktop/
  goose-binary/
  goose2/
  install-link-generator/
  scripts/
  sdk/
  text/
```

That is useful if you want to study how goose separates desktop UI, SDK, and text/terminal interface pieces. ([GitHub][4])

---

## 8. Highest-Value Plunder Targets

## 8.1 `crates/goose/` — Core Agent Engine

This is likely the richest core target.

goose’s custom distribution guide describes the core `goose` crate as containing the provider system, extension system, config, and recipes. ([GitHub][5])

Likely interesting areas:

```text
crates/goose/src/providers/
crates/goose/src/providers/base.rs
crates/goose/src/providers/factory.rs
crates/goose/src/providers/declarative/
crates/goose/src/config/
crates/goose/src/config/base.rs
crates/goose/src/prompts/
crates/goose/src/recipe/
crates/goose/src/recipe/mod.rs
crates/goose/src/recipe/local_recipes.rs
crates/goose/src/posthog.rs
```

### Why It Matters

This is where goose’s basic “agent operating system” logic lives:

* provider abstraction
* config
* recipes
* prompts
* extension/tool integration
* secret storage
* model setup
* workflow behavior

### Mythic CLI Adaptation

```text
mythic_cli/core/
  agent_loop.py
  providers/
  config/
  prompts/
  recipes/
  secrets/
  extensions/
```

Design law:

```md
## Core Agent Law

The core should not care whether the user is in a desktop app, terminal, API, or CI workflow.

The core owns:

- model/provider selection
- prompt construction
- tool routing
- extension registry
- permission policy
- session state
- recipe execution
```

---

## 8.2 `crates/goose-cli/` — CLI Interface

goose has a full CLI for terminal workflows, with commands for managing sessions, configuration, and extensions. Its command docs emphasize consistent flag naming patterns, including `--session-id`, `--schedule-id`, `--output`, `--resume`, `--verbose`, `--limit`, `--format`, and `--working_dir`. ([Goose Docs][6])

Likely interesting areas:

```text
crates/goose-cli/
```

### Plunder Value

Study for:

* command structure
* `goose configure`
* session commands
* extension configuration UX
* consistent flag naming
* session resume
* output formatting
* terminal-first workflow

### Mythic CLI Adaptation

```bash
mythic session
mythic configure
mythic info -v
mythic recipe run ./repo-audit.yaml
mythic session --resume latest
mythic session --format json
```

Design law:

```md
## CLI Law

The CLI should expose the same core engine as the desktop/API layers.

Do not build a weak CLI around a strong agent.

The CLI should support:

- sessions
- config
- recipes
- extensions
- permissions
- output formats
- resume/export
```

---

## 8.3 `crates/goose-server/` — REST API Bridge

The custom distribution guide shows `goose-server`, also called `goosed`, sitting between the user interfaces and core, providing a REST API for all goose functionality. ([GitHub][5])

Likely interesting area:

```text
crates/goose-server/
```

### Why It Matters

This is huge if your CLI project eventually wants:

* desktop UI
* web UI
* local API
* VS Code / IDE bridge
* mobile control surface
* multi-agent orchestration
* external automation control

### Mythic CLI Adaptation

```text
mythic_server/
  api.py
  routes/
  sessions.py
  recipes.py
  providers.py
  tools.py
  permissions.py
```

Design law:

```md
## Server Bridge Law

The agent core should be callable from more than one interface.

A local REST/API bridge allows:

- CLI
- desktop
- browser
- IDE extensions
- automation scripts
- external controllers
```

---

## 8.4 `crates/goose-mcp/` — MCP Integration

goose is deeply built around **Model Context Protocol**. Its docs say MCP is the open standard goose uses to connect to external tools and data sources, and goose calls these MCP systems “extensions.” ([Goose Docs][2])

Likely interesting area:

```text
crates/goose-mcp/
```

### Plunder Value

Study for:

* MCP client behavior
* extension discovery
* tool calls
* tool metadata
* extension registration
* tool errors
* external process management
* command-line MCP setup
* built-in vs external extension boundaries

### Mythic CLI Adaptation

```text
mythic_cli/mcp/
  client.py
  server_registry.py
  extension_config.py
  tool_bridge.py
  tool_permissions.py
```

Design law:

```md
## MCP Law

Tools should be external, typed, inspectable, and permission-scoped.

The agent should not hardwire every tool into the core.

Use MCP for:

- file tools
- GitHub
- Google Drive
- browsers
- local knowledge
- code analysis
- memory
- databases
- custom project tools
```

---

## 8.5 Developer Extension

The Developer extension is one of the most important goose systems to study. The docs say it allows goose to automate developer-centric tasks such as file editing, shell command execution, project setup, enhanced code editing, and codebase analysis. It is built in and enabled by default when goose is installed. ([Block][7])

The docs identify tools such as:

* `shell`
* `text_editor`
* `analyze`
* `screen_capture`
* `image_processor`

The docs also label `shell` and `text_editor` as high-risk because they can execute commands and modify accessible files. ([Block][7])

### Mythic CLI Adaptation

```text
mythic_cli/extensions/developer/
  shell.py
  text_editor.py
  analyze.py
  screen_capture.py
  image_processor.py
```

Design law:

```md
## Developer Tool Law

Developer tools are powerful and dangerous.

Each tool must declare:

- capabilities
- risk level
- permission requirements
- affected filesystem scope
- whether approval is needed
- whether it can mutate state
```

---

## 8.6 Permission Modes

goose has four permission modes:

| Mode                  | Behavior                                                            |
| --------------------- | ------------------------------------------------------------------- |
| Completely Autonomous | Can modify files, use extensions, and delete files without approval |
| Manual Approval       | Asks before using tools/extensions                                  |
| Smart Approval        | Risk-based approval for higher-risk actions                         |
| Chat Only             | No extension use or file modification                               |

The docs also say **Autonomous Mode is applied by default**. ([Goose Docs][8])

### Mythic CLI Adaptation

```text
plan
chat
approve
smart_approve
auto
```

Suggested config:

```yaml
permissions:
  default_mode: approve
  allow_autonomous_delete: false
  require_approval_for_shell: true
  require_approval_for_external_network: true
```

Design law:

```md
## Permission Law

The agent may think freely.

The agent may act only according to its active permission mode.

Dangerous modes must be visible, explicit, reversible, and easy to change.
```

For your CLI, I would **not** default to full autonomous mode. I would default to something closer to **Smart Approval** or **Manual Approval**, especially during development.

---

## 8.7 Smart Approval / Tool Permissions

Goose’s permission docs mention granular tool permissions alongside Manual Approval and Smart Approval modes. ([Goose Docs][8])

This is very worth plundering conceptually.

### Mythic CLI Adaptation

```yaml
tools:
  shell:
    permission: ask
    risk: high
  text_editor:
    permission: ask
    risk: high
  analyze:
    permission: allow
    risk: low
  screen_capture:
    permission: ask
    risk: medium
  search_docs:
    permission: allow
    risk: low
```

Design law:

```md
## Tool Permission Law

Permission should be per tool, not just per agent.

A safe agent can still call a dangerous tool.

A dangerous tool should require approval even when the agent seems trustworthy.
```

---

## 8.8 Recipes

Recipes are one of goose’s strongest plunder targets.

The docs define recipes as reusable workflows that package extensions, prompts, and settings together so teams can reproduce proven workflows. ([Goose Docs][9])

Reusable recipes can include:

* title and description
* instructions
* initial prompt
* activities / clickable buttons
* parameters
* model and provider
* extensions
* response JSON schema
* subrecipes

([Goose Docs][10])

Recipe files can be JSON or YAML, and goose can generate a recipe from a session with `/recipe`. ([Goose Docs][10])

### Mythic CLI Adaptation

```text
.mythic/recipes/
  architecture-audit.yaml
  release-risk-check.yaml
  code-review.yaml
  docs-refresh.yaml
```

Example:

```yaml
version: 1.0.0
title: Architecture Audit
description: Audit a codebase for structural drift, ownership confusion, and missing docs.

instructions: |
  You are The Architect.
  Read DOMAIN_MAP.md, ARCHITECTURE.md, README.md files, and INTERFACE.md files.
  Identify boundary violations, duplicate ownership, stale docs, and dangerous coupling.

parameters:
  - key: target_path
    input_type: string
    requirement: optional
    default: "."

extensions:
  - type: builtin
    name: developer

settings:
  permission_mode: approve
  output_format: markdown
```

Design law:

```md
## Recipe Law

A recipe is a reusable ritual.

It should package:

- role
- purpose
- instructions
- tools
- permissions
- parameters
- expected output
- optional subrecipes
```

For your Mythic Engineering world, recipes are basically **structured vibe-coding rituals**.

---

## 8.9 Subagents

goose supports subagents: independent instances that execute tasks while keeping the main conversation focused. The docs say goose can autonomously create subagents in autonomous mode, and subagents are disabled in manual approval, smart approval, and chat-only modes. ([Goose Docs][11])

The docs also say recipes can define specific instructions, extensions, and behavior for subagents. ([Goose Docs][11])

### Mythic CLI Adaptation

```text
.mythic/subagents/
  architect.yaml
  auditor.yaml
  forge-worker.yaml
  cartographer.yaml
  scribe.yaml
```

Example:

```yaml
version: 1.0.0
title: Auditor Subagent
description: Reviews changes for bugs, regressions, unsafe assumptions, and missing tests.

instructions: |
  You are The Auditor.
  Inspect the current diff and identify only actionable risks.
  Do not rewrite code unless explicitly asked.

extensions:
  - type: builtin
    name: developer

settings:
  permission_mode: chat
```

Design law:

```md
## Subagent Law

Subagents should isolate context and responsibility.

Use them for:

- code review
- research
- file processing
- test analysis
- architecture review
- documentation cleanup

Do not let subagents mutate the same files blindly in parallel.
```

---

## 8.10 Skills

goose Skills are reusable instruction/resource packages that teach goose how to perform specific tasks. The docs say a skill can be a simple checklist or a detailed workflow with supporting files such as scripts or templates. ([Goose Docs][12])

### Mythic CLI Adaptation

```text
.mythic/skills/
  architecture-audit/
    SKILL.md
    examples.md
  patch-forge/
    SKILL.md
    templates/
  repo-cartography/
    SKILL.md
    scripts/
  release-risk-check/
    SKILL.md
```

Example:

```md
# Architecture Audit Skill

## Purpose

Audit a repository for structural drift, unclear ownership, stale docs, and unsafe coupling.

## Required Inputs

- DOMAIN_MAP.md
- ARCHITECTURE.md
- README.md files
- INTERFACE.md files
- current Git diff

## Process

1. Identify major domains.
2. Compare implementation against declared boundaries.
3. Detect circular dependencies.
4. Detect stale interface docs.
5. Produce a repair plan.

## Output

Return:

1. Findings
2. Severity
3. Affected files
4. Repair plan
5. Required documentation updates
```

Design law:

```md
## Skill Law

A skill is not just a prompt.

A skill should include:

- purpose
- when to use it
- required context
- procedure
- outputs
- examples
- safety limits
```

---

## 8.11 `.goosehints` / Project Context

goose supports global and local `.goosehints` files. Global hints live in `~/.config/goose/.goosehints`, while local hints can live at the project root or within directories. Local hints override global preferences when conflicts occur. ([Goose Docs][13])

goose can also load other agent rule files through the `CONTEXT_FILE_NAMES` environment variable. It loads hints at session start and can discover nested hints as it accesses files in nested directories. ([Goose Docs][13])

### Mythic CLI Adaptation

```text
MYTHIC.md
AGENTS.md
DOMAIN_MAP.md
ARCHITECTURE.md
INTERFACE.md
.mythic/hints.md
```

Suggested behavior:

```yaml
context_files:
  - MYTHIC.md
  - AGENTS.md
  - DOMAIN_MAP.md
  - ARCHITECTURE.md
  - INTERFACE.md
  - .mythic/hints.md
```

Design law:

```md
## Context Law

Project law should live in files.

The agent should automatically load:

- global preferences
- project rules
- directory-specific rules
- role instructions
- interface contracts

Local rules should override global preferences when they conflict.
```

This maps directly to your repo-doc style.

---

## 8.12 Prompt Templates

goose supports customizing prompt templates. Its docs say built-in prompt templates guide behavior in different situations, and users can override defaults through local config. Custom templates persist across goose updates, and changes take effect in new sessions. ([Goose Docs][14])

### Mythic CLI Adaptation

```text
.mythic/prompts/
  system.md
  planning.md
  compaction.md
  tool-use.md
  review.md
  handoff.md
```

Design law:

```md
## Prompt Template Law

Prompts should be versioned, editable, and role-specific.

Do not bury all agent behavior in source code.

Expose:

- system prompt
- planning prompt
- review prompt
- compaction prompt
- tool-use prompt
- subagent prompt
```

---

## 8.13 Custom Distributions

goose is explicitly designed to be forked and customized. Its custom distribution guide says organizations can create remixed versions with preconfigured AI providers, bundled tools, customized branding/UI/default behavior, and audience-specific versions. ([GitHub][5])

The same guide gives key customization points:

| Goal                        | Where goose says to look                                  |
| --------------------------- | --------------------------------------------------------- |
| Preconfigure model/provider | `config.yaml`, `init-config.yaml`, env vars               |
| Add custom AI providers     | `crates/goose/src/providers/declarative/`                 |
| Bundle MCP extensions       | `config.yaml` extensions, desktop bundled-extension files |
| Modify system prompts       | `crates/goose/src/prompts/`                               |
| Customize desktop branding  | `ui/desktop/`                                             |
| Build a new UI              | `goose-server` REST API                                   |
| Guided workflows            | YAML recipes                                              |
| Multi-step workflows        | recipes + subrecipes + subagents                          |

([GitHub][5])

### Mythic CLI Adaptation

This is almost exactly what you want for a **Mythic Engineering CLI distro**:

```text
mythic-cli/
  config/
    init-config.yaml
  recipes/
  skills/
  agents/
  prompts/
  mcp/
  ui/
```

Design law:

```md
## Distro Law

A serious AI CLI should support custom distributions.

A distro can predefine:

- model providers
- local models
- MCP tools
- skills
- recipes
- system prompts
- branding
- workflow defaults
- safety defaults
```

---

## 8.14 Provider System

goose supports many model providers. Its homepage says it works with 15+ providers, including Anthropic, OpenAI, Google, Ollama, OpenRouter, Azure, Bedrock, and more. It can also use existing Claude, ChatGPT, or Gemini subscriptions through ACP. ([Goose Docs][15])

The custom distribution guide says you can add a declarative provider with JSON, using engines like `openai`, `anthropic`, or `ollama`, or implement a custom Provider trait for providers with unique APIs. ([GitHub][5])

### Mythic CLI Adaptation

```json
{
  "name": "openrouter",
  "engine": "openai",
  "display_name": "OpenRouter",
  "api_key_env": "OPENROUTER_API_KEY",
  "base_url": "https://openrouter.ai/api/v1/chat/completions",
  "models": [
    {
      "name": "qwen/qwen3.5-coder",
      "context_limit": 131072
    }
  ],
  "supports_streaming": true,
  "requires_auth": true
}
```

Design law:

```md
## Provider Law

Provider configuration should be declarative when possible.

Only write provider code when the API truly requires custom behavior.

A provider should declare:

- name
- engine/protocol
- base URL
- auth env var
- models
- context limits
- streaming support
- tool support
```

---

## 8.15 CLI Providers / ACP Bridge

goose has a very interesting CLI-provider system. Its docs say CLI providers are useful when you already have subscriptions to tools like Claude Code, Codex, Cursor, or Gemini CLI and want to use them through goose. The docs also say CLI providers can provide session persistence, export, recipe compatibility, scheduling support, unified commands, and multi-model workflows. ([Goose Docs][16])

The docs list provider options for:

* Claude Code
* OpenAI Codex CLI
* Cursor Agent
* Gemini CLI

([Goose Docs][16])

### Mythic CLI Adaptation

```yaml
providers:
  claude_code:
    type: cli
    command: claude
  codex:
    type: cli
    command: codex
  gemini_cli:
    type: cli
    command: gemini
  openrouter:
    type: api
    base_url: https://openrouter.ai/api/v1
```

Design law:

```md
## CLI Provider Law

Do not force every model through an API key.

A serious local agent should be able to delegate to:

- Claude Code
- Codex CLI
- Gemini CLI
- Cursor Agent
- local model tools
- API providers

Subscriptions are also infrastructure.
```

This is especially valuable for your multi-AI “crew” model.

---

## 8.16 ACP Support

goose works with **Agent Client Protocol**. The homepage says goose can act as an ACP server for Zed, JetBrains, or VS Code, and can use ACP agents like Claude Code and Codex as providers. ([Goose Docs][15])

### Mythic CLI Adaptation

```text
mythic_cli/acp/
  server.py
  client.py
  providers/
  ide_bridge.py
```

Design law:

```md
## ACP Law

A modern coding agent should not be trapped in one UI.

It should speak protocols that let it connect to:

- IDEs
- terminal agents
- desktop apps
- coding assistants
- external orchestrators
```

---

## 8.17 Security Systems

goose’s security docs point to several major safety systems:

* Adversary Mode
* prompt injection detection
* classification API
* macOS sandboxing
* extension allowlists
* environment variables
* `gooseignore`
* MCP roots

([Goose Docs][17])

The macOS sandbox guide says goose Desktop can use Apple sandbox technology to restrict filesystem access, control network connections, prevent bypasses, audit network activity, and enforce policy. It combines `sandbox-exec` file/network restrictions with a local egress proxy. ([Goose Docs][18])

### Mythic CLI Adaptation

```text
mythic_cli/security/
  prompt_injection.py
  adversary_reviewer.py
  sandbox.py
  extension_allowlist.py
  ignore_rules.py
  egress_proxy.py
```

Design law:

```md
## Security Law

Agent safety needs layers:

- permission mode
- tool permissions
- file ignore rules
- extension allowlist
- prompt injection detection
- adversary review
- sandboxing
- network controls
- audit logs
```

---

## 8.18 Error Handling

goose’s error-handling docs make a useful distinction between traditional errors and agent errors. Traditional errors include network/model availability issues; agent errors include things like unknown tool names, incorrect parameters, or tool failures that can be surfaced to the model for self-recovery. ([Goose Docs][19])

### Mythic CLI Adaptation

```text
mythic_cli/errors/
  traditional.py
  agent_recoverable.py
  tool_error.py
  retry_policy.py
  self_repair.py
```

Design law:

```md
## Agent Error Law

Not every error should crash the session.

Some errors should be returned to the model for recovery:

- unknown tool
- malformed arguments
- tool failure
- command failure
- missing file
- invalid patch

The runtime should distinguish recoverable agent errors from fatal system errors.
```

---

## 8.19 Codebase Analysis and Enhanced Editing

The Developer extension docs say goose provides enhanced code editing and codebase analysis through the built-in Developer MCP server. ([Block][7])

### Mythic CLI Adaptation

```text
mythic_cli/code_intel/
  analyze.py
  edit.py
  search.py
  symbol_map.py
  patch.py
```

Design law:

```md
## Code Intelligence Law

Do not make the model rely only on raw file reads.

Give it tools for:

- codebase analysis
- symbol discovery
- dependency lookup
- safe file editing
- structured patching
- project setup
```

---

## 8.20 UI / Desktop Architecture

goose has a native desktop app for macOS, Linux, and Windows, plus a CLI and API. The homepage says it is built in Rust for performance and portability. ([Goose Docs][15])

The repo’s `ui/` folder includes `desktop`, `sdk`, `text`, and other UI-related packages. ([GitHub][4])

### Mythic CLI Adaptation

Even if you start CLI-only, study the split:

```text
ui/
  desktop/
  text/
  sdk/
```

Potential target:

```text
mythic-ui/
  desktop/
  terminal/
  sdk/
```

Design law:

```md
## Interface Law

The interface should not own the agent.

The interface should only:

- collect input
- display output
- manage local UX
- call the core/server
- expose approvals
- render tool activity
```

---

## 9. Suggested Plunder Priority

### Tier 1 — Highest Value

Study first:

```text
crates/goose/
crates/goose-cli/
crates/goose-mcp/
crates/goose-server/
crates/goose-sdk/
CUSTOM_DISTROS.md
documentation/
```

These are the bones: core agent, CLI, MCP, server/API, SDK, and customization model.

---

### Tier 2 — Mythic Engineering Power Systems

Study next:

```text
crates/goose/src/providers/
crates/goose/src/config/
crates/goose/src/prompts/
crates/goose/src/recipe/
crates/goose/src/providers/declarative/
crates/goose/src/config/declarative_providers.rs
crates/goose/src/providers/base.rs
crates/goose/src/providers/factory.rs
ui/desktop/
ui/sdk/
workflow_recipes/
.agents/
.codex/
.claude/
.cursor/
```

These are the expansion systems: providers, recipes, prompts, skills/agent instruction folders, and UI integration.

---

### Tier 3 — Support Infrastructure

Study later:

```text
evals/
recipe-scanner/
examples/
services/
scripts/
oidc-proxy/
goose-self-test.yaml
BUILDING_LINUX.md
BUILDING_DOCKER.md
RELEASE.md
RELEASE_CHECKLIST.md
```

These are useful for testing, release, examples, workflows, auth, and build support.

---

## 10. What Not To Plunder Blindly

Be careful with:

* Goose branding
* AAIF / Linux Foundation branding
* Block branding
* telemetry defaults
* PostHog integration
* provider-specific auth flows
* OIDC proxy behavior
* UI branding assets
* desktop icons/logos
* hardcoded service assumptions
* security defaults you do not understand
* full autonomous mode defaults
* any code tied to paid/managed provider workflows

The clean strategy:

```md
Copy architecture aggressively.

Copy implementation selectively.

Rewrite branding, telemetry, provider defaults, security policy, and product-specific assumptions.
```

---

## 11. Recommended Local Study Workflow

### Step 1: Clone Upstream

```bash
git clone https://github.com/aaif-goose/goose.git external/goose
cd external/goose
```

### Step 2: Inspect Structure

```bash
find crates -maxdepth 2 -type d | sort
find ui -maxdepth 2 -type d | sort
find documentation -maxdepth 2 -type f | sort
find workflow_recipes -maxdepth 3 -type f | sort
```

### Step 3: Create a Plunder Map

Create:

```text
docs/plunder/GOOSE_PLUNDER_MAP.md
```

Template:

```md
# goose Plunder Map

## Upstream

Project: goose  
Repository: aaif-goose/goose  
License: Apache-2.0  
Governance: Agentic AI Foundation / Linux Foundation  

## Targeted Areas

| Upstream Path | Local Target | Status | Notes |
|---|---|---|---|
| crates/goose | mythic_cli/core | studying | Core agent, config, providers, recipes |
| crates/goose-cli | mythic_cli/cli | planned | CLI commands and session UX |
| crates/goose-mcp | mythic_cli/mcp | planned | MCP client/extension system |
| crates/goose-server | mythic_cli/server | planned | Local REST/API bridge |
| crates/goose-sdk | mythic_cli/sdk | planned | Embeddable SDK patterns |
| crates/goose/src/providers | mythic_cli/providers | planned | Provider abstraction |
| crates/goose/src/prompts | .mythic/prompts | planned | Prompt templates |
| crates/goose/src/recipe | .mythic/recipes | planned | YAML workflow system |
| ui/desktop | mythic_ui/desktop | later | Desktop shell ideas |
| .goosehints | MYTHIC.md / AGENTS.md | adapted | Project context pattern |
```

### Step 4: Copy One Subsystem at a Time

```bash
git checkout -b adapt-goose-recipes
```

### Step 5: Commit With Attribution

```bash
git commit -m "Adapt recipe workflow patterns from goose

- Adds Apache-2.0 attribution
- Marks modified files
- Updates THIRD_PARTY_NOTICES.md
- Reworks recipe schema for Mythic CLI"
```

---

## 12. README Attribution Template

```md
## Third-Party Attribution

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected architectural patterns and code from goose, also licensed under Apache-2.0.

goose is an open-source local AI agent currently under the Agentic AI Foundation / AAIF at the Linux Foundation.

This project is independent and is not affiliated with, endorsed by, or sponsored by the Agentic AI Foundation, Linux Foundation, Block, or the goose project.
```

---

## 13. Mythic CLI Adaptation Map

### 13.1 Agent Core

goose inspiration:

```text
crates/goose/
```

Mythic target:

```text
mythic_cli/core/
  agent_loop.py
  session.py
  provider_router.py
  extension_router.py
  tool_executor.py
```

---

### 13.2 CLI Layer

goose inspiration:

```text
crates/goose-cli/
```

Mythic target:

```text
mythic_cli/cli/
  main.py
  configure.py
  session.py
  info.py
  recipes.py
  extensions.py
```

---

### 13.3 MCP Extension System

goose inspiration:

```text
crates/goose-mcp/
```

Mythic target:

```text
mythic_cli/mcp/
  client.py
  server_config.py
  extension_registry.py
  tool_permissions.py
```

---

### 13.4 REST/API Bridge

goose inspiration:

```text
crates/goose-server/
```

Mythic target:

```text
mythic_cli/server/
  app.py
  routes/
  sessions.py
  recipes.py
  providers.py
  tools.py
```

---

### 13.5 Provider System

goose inspiration:

```text
crates/goose/src/providers/
crates/goose/src/providers/declarative/
crates/goose/src/providers/base.rs
crates/goose/src/providers/factory.rs
```

Mythic target:

```text
mythic_cli/providers/
  base.py
  factory.py
  declarative/
  openai.py
  anthropic.py
  openrouter.py
  ollama.py
  lmstudio.py
```

---

### 13.6 Recipes

goose inspiration:

```text
crates/goose/src/recipe/
workflow_recipes/
```

Mythic target:

```text
.mythic/recipes/
  architecture-audit.yaml
  release-risk-check.yaml
  code-review.yaml
  docs-refresh.yaml
```

---

### 13.7 Project Context

goose inspiration:

```text
.goosehints
CONTEXT_FILE_NAMES
```

Mythic target:

```text
MYTHIC.md
AGENTS.md
DOMAIN_MAP.md
ARCHITECTURE.md
INTERFACE.md
.mythic/hints.md
```

---

### 13.8 Prompt Templates

goose inspiration:

```text
crates/goose/src/prompts/
```

Mythic target:

```text
.mythic/prompts/
  system.md
  planning.md
  compaction.md
  review.md
  tool-use.md
```

---

### 13.9 Security

goose inspiration:

```text
security docs
permission modes
sandbox docs
gooseignore
extension allowlist
prompt injection detection
adversary mode
```

Mythic target:

```text
mythic_cli/security/
  permissions.py
  sandbox.py
  prompt_injection.py
  adversary_reviewer.py
  extension_allowlist.py
  ignore_rules.py
```

---

## 14. Final Checklist Before Publishing

Before pushing your adapted CLI publicly:

* [ ] Your repo has `LICENSE`.
* [ ] Your repo uses Apache-2.0 or another compatible strategy.
* [ ] Your repo has `NOTICE`.
* [ ] Your repo has `THIRD_PARTY_NOTICES.md`.
* [ ] Your README credits `aaif-goose/goose`.
* [ ] Modified files have prominent change notices.
* [ ] Original copyright/SPDX/license headers are preserved.
* [ ] You removed Goose / AAIF / Linux Foundation / Block branding from your own product identity.
* [ ] You documented copied/adapted areas in a plunder map.
* [ ] You tested each adapted subsystem.
* [ ] You understand every copied dependency.
* [ ] Permission modes are safe by default.
* [ ] Autonomous mode is explicit, not silent.
* [ ] Tool permissions are configurable.
* [ ] Extension allowlists are supported.
* [ ] Recipes are versioned.
* [ ] Provider configs avoid hardcoded secrets.
* [ ] Telemetry is disabled, removed, or made explicit.
* [ ] Desktop/UI branding assets are replaced if copied.
* [ ] Security-sensitive behavior is reviewed before release.

---

## 15. Clean Rule

```text
Copy the architecture.
Respect the license.
Preserve attribution.
Mark your changes.
Do not steal the branding.
Rewrite provider-specific assumptions.
Treat autonomy as dangerous power.
Study recipes, MCP, providers, and permissions deeply.
```

goose is especially valuable because it is not merely a coding CLI. It is a **local agent platform**:

* desktop app
* CLI
* API
* Rust core
* TypeScript UI
* MCP extensions
* ACP interoperability
* provider abstraction
* custom distributions
* recipes
* subagents
* skills
* permission modes
* prompt templates
* project hints
* security layers
* sandboxing
* CI/CD workflows

For your own CLI project, the greatest treasure is probably:

```text
goose's extension ecosystem + recipe system + custom distribution architecture.
```

That is battle-tested steel for building your own Mythic Engineering agent platform.

[1]: https://github.com/aaif-goose/goose "GitHub - aaif-goose/goose: an open source, extensible AI agent that goes beyond code suggestions - install, execute, edit, and test with any LLM · GitHub"
[2]: https://goose-docs.ai/docs/goose-architecture/ "goose Architecture | goose | Your open source AI agent"
[3]: https://github.com/aaif-goose/goose/tree/main/crates "goose/crates at main · aaif-goose/goose · GitHub"
[4]: https://github.com/aaif-goose/goose/tree/main/ui "goose/ui at main · aaif-goose/goose · GitHub"
[5]: https://github.com/aaif-goose/goose/blob/main/CUSTOM_DISTROS.md "goose/CUSTOM_DISTROS.md at main · aaif-goose/goose · GitHub"
[6]: https://goose-docs.ai/docs/guides/goose-cli-commands/ "CLI Commands | goose | Your open source AI agent"
[7]: https://block.github.io/goose/docs/mcp/developer-mcp/ "Developer Extension | goose"
[8]: https://goose-docs.ai/docs/guides/goose-permissions/ "goose Permission Modes | goose | Your open source AI agent"
[9]: https://goose-docs.ai/docs/guides/recipes/?utm_source=chatgpt.com "Recipes | goose | Your open source AI agent"
[10]: https://goose-docs.ai/docs/guides/recipes/session-recipes/ "Reusable Recipes | goose | Your open source AI agent"
[11]: https://goose-docs.ai/docs/guides/subagents/?utm_source=chatgpt.com "Subagents | goose | Your open source AI agent"
[12]: https://goose-docs.ai/docs/guides/context-engineering/using-skills/?utm_source=chatgpt.com "Using Skills | goose | Your open source AI agent"
[13]: https://goose-docs.ai/docs/guides/context-engineering/using-goosehints/ "Providing Hints to goose | goose | Your open source AI agent"
[14]: https://goose-docs.ai/docs/guides/prompt-templates/?utm_source=chatgpt.com "Customizing Prompt Templates | Your open source AI agent"
[15]: https://goose-docs.ai/ "goose | Your open source AI agent"
[16]: https://goose-docs.ai/docs/guides/cli-providers/?utm_source=chatgpt.com "CLI Providers | goose | Your open source AI agent"
[17]: https://goose-docs.ai/docs/guides/security/ "Staying Safe with goose | goose | Your open source AI agent"
[18]: https://goose-docs.ai/docs/guides/sandbox?utm_source=chatgpt.com "macOS Sandbox for goose Desktop"
[19]: https://goose-docs.ai/docs/goose-architecture/error-handling?utm_source=chatgpt.com "Error Handling | goose | Your open source AI agent"
