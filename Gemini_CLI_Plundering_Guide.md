# Gemini CLI Plundering Guide

## Purpose

This guide explains how to lawfully study, reuse, adapt, and “plunder” useful architecture from **Google Gemini CLI** for your own Apache-2.0 CLI project.

Gemini CLI is Google’s open-source terminal AI agent. Its README describes it as an AI agent that brings Gemini directly into the terminal, with built-in support for codebase work, shell commands, file operations, web fetching, Google Search grounding, MCP integrations, checkpointing, and custom project context through `GEMINI.md`. :contentReference[oaicite:0]{index=0}

This guide is practical open-source hygiene, not legal advice.

---

# 1. Core Legal Position

## License Match

Gemini CLI is licensed under **Apache License 2.0**. Its README explicitly identifies the project as Apache-2.0 licensed, and the repo contains the Apache-2.0 `LICENSE` file. :contentReference[oaicite:1]{index=1}

Apache-2.0 allows you to reproduce, modify, prepare derivative works from, and distribute the work in source or object form, as long as you follow the redistribution conditions. :contentReference[oaicite:2]{index=2}

In plain Viking terms:

> Take the useful steel.  
> Keep the maker’s mark.  
> Forge your own blade.

---

# 2. Required Source Links

Use these as your canonical references.

## Main Project Links

- **Gemini CLI GitHub Repository** — main source repo. :contentReference[oaicite:3]{index=3}
- **Gemini CLI README** — project overview, install options, feature list, auth options, and docs index. :contentReference[oaicite:4]{index=4}
- **Apache-2.0 LICENSE** — license terms and redistribution obligations. :contentReference[oaicite:5]{index=5}
- **Gemini CLI Documentation Site** — linked from the README as the main documentation hub. :contentReference[oaicite:6]{index=6}
- **CLI Command Reference** — commands, flags, interactive/non-interactive patterns, resume behavior, update command, extension command, and MCP command. :contentReference[oaicite:7]{index=7}
- **Configuration Reference** — config layers, settings files, schema, environment variables, and command-line override precedence. :contentReference[oaicite:8]{index=8}
- **Settings Command Docs** — `/settings`, user settings, workspace settings, approval modes, UI, keybindings, and accessibility configuration. :contentReference[oaicite:9]{index=9}
- **MCP Server Docs** — MCP server config, transports, resources, trust settings, tool filtering, and environment-variable expansion. :contentReference[oaicite:10]{index=10}
- **Custom Commands Docs** — reusable prompt-command system using global and project-local command folders. :contentReference[oaicite:11]{index=11}
- **Sandboxing Docs** — safety boundary for shell commands and file modifications. :contentReference[oaicite:12]{index=12}
- **GitHub Action Integration** — README links Gemini CLI into GitHub workflows for PR reviews, issue triage, mentions, scheduled workflows, and custom automation. :contentReference[oaicite:13]{index=13}

---

# 3. Core Apache-2.0 Duties

## 3.1 Keep the License

Your project should include:

```text
LICENSE
````

That file should contain Apache License 2.0.

Apache-2.0 requires redistributed derivative works to provide recipients with a copy of the license. ([GitHub][1])

---

## 3.2 Mark Modified Files

Apache-2.0 requires modified files to carry prominent notices stating that you changed them. ([GitHub][1])

### TypeScript Header

```ts
// Portions adapted from Google Gemini CLI.
// Original project: google-gemini/gemini-cli.
// Modified by Volmarr / RuneForgeAI, 2026.
// Licensed under the Apache License, Version 2.0.
```

### Markdown Header

```md
<!--
Portions adapted from Google Gemini CLI.
Original project: google-gemini/gemini-cli.
Modified by Volmarr / RuneForgeAI, 2026.
Licensed under the Apache License, Version 2.0.
-->
```

### JSON/Config Note

JSON does not allow comments, so document attribution in `NOTICE`, `THIRD_PARTY_NOTICES.md`, or adjacent docs.

---

## 3.3 Preserve Attribution Notices

Apache-2.0 requires you to retain copyright, patent, trademark, and attribution notices from the source form of the work, excluding notices that do not apply to the derivative portion you used. ([GitHub][1])

Suggested attribution section:

```md
## Third-Party Attribution

This project includes or adapts selected portions of Google Gemini CLI.

Gemini CLI  
Copyright Google and contributors  
Licensed under the Apache License, Version 2.0.

This project is independent and is not affiliated with, endorsed by, or sponsored by Google.
```

---

## 3.4 Do Not Steal Branding

Apache-2.0 does **not** grant permission to use the licensor’s trade names, trademarks, service marks, or product names except for reasonable attribution. ([GitHub][1])

Safe wording:

```md
This project includes code adapted from Google Gemini CLI.
```

Unsafe wording:

```md
This is the official Google Gemini CLI.
```

Avoid branding your project as:

* Gemini CLI Pro
* Official Gemini Agent
* Google Gemini Fork
* Google CLI Agent
* Gemini Code Assistant

Use their name only for attribution.

---

# 4. Recommended Repo Files

Your project should include:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/GEMINI_CLI_PLUNDER_GUIDE.md
docs/plunder/GEMINI_CLI_PLUNDER_MAP.md
```

Even if the upstream root listing does not show a root `NOTICE` file, keeping your own third-party notice file is clean and wise for a project that intentionally adapts external code. The root repo listing shows the Apache-2.0 license and major project files such as `README.md`, `GEMINI.md`, `SECURITY.md`, `Makefile`, `packages`, `docs`, `schemas`, `integration-tests`, `memory-tests`, `perf-tests`, and `evals`. ([GitHub][2])

---

# 5. Suggested `NOTICE`

```md
# NOTICE

[Your CLI Project Name]

Copyright 2026 Volmarr / RuneForgeAI

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected portions of software from:

## Google Gemini CLI

Project: Gemini CLI  
Repository: google-gemini/gemini-cli  
License: Apache License 2.0

Gemini CLI is an open-source AI agent for bringing Gemini into the terminal.

This project is independent and is not affiliated with, endorsed by, or sponsored by Google.
```

---

# 6. Suggested `THIRD_PARTY_NOTICES.md`

```md
# Third-Party Notices

This project includes or adapts material from third-party open-source projects.

## Google Gemini CLI

Project: Gemini CLI  
Repository: google-gemini/gemini-cli  
License: Apache License 2.0  

Usage:

This project may include or adapt selected portions of Google Gemini CLI, especially architectural patterns related to:

- CLI command structure
- Interactive terminal UI
- Non-interactive execution
- MCP server integration
- Settings and configuration layering
- Custom command discovery
- Context files
- Agent/subagent structure
- Sandboxing
- Policy handling
- Tool registry structure
- Patch handling
- Checkpointing/session recovery
- Testing and evaluation structure

This project is independent and is not affiliated with, endorsed by, or sponsored by Google.
```

---

# 7. Repo Structure Worth Studying

Gemini CLI is a TypeScript/Node-based monorepo. The top-level repo includes `docs`, `evals`, `integration-tests`, `memory-tests`, `packages`, `perf-tests`, `schemas`, `scripts`, `sea`, `third_party/get-ripgrep`, and `tools/gemini-cli-bot`. ([GitHub][2])

The `packages` folder contains:

```text
packages/
  a2a-server/
  cli/
  core/
  devtools/
  sdk/
  test-utils/
  vscode-ide-companion/
```

That package layout is useful because it separates the terminal application from the agent core, SDK, test utilities, devtools, and IDE companion behavior. ([GitHub][3])

---

# 8. Highest-Value Plunder Targets

## 8.1 `packages/core`

This is probably the richest area to study.

The `packages/core/src` tree includes folders for agent behavior, agents, billing, code assist, commands, config, confirmation bus, context, core logic, fallback, hooks, IDE integration, MCP, output, policy, prompts, resources, routing, safety, sandboxing, scheduler, services, skills, telemetry, tools, utilities, and voice. ([GitHub][4])

Likely useful targets:

| Upstream Area                        | Why It Is Interesting                               |
| ------------------------------------ | --------------------------------------------------- |
| `packages/core/src/agent`            | Main agent execution logic.                         |
| `packages/core/src/agents`           | Local/remote subagent architecture.                 |
| `packages/core/src/config`           | Core configuration loading and validation.          |
| `packages/core/src/context`          | Context construction and project memory behavior.   |
| `packages/core/src/confirmation-bus` | Tool confirmation / approval signaling.             |
| `packages/core/src/hooks`            | Lifecycle hooks and event-style extension points.   |
| `packages/core/src/mcp`              | MCP client integration and tool/resource discovery. |
| `packages/core/src/policy`           | Fine-grained execution policy concepts.             |
| `packages/core/src/prompts`          | System prompts and prompt assembly.                 |
| `packages/core/src/resources`        | External/contextual resource handling.              |
| `packages/core/src/routing`          | Model/tool/agent routing concepts.                  |
| `packages/core/src/safety`           | Safety checks and boundary logic.                   |
| `packages/core/src/sandbox`          | Sandboxed command/file-operation design.            |
| `packages/core/src/scheduler`        | Task scheduling / orchestration patterns.           |
| `packages/core/src/skills`           | Skill extraction, creation, and reuse system.       |
| `packages/core/src/tools`            | Tool registry and tool execution patterns.          |
| `packages/core/src/telemetry`        | Observability and event measurement.                |

For your CLI, this maps directly to a strong **agent core / tool law / policy engine / skill system**.

---

## 8.2 `packages/cli`

This is the terminal-facing layer.

The `packages/cli/src` tree includes `acp`, `commands`, `config`, `core`, `integration-tests`, `patches`, `services`, `ui`, `utils`, plus interactive and non-interactive CLI entry files. ([GitHub][5])

Likely useful targets:

| Upstream Area                                       | Why It Is Interesting                                |
| --------------------------------------------------- | ---------------------------------------------------- |
| `packages/cli/src/ui`                               | Terminal UI components, rendering, interaction flow. |
| `packages/cli/src/commands`                         | Slash commands and CLI meta-command structure.       |
| `packages/cli/src/nonInteractiveCli.ts`             | Scriptable one-shot execution mode.                  |
| `packages/cli/src/nonInteractiveCliAgentSession.ts` | Non-interactive session handling.                    |
| `packages/cli/src/interactiveCli.tsx`               | Interactive terminal session behavior.               |
| `packages/cli/src/patches`                          | Patch handling and user-facing edit flow.            |
| `packages/cli/src/acp`                              | Agent Client Protocol / IDE bridge patterns.         |
| `packages/cli/src/config`                           | CLI-side config assembly.                            |
| `packages/cli/src/services`                         | Terminal app services.                               |

For your own CLI, this is where you steal the **shape** of the terminal experience: command router, TUI flow, patch display, non-interactive execution, and approval UX.

---

## 8.3 `GEMINI.md` Context System

Gemini CLI supports custom context files named `GEMINI.md` to tailor behavior for a project. The README lists `GEMINI.md` under advanced capabilities and docs. ([GitHub][2])

This is extremely aligned with your Mythic Engineering style.

Plunder concept:

```text
GEMINI.md       -> MYTHIC.md or AGENTS.md
.gemini/        -> .mythic/
.gemini/commands -> .mythic/commands
.gemini/agents   -> .mythic/agents
```

Suggested adaptation:

```md
# MYTHIC.md

## Project Law

This project follows Mythic Engineering.

All agents must obey:

- DOMAIN_MAP.md
- ARCHITECTURE.md
- INTERFACE.md
- README.md
- docs/architecture/*
- docs/protocols/*

## Agent Roles

- Architect: owns boundaries and structure.
- Forge Worker: owns implementation.
- Auditor: owns defects and risk.
- Scribe: owns documentation.
- Cartographer: owns repo maps and file knowledge.
```

---

## 8.4 Custom Commands

Gemini CLI custom commands let users save reusable prompts as shortcuts. They can be global under `~/.gemini/commands/` or project-local under `<project>/.gemini/commands/`, with project-local commands shareable in version control. ([Gemini CLI][6])

This is very plunder-worthy.

Suggested adaptation:

```text
.mythic/commands/
  architecture-audit.md
  refactor-plan.md
  bug-hunt.md
  summarize-module.md
  update-docs.md
  create-skill.md
```

Example command file:

```md
# architecture-audit

Act as The Architect.

Audit this repository for:

- Boundary violations
- Duplicate ownership
- Circular dependencies
- Missing interface docs
- Outdated architecture docs
- Unsafe coupling

Return:

1. Findings
2. Risk level
3. Recommended refactor plan
4. Files that must be updated
```

---

## 8.5 MCP Integration

Gemini CLI’s MCP system is one of the best architecture targets. The docs say it discovers configured MCP servers from `settings.json`, connects using Stdio, SSE, or Streamable HTTP, fetches tool definitions, validates schemas, registers tools, resolves conflicts, and can discover MCP resources. ([GitHub][7])

MCP server configs support command/url/httpUrl, args, env, cwd, timeout, trust, and includeTools. Environment variables can be referenced from MCP config without hardcoding secrets. ([GitHub][7])

Suggested adaptation:

```json
{
  "mcp": {
    "allowed": ["local-docs", "github", "norse-lore"],
    "excluded": ["experimental-danger-zone"]
  },
  "mcpServers": {
    "local-docs": {
      "command": "python",
      "args": ["-m", "mythic_docs_mcp"],
      "cwd": "./tools/mcp/local-docs",
      "timeout": 30000,
      "trust": false,
      "includeTools": ["search_docs", "read_doc"]
    },
    "github": {
      "httpUrl": "https://example.com/mcp/github",
      "headers": {
        "Authorization": "Bearer $GITHUB_TOKEN"
      },
      "trust": false
    }
  }
}
```

Plunder principle:

> Tool access should be discoverable, configurable, filterable, and trust-scoped.

---

## 8.6 Configuration Layering

Gemini CLI has a strong configuration hierarchy: defaults, system defaults, user settings, project settings, system override settings, environment variables, and command-line arguments. Higher layers override lower layers. ([GitHub][8])

This is exactly the kind of structure a serious CLI needs.

Suggested Mythic CLI config model:

```text
1. Built-in defaults
2. System defaults
3. User settings
4. Project settings
5. Agent profile settings
6. Environment variables
7. Command-line arguments
```

Example:

```json
{
  "general": {
    "defaultApprovalMode": "default",
    "vimMode": false
  },
  "models": {
    "architect": {
      "provider": "openrouter",
      "model": "anthropic/claude-opus-4.5"
    },
    "forge_worker": {
      "provider": "openrouter",
      "model": "qwen/qwen3.5-coder"
    }
  },
  "sandbox": {
    "enabled": true,
    "mode": "workspace-write"
  }
}
```

---

## 8.7 Approval Modes

Gemini CLI settings include a default approval mode. The docs list `default`, `auto_edit`, and `plan`, while YOLO mode can only be enabled through command-line flags. ([GitHub][9])

This is a good safety pattern to copy.

Suggested adaptation:

```md
## Approval Modes

| Mode | Behavior |
|---|---|
| `plan` | Read-only. Agent may inspect and propose but not edit. |
| `default` | Ask before tool execution or risky edits. |
| `auto_edit` | Auto-approve safe edit tools, ask for shell/risky tools. |
| `yolo` | Auto-approve everything. CLI-only. Must be explicit. |
```

Important design law:

> Dangerous modes should never be silently enabled by project config.

---

## 8.8 Sandboxing

Gemini CLI’s sandboxing docs describe sandboxing as a way to isolate risky operations such as shell commands and file modifications from the host system. ([Gemini CLI][10])

This is worth studying even if you do not copy implementation directly.

Suggested adaptation:

```md
# Sandboxing Law

The agent may reason freely.

The agent may only act within approved boundaries.

Sandbox policy controls:

- Which directories can be read.
- Which directories can be written.
- Which commands can run.
- Which network actions are allowed.
- Which tools require confirmation.
- Which tools are forbidden.
```

---

## 8.9 CLI Command UX

Gemini CLI supports interactive REPL usage, non-interactive prompting with `-p`, piping content into the CLI, continuing interactively with `-i`, resuming sessions with `-r`, updating the tool, managing extensions, and managing MCP servers. ([GitHub][11])

Plunder-worthy command patterns:

```bash
mythic
mythic -p "summarize README.md"
cat logs.txt | mythic
mythic -i "explain this project"
mythic -r latest
mythic -r latest "continue the refactor"
mythic update
mythic extensions
mythic mcp
```

The big lesson:

> A serious CLI should support both ritual conversation and scriptable automation.

---

## 8.10 Structured Output

Gemini CLI README documents non-interactive output formats including normal text, JSON output, and stream-json events for long-running operations. ([GitHub][2])

This is very worth copying.

Suggested adaptation:

```bash
mythic -p "audit this repo" --output-format json
mythic -p "run tests and fix failures" --output-format stream-json
```

Useful for:

* CI workflows
* GitHub Actions
* agent orchestration
* logs
* dashboards
* external controllers
* long-running task monitoring

---

## 8.11 Checkpointing and Session Resume

Gemini CLI README lists conversation checkpointing as an advanced capability, and the CLI command reference includes session resume commands using `-r latest` or `-r <session-id>`. ([GitHub][2])

This is important for your continuity-driven workflow.

Suggested adaptation:

```text
.mythic/state/
  sessions/
  checkpoints/
  rollouts/
  traces/
```

Design principle:

```md
## Checkpoint Law

Every long-running agent session should be recoverable.

A failed terminal, crashed model call, or exhausted token session should not destroy the working thread.
```

---

## 8.12 Subagents

Gemini CLI’s command reference includes `/agents` commands for listing, reloading, enabling, and discovering local and remote agents. It looks in `~/.gemini/agents` and `.gemini/agents`. ([GitHub][12])

This is extremely relevant to your named Vibe Coding roles.

Suggested adaptation:

```text
.mythic/agents/
  architect.md
  forge-worker.md
  auditor.md
  cartographer.md
  scribe.md
  seer.md
  warden.md
```

Example:

```md
# Architect

Role: The Dominant Designer

Owns:

- Domain boundaries
- Architecture maps
- Refactor strategy
- Module ownership
- Long-range coherence

Never owns:

- Random implementation churn
- Unreviewed rewrites
- Silent behavior changes
```

---

## 8.13 Skills System

The current repo structure includes `packages/core/src/skills`, and recent release notes mention skill extraction, skill creator integration, and skill-related tests. ([GitHub][4])

This is a major plunder target.

Suggested adaptation:

```text
.mythic/skills/
  skill-creator/
    SKILL.md
  architecture-audit/
    SKILL.md
  patch-forge/
    SKILL.md
  repo-cartography/
    SKILL.md
  continuity-recovery/
    SKILL.md
  doc-scribe/
    SKILL.md
```

Design law:

```md
## Skill Law

A skill is not just a prompt.

A skill should include:

- Purpose
- Invocation conditions
- Inputs
- Outputs
- Safety limits
- Required files
- Expected format
- Failure behavior
```

---

## 8.14 Patch Handling

The CLI source tree includes a `patches` area under `packages/cli/src`. ([GitHub][5])

This is worth studying because coding agents need safe, reviewable edits.

Suggested adaptation:

```md
# Patch Forge Law

All file edits should be:

- Previewable
- Reversible
- Diffable
- Testable
- Attribution-safe
- Protected against overwriting user work
```

---

## 8.15 Testing and Evaluation Structure

The root repo includes `integration-tests`, `memory-tests`, `perf-tests`, and `evals`; the package trees also include test setup and test utility areas. ([GitHub][2])

Worth plundering:

| Area                                 | Why It Matters                              |
| ------------------------------------ | ------------------------------------------- |
| `integration-tests`                  | End-to-end behavior validation.             |
| `memory-tests`                       | Context and continuity validation.          |
| `perf-tests`                         | Performance and large-session behavior.     |
| `evals`                              | Agent quality and task behavior evaluation. |
| `packages/test-utils`                | Shared test scaffolding.                    |
| `packages/core/src/test-utils`       | Core-level test helpers.                    |
| `packages/cli/src/integration-tests` | CLI-specific integration testing.           |

For your project:

```text
tests/
  unit/
  integration/
  e2e/
  memory/
  perf/
  evals/
```

---

## 8.16 GitHub Action Pattern

Gemini CLI has a GitHub workflow integration path for automated PR reviews, issue triage, on-demand issue/PR assistance, scheduled workflows, and custom workflows. ([GitHub][2])

For your CLI project, this is worth turning into:

```yaml
name: Mythic CLI Repo Audit

on:
  pull_request:
  workflow_dispatch:

jobs:
  mythic-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Mythic CLI architecture audit
        run: mythic -p "Audit this PR for architecture drift" --output-format json
```

Potential plunder idea:

> A CLI is stronger when it can operate both as a local terminal companion and a CI/CD agent.

---

# 9. Suggested Plunder Priority

## Tier 1 — Load-Bearing Architecture

Study first:

```text
packages/core/src/agent
packages/core/src/agents
packages/core/src/config
packages/core/src/context
packages/core/src/tools
packages/core/src/mcp
packages/core/src/policy
packages/core/src/sandbox
packages/core/src/safety
packages/cli/src/interactiveCli.tsx
packages/cli/src/nonInteractiveCli.ts
packages/cli/src/ui
packages/cli/src/commands
```

---

## Tier 2 — Mythic Engineering Power Systems

Study next:

```text
packages/core/src/skills
packages/core/src/hooks
packages/core/src/scheduler
packages/core/src/routing
packages/core/src/prompts
packages/core/src/resources
packages/core/src/confirmation-bus
packages/cli/src/patches
packages/cli/src/acp
packages/cli/src/nonInteractiveCliAgentSession.ts
```

---

## Tier 3 — Support Infrastructure

Study later:

```text
docs/
schemas/
evals/
integration-tests/
memory-tests/
perf-tests/
packages/sdk/
packages/test-utils/
packages/devtools/
packages/vscode-ide-companion/
tools/gemini-cli-bot/
sea/
third_party/get-ripgrep/
```

---

# 10. What Not To Plunder Blindly

Be careful with:

* Google branding
* Gemini branding
* Google auth flows
* Code Assist-specific behavior
* Vertex AI-specific assumptions
* Billing-specific code
* Telemetry defaults
* Product-specific prompt wording
* Terms/privacy-related integration
* Any endpoint tied to Google-owned infrastructure
* Anything you do not understand well enough to maintain

Better rule:

> Copy architecture aggressively.
> Copy implementation selectively.
> Rewrite service-specific integrations.

---

# 11. Recommended Local Study Workflow

## Step 1: Clone Upstream

```bash
git clone https://github.com/google-gemini/gemini-cli.git external/google-gemini-cli
cd external/google-gemini-cli
```

## Step 2: Inspect Structure

```bash
find packages -maxdepth 3 -type d | sort
find docs -maxdepth 2 -type f | sort
```

## Step 3: Create a Plunder Map

Create:

```text
docs/plunder/GEMINI_CLI_PLUNDER_MAP.md
```

Template:

```md
# Gemini CLI Plunder Map

## Upstream

Project: Google Gemini CLI  
Repository: google-gemini/gemini-cli  
License: Apache-2.0  

## Targeted Areas

| Upstream Path | Local Target | Status | Notes |
|---|---|---|---|
| packages/core/src/tools | mythic_cli/tools | studying | Tool registry and execution model |
| packages/core/src/mcp | mythic_cli/mcp | planned | MCP server integration |
| packages/core/src/skills | .mythic/skills | planned | Skill packet system |
| packages/cli/src/ui | mythic_cli/tui | studying | Terminal UI patterns |
| packages/cli/src/patches | mythic_cli/patching | planned | Patch preview/apply layer |
| packages/core/src/sandbox | mythic_cli/sandbox | planned | Execution boundary model |
| docs/reference/configuration.md | docs/architecture/CONFIG_LAW.md | adapted | Config precedence model |
```

## Step 4: Copy One Subsystem at a Time

```bash
git checkout -b adapt-gemini-cli-mcp-patterns
```

## Step 5: Commit With Attribution

```bash
git commit -m "Adapt MCP architecture patterns from Google Gemini CLI

- Adds Apache-2.0 attribution
- Marks modified files
- Updates THIRD_PARTY_NOTICES.md
- Reworks config shape for Mythic CLI"
```

---

# 12. README Attribution Template

```md
## Third-Party Attribution

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected architectural patterns and code from Google Gemini CLI, also licensed under Apache-2.0.

Gemini CLI is an open-source AI terminal agent developed by Google and the open-source community.

This project is independent and is not affiliated with, endorsed by, or sponsored by Google.
```

---

# 13. Mythic CLI Adaptation Map

## 13.1 Agent Core

Gemini inspiration:

```text
packages/core/src/agent
packages/core/src/agents
packages/core/src/scheduler
packages/core/src/routing
```

Mythic adaptation:

```text
mythic_cli/agent_core/
  agent_loop.py
  role_router.py
  subagents.py
  scheduler.py
```

---

## 13.2 Tool Law

Gemini inspiration:

```text
packages/core/src/tools
packages/core/src/confirmation-bus
packages/core/src/policy
packages/core/src/safety
```

Mythic adaptation:

```text
mythic_cli/tools/
  registry.py
  tool_call.py
  approval.py
  policy.py
  safety.py
```

---

## 13.3 MCP Gate

Gemini inspiration:

```text
packages/core/src/mcp
docs/tools/mcp-server.md
```

Mythic adaptation:

```text
mythic_cli/mcp/
  client.py
  server_config.py
  resource_reader.py
  tool_bridge.py
```

---

## 13.4 Context and Memory

Gemini inspiration:

```text
GEMINI.md
packages/core/src/context
memory-tests/
```

Mythic adaptation:

```text
MYTHIC.md
AGENTS.md
.mythic/memory/
tests/memory/
```

---

## 13.5 Skill Packets

Gemini inspiration:

```text
packages/core/src/skills
docs/cli/tutorials/skills-getting-started
```

Mythic adaptation:

```text
.mythic/skills/
  architecture-audit/
  patch-forge/
  continuity-recovery/
  doc-scribe/
```

---

## 13.6 Terminal UI

Gemini inspiration:

```text
packages/cli/src/ui
packages/cli/src/interactiveCli.tsx
packages/cli/src/nonInteractiveCli.ts
```

Mythic adaptation:

```text
mythic_cli/tui/
  app.py
  components/
  approval_panel.py
  diff_view.py
  session_view.py
```

---

# 14. Final Checklist Before Publishing

Before pushing your adapted CLI publicly:

* [ ] Your repo has `LICENSE`.
* [ ] Your repo uses Apache-2.0 or a compatible strategy.
* [ ] Your repo has `THIRD_PARTY_NOTICES.md`.
* [ ] Your README credits Google Gemini CLI where relevant.
* [ ] Modified files have prominent change notices.
* [ ] You removed Google/Gemini branding from your own product identity.
* [ ] You did not copy Google-specific auth or billing logic blindly.
* [ ] You did not imply official affiliation.
* [ ] You documented copied/adapted areas in a plunder map.
* [ ] You tested each adapted subsystem.
* [ ] You can explain every copied dependency.
* [ ] You preserved relevant copyright and attribution notices.
* [ ] Dangerous modes cannot be enabled silently by project config.
* [ ] MCP tools are trust-scoped and filterable.
* [ ] Patch handling protects user work.

---

# 15. Clean Rule

```text
Copy the architecture.
Respect the license.
Preserve attribution.
Mark your changes.
Do not steal the branding.
Rewrite service-specific Google integrations.
Keep the terminal-agent wisdom.
```

Gemini CLI is especially valuable as a **TypeScript terminal-agent architecture reference**: config layering, MCP, custom commands, project context, subagents, skills, sandboxing, structured output, checkpointing, GitHub automation, and a serious interactive/non-interactive CLI split.

The real treasure is not one file.

The treasure is the pattern language.

```
::contentReference[oaicite:38]{index=38}
```

[1]: https://github.com/google-gemini/gemini-cli/blob/main/LICENSE "gemini-cli/LICENSE at main · google-gemini/gemini-cli · GitHub"
[2]: https://github.com/google-gemini/gemini-cli "GitHub - google-gemini/gemini-cli: An open-source AI agent that brings the power of Gemini directly into your terminal. · GitHub"
[3]: https://github.com/google-gemini/gemini-cli/tree/main/packages "gemini-cli/packages at main · google-gemini/gemini-cli · GitHub"
[4]: https://github.com/google-gemini/gemini-cli/tree/main/packages/core/src "gemini-cli/packages/core/src at main · google-gemini/gemini-cli · GitHub"
[5]: https://github.com/google-gemini/gemini-cli/tree/main/packages/cli/src "gemini-cli/packages/cli/src at main · google-gemini/gemini-cli · GitHub"
[6]: https://geminicli.com/docs/cli/custom-commands/ "Custom commands | Gemini CLI"
[7]: https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md "gemini-cli/docs/tools/mcp-server.md at main · google-gemini/gemini-cli · GitHub"
[8]: https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/configuration.md "gemini-cli/docs/reference/configuration.md at main · google-gemini/gemini-cli · GitHub"
[9]: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/settings.md "gemini-cli/docs/cli/settings.md at main · google-gemini/gemini-cli · GitHub"
[10]: https://geminicli.com/docs/cli/sandbox/ "Sandboxing in Gemini CLI | Gemini CLI"
[11]: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/cli-reference.md "gemini-cli/docs/cli/cli-reference.md at main · google-gemini/gemini-cli · GitHub"
[12]: https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/commands.md "gemini-cli/docs/reference/commands.md at main · google-gemini/gemini-cli · GitHub"
