# Mistral Vibe Plundering Guide

## Purpose

This guide explains how to lawfully study, reuse, adapt, and “plunder” useful architecture from **Mistral Vibe** for your own Apache-2.0 CLI project.

Small correction: this is **Mistral AI’s Mistral Vibe**, not an OpenAI project. Mistral Vibe is an open-source, terminal-native coding agent powered by Mistral/Devstral models. It works through a conversational CLI, scans project structure and Git state, maintains multi-file context, executes shell commands, supports custom agents/skills, integrates with IDEs through ACP, and can run with local models. ([Mistral AI][1])

This is practical open-source hygiene, not legal advice.

---

## 1. Core Legal Position

Mistral Vibe is released under **Apache License 2.0**. The official docs say the code is available on GitHub under Apache 2.0, and the repo exposes the Apache-2.0 `LICENSE` file. ([Mistral AI][2])

Under Apache-2.0, you can generally:

* Copy code.
* Modify code.
* Redistribute modified versions.
* Merge useful portions into your own Apache-2.0 project.
* Use it commercially.
* Build your own CLI system using adapted pieces.

But you must preserve required license/copyright notices, mark modified files, and avoid implying that your project is official Mistral branding.

> Take the useful steel.
> Keep the maker’s mark.
> Forge your own blade.

---

## 2. Required Source Links

Use these as canonical upstream references in your own repo docs.

### Main Links

* [Mistral Vibe GitHub Repository](https://github.com/mistralai/mistral-vibe)
* [Mistral Vibe LICENSE](https://github.com/mistralai/mistral-vibe/blob/main/LICENSE)
* [Mistral Vibe Docs Overview](https://docs.mistral.ai/mistral-vibe/overview)
* [CLI Introduction](https://docs.mistral.ai/mistral-vibe/terminal)
* [Installation](https://docs.mistral.ai/mistral-vibe/introduction/install)
* [Quickstart](https://docs.mistral.ai/mistral-vibe/terminal/quickstart)
* [Configuration](https://docs.mistral.ai/mistral-vibe/terminal/configuration)
* [Agents & Skills](https://docs.mistral.ai/mistral-vibe/agents-skills)
* [Offline / Local](https://docs.mistral.ai/mistral-vibe/local)
* [Coding / FIM API Page](https://docs.mistral.ai/mistral-vibe/using-fim-api)
* [Mistral Vibe Product Page](https://mistral.ai/products/vibe)
* [Devstral 2 and Vibe CLI Announcement](https://mistral.ai/news/devstral-2-vibe-cli)
* [Mistral Vibe 2.0 Announcement](https://mistral.ai/news/mistral-vibe-2-0)
* [CHANGELOG](https://github.com/mistralai/mistral-vibe/blob/main/CHANGELOG.md)
* [CONTRIBUTING](https://github.com/mistralai/mistral-vibe/blob/main/CONTRIBUTING.md)

---

## 3. Core Apache-2.0 Duties

### 3.1 Keep the License

Your project should include:

```text
LICENSE
```

Use Apache License 2.0 if your project is already Apache-2.0.

---

### 3.2 Preserve Notices

When copying files or meaningful chunks from Mistral Vibe:

* Preserve copyright headers.
* Preserve SPDX/license comments if present.
* Preserve attribution comments.
* Do not claim copied code was written entirely from scratch.
* Do not remove references to Mistral Vibe upstream authorship.

Suggested Python header:

```python
# Portions adapted from mistralai/mistral-vibe.
# Upstream project: Mistral Vibe, licensed under Apache License 2.0.
# Modified by Volmarr / RuneForgeAI, 2026.
# Licensed under the Apache License, Version 2.0.
```

Suggested Markdown header:

```md
<!--
Portions adapted from mistralai/mistral-vibe.
Upstream project: Mistral Vibe, licensed under Apache License 2.0.
Modified by Volmarr / RuneForgeAI, 2026.
Licensed under the Apache License, Version 2.0.
-->
```

---

### 3.3 Add Third-Party Notices

Recommended repo files:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/MISTRAL_VIBE_PLUNDER_GUIDE.md
docs/plunder/MISTRAL_VIBE_PLUNDER_MAP.md
```

Suggested `NOTICE`:

```md
# NOTICE

[Your CLI Project Name]

Copyright 2026 Volmarr / RuneForgeAI

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected portions of software from:

## Mistral Vibe

Project: Mistral Vibe  
Repository: mistralai/mistral-vibe  
License: Apache License 2.0

Mistral Vibe is an open-source terminal-native coding assistant from Mistral AI.

This project is independent and is not affiliated with, endorsed by, or sponsored by Mistral AI or the Mistral Vibe project.
```

Suggested `THIRD_PARTY_NOTICES.md`:

```md
# Third-Party Notices

This project includes or adapts material from third-party open-source projects.

## Mistral Vibe

Project: Mistral Vibe  
Repository: mistralai/mistral-vibe  
License: Apache License 2.0  

Usage:

This project may include or adapt selected portions of Mistral Vibe, especially architectural patterns related to:

- Python terminal AI agent architecture
- CLI/core package separation
- Textual-style terminal UI
- Agent loop design
- Programmatic mode
- Tool registry and permissions
- Built-in tools
- MCP server integration
- ACP integration
- Agent profiles
- Subagents
- Agent Skills
- Project-aware context
- Git/file-structure scanning
- Session logging/resume
- Config.toml model/provider system
- Trusted folder system
- Local/offline model support
- Voice mode
- Notifications
- Telemetry toggles

This project is independent and is not affiliated with, endorsed by, or sponsored by Mistral AI or the Mistral Vibe project.
```

---

## 4. Branding Warning

Apache-2.0 lets you reuse code. It does **not** let you steal the project’s identity.

Safe wording:

```md
This project includes code adapted from mistralai/mistral-vibe.
```

Unsafe wording:

```md
This is the official Mistral Vibe CLI.
```

Avoid naming your project:

* Official Mistral Vibe Fork
* Mistral Vibe Pro
* Mistral Code Official CLI
* Devstral Official Agent
* Mistral Mythic Edition

Use “Mistral,” “Mistral Vibe,” and “Devstral” only for attribution, compatibility notes, or model/provider documentation.

---

## 5. What Mistral Vibe Is Architecturally

Mistral Vibe is a **Python CLI coding agent**. It can be installed as a Python package through tools like `uv` or `pip`, and the README shows the main package directory as `vibe/` with subpackages for `acp`, `cli`, `core`, and `setup`. ([GitHub][3])

High-level shape:

```text
vibe/
  acp/
  cli/
  core/
  setup/
```

For your own Mythic CLI, that maps cleanly to:

```text
mythic_cli/
  acp/
  cli/
  core/
  setup/
```

Design law:

```md
## Interface/Core Law

The terminal interface should not own the whole agent.

Separate:

- CLI / TUI
- Agent core
- Tool layer
- Config layer
- Session layer
- Protocol bridges
```

---

## 6. Repo Structure Worth Studying

The most important root-level files and folders visible in the repo include:

```text
vibe/
tests/
CHANGELOG.md
CONTRIBUTING.md
LICENSE
README.md
action.yml
flake.nix
pyproject.toml
uv.lock
vibe-acp.spec
```

The README and root file listing show it is packaged as a Python project, with `pyproject.toml`, `uv.lock`, Nix files, GitHub Action metadata, and an ACP spec file. ([GitHub][3])

---

## 7. Highest-Value Plunder Targets

## 7.1 `vibe/core/agent_loop.py`

This is probably one of the richest targets.

The `vibe/core/` tree includes `agent_loop.py`, `programmatic.py`, `plan_session.py`, `middleware.py`, `system_prompt.py`, `output_formatters.py`, `tracing.py`, and other core runtime files. ([GitHub][4])

Likely value:

* Main agent turn loop.
* Tool-call orchestration.
* Message flow.
* Plan/session behavior.
* Middleware hooks.
* Output formatting.
* Runtime tracing.
* System prompt assembly.

Mythic adaptation:

```text
mythic_cli/core/
  agent_loop.py
  middleware.py
  system_prompt.py
  plan_session.py
  output_formatters.py
  tracing.py
```

Design law:

```md
## Agent Loop Law

The agent loop owns:

- user input
- model calls
- tool-call detection
- approval flow
- tool execution
- result injection
- final response
- turn summaries
- session state updates
```

---

## 7.2 `vibe/cli/` — Terminal Interface

The `vibe/cli/` folder includes terminal-facing areas such as `autocompletion`, `textual_ui`, `turn_summary`, `update_notifier`, `voice_manager`, `cli.py`, `commands.py`, `entrypoint.py`, `history_manager.py`, `terminal_detect.py`, and more. ([GitHub][5])

Likely value:

| Upstream Area                 | Why It Is Interesting                    |
| ----------------------------- | ---------------------------------------- |
| `vibe/cli/cli.py`             | Main CLI entry behavior                  |
| `vibe/cli/entrypoint.py`      | Launch path                              |
| `vibe/cli/commands.py`        | Slash-command system                     |
| `vibe/cli/textual_ui/`        | Terminal UI architecture                 |
| `vibe/cli/autocompletion/`    | Slash and path autocomplete              |
| `vibe/cli/history_manager.py` | Persistent command/session input history |
| `vibe/cli/turn_summary/`      | Turn summary behavior                    |
| `vibe/cli/update_notifier/`   | Update notifications                     |
| `vibe/cli/voice_manager/`     | Voice input layer                        |
| `vibe/cli/terminal_detect.py` | Terminal capability detection            |

Mythic adaptation:

```text
mythic_cli/cli/
  entrypoint.py
  cli.py
  commands.py
  textual_ui/
  autocompletion/
  history_manager.py
  terminal_detect.py
```

Design law:

```md
## Terminal UX Law

A serious AI CLI should support:

- slash commands
- file-path autocomplete
- command history
- external editor input
- tool output toggle
- todo view
- debug console
- approval toggles
- session summaries
```

Mistral Vibe’s README specifically documents features like `@` file references, `!` shell commands, external editor editing, tool-output toggles, todo view toggles, debug console, and auto-approve toggling. ([GitHub][3])

---

## 7.3 `vibe/core/tools/` — Tool System

The `vibe/core/tools/` tree includes `base.py`, `manager.py`, `permissions.py`, `ui.py`, `arity.py`, `mcp_sampling.py`, and folders for `builtins`, `connectors`, and `mcp`. ([GitHub][6])

Likely value:

* Tool interface/base class.
* Tool manager.
* Permission model.
* Tool UI rendering.
* Arity/argument handling.
* MCP tool integration.
* Built-in tool registration.
* Connector layer.

Mythic adaptation:

```text
mythic_cli/tools/
  base.py
  manager.py
  permissions.py
  ui.py
  arity.py
  builtins/
  mcp/
  connectors/
```

Design law:

```md
## Tool Law

Tools should be:

- registered
- typed
- permission-scoped
- inspectable
- UI-renderable
- safe by default
- disable-able by pattern
- compatible with local and MCP tools
```

---

## 7.4 Built-In Tools

The `vibe/core/tools/builtins/` folder includes built-in tools such as `ask_user_question.py`, `bash.py`, `grep.py`, `read_file.py`, `search_replace.py`, `todo.py`, `task.py`, `webfetch.py`, `websearch.py`, and `write_file.py`. ([GitHub][7])

Likely value:

| Tool                | Why It Is Interesting            |
| ------------------- | -------------------------------- |
| `read_file`         | Safe context ingestion           |
| `write_file`        | File creation/overwrite flow     |
| `search_replace`    | Patch-like file editing          |
| `grep`              | Codebase search                  |
| `bash`              | Stateful shell command execution |
| `todo`              | Agent task tracking              |
| `task`              | Subagent delegation              |
| `ask_user_question` | Structured clarification UI      |
| `webfetch`          | URL context ingestion            |
| `websearch`         | Search integration               |
| `skill`             | Skill invocation / management    |
| `exit_plan_mode`    | Plan-to-execute transition       |

Mythic adaptation:

```text
mythic_cli/tools/builtins/
  read_file.py
  write_file.py
  search_replace.py
  grep.py
  bash.py
  todo.py
  task.py
  ask_user_question.py
  webfetch.py
  websearch.py
  skill.py
```

Design law:

```md
## Built-In Tool Law

The core built-in tools should cover:

- reading
- writing
- patching
- searching
- shell execution
- planning
- todo tracking
- subagent delegation
- user clarification
- web/context retrieval
```

---

## 7.5 Tool Permissions and Agent Profiles

Mistral Vibe includes built-in agent profiles:

| Agent          | Behavior                                                     |
| -------------- | ------------------------------------------------------------ |
| `default`      | Requires approval for tool executions                        |
| `plan`         | Read-only exploration and planning; auto-approves safe tools |
| `accept-edits` | Auto-approves file edits only                                |
| `auto-approve` | Auto-approves all tool executions                            |

The README describes these built-in profiles and warns that auto-approval should be used carefully. ([GitHub][3])

Mythic adaptation:

```text
plan
default
accept_edits
auto_approve
audit_only
forge_worker
architect
scribe
```

Example config:

```toml
[agents.architect]
active_model = "deep"
system_prompt_id = "architect"
disabled_tools = ["write_file", "search_replace", "bash"]

[agents.forge_worker]
active_model = "coder"
system_prompt_id = "forge_worker"
enabled_tools = ["read_file", "write_file", "search_replace", "grep", "bash"]

[tools.bash]
permission = "ask"

[tools.read_file]
permission = "always"
```

Design law:

```md
## Permission Law

The agent may think freely.

The agent may only act according to its active permission mode.

Read-only, edit-only, approval-required, and full-auto modes should be explicit and visible.
```

---

## 7.6 `ask_user_question` Tool

Mistral Vibe’s README documents a structured `ask_user_question` tool that lets the agent ask clarifying questions with selectable options and free-text fallback. ([GitHub][3])

This is very worth plundering.

Mythic adaptation:

```python
ask_user_question(
    questions=[
        {
            "question": "What kind of refactor do you want?",
            "options": [
                {"label": "Safety", "description": "Minimal low-risk changes"},
                {"label": "Architecture", "description": "Improve boundaries"},
                {"label": "Performance", "description": "Make it faster"},
            ],
        }
    ]
)
```

Design law:

```md
## Clarification Law

The agent should not always guess.

It should be able to ask structured questions when:

- intent is ambiguous
- risk is high
- multiple valid paths exist
- user preference matters
- destructive work is possible
```

---

## 7.7 Subagents and `task`

Mistral Vibe supports subagents through the `task` tool. Subagents run independently, perform specialized work, and return results as text to the main agent. ([GitHub][3])

Mythic adaptation:

```text
.mythic/agents/
  architect.toml
  forge-worker.toml
  auditor.toml
  cartographer.toml
  scribe.toml
  explorer.toml
```

Example:

```toml
agent_type = "subagent"
active_model = "fast"
system_prompt_id = "cartographer"

enabled_tools = ["read_file", "grep"]
disabled_tools = ["write_file", "search_replace", "bash"]

[tools.read_file]
permission = "always"

[tools.grep]
permission = "always"
```

Design law:

```md
## Subagent Law

Subagents should isolate context and responsibility.

Use them for:

- codebase exploration
- architecture review
- file summarization
- test analysis
- documentation review
- risk scanning

Do not let multiple subagents blindly mutate the same files in parallel.
```

---

## 7.8 Skills System

Mistral Vibe has a Skills system that can add tools, slash commands, and specialized behavior. The README says it follows the Agent Skills specification, uses `SKILL.md` with YAML frontmatter, supports user-invocable skills, and discovers skills from custom paths, `.agents/skills/`, project `.vibe/skills/`, and global `~/.vibe/skills/`. ([GitHub][3])

The source tree includes `vibe/core/skills/` with `manager.py`, `models.py`, `parser.py`, and built-in skills. ([GitHub][8])

Mythic adaptation:

```text
.mythic/skills/
  architecture-audit/
    SKILL.md
  patch-forge/
    SKILL.md
  repo-cartography/
    SKILL.md
  test-repair/
    SKILL.md
  docs-scribe/
    SKILL.md
```

Example:

```md
---
name: architecture-audit
description: Audit a repository for architectural drift, ownership confusion, stale docs, and unsafe coupling.
license: Apache-2.0
compatibility: Python 3.12+
user-invocable: true
allowed-tools:
  - read_file
  - grep
  - ask_user_question
---

# Architecture Audit Skill

## Purpose

Audit a codebase for structural drift.

## Process

1. Read DOMAIN_MAP.md.
2. Read ARCHITECTURE.md.
3. Inspect nearby README.md and INTERFACE.md files.
4. Identify boundary violations.
5. Return findings and a repair plan.

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

A skill is a reusable capability package.

It should define:

- name
- description
- allowed tools
- invocation conditions
- procedure
- output format
- examples
- safety limits
```

---

## 7.9 `config.toml` System

Mistral Vibe uses `config.toml`, checking first `./.vibe/config.toml` and then `~/.vibe/config.toml`. It also supports `~/.vibe/.env` for API keys, with environment variables taking precedence. ([Mistral AI][9])

It supports:

* API key config
* custom system prompts
* custom agent configs
* provider presets
* model presets
* MCP servers
* session management
* tool enable/disable patterns
* custom home directory through `VIBE_HOME`
* trusted folders
* update settings
* telemetry toggle

([Mistral AI][9])

Mythic adaptation:

```toml
active_model = "forge"
system_prompt_id = "mythic_default"
enable_telemetry = false
enable_auto_update = false
enable_notifications = true

skill_paths = [".mythic/skills"]

enabled_tools = ["read_file", "grep", "search_replace", "bash"]
disabled_tools = ["websearch"]

[[providers]]
name = "openrouter"
api_base = "https://openrouter.ai/api/v1"
api_key_env_var = "OPENROUTER_API_KEY"
api_style = "openai"
backend = "generic"

[[models]]
name = "qwen/qwen3.5-coder"
provider = "openrouter"
alias = "forge"
temperature = 0.2
input_price = 0.0
output_price = 0.0
```

Design law:

```md
## Config Law

A serious CLI should support:

- project config
- user config
- env-file secrets
- environment variable overrides
- model aliases
- provider presets
- agent profiles
- tool permissions
- skill paths
- MCP servers
- trusted folders
```

---

## 7.10 Provider and Model Presets

Mistral Vibe supports provider/model presets. The docs show an OpenRouter-style provider using an OpenAI-compatible API style, plus a model alias that can be selected from `/config`. ([Mistral AI][9])

Mythic adaptation:

```toml
[[providers]]
name = "lmstudio"
api_base = "http://localhost:1234/v1"
api_key_env_var = "LMSTUDIO_API_KEY"
api_style = "openai"
backend = "generic"

[[models]]
name = "local-model"
provider = "lmstudio"
alias = "local"
temperature = 0.3
input_price = 0.0
output_price = 0.0
```

Design law:

```md
## Provider Law

A provider should be declarative when possible.

Each provider should define:

- name
- API base URL
- API-key environment variable
- API style
- backend type
- supported model aliases
```

---

## 7.11 Offline / Local Model Support

Mistral Vibe supports local models and OpenAI-compatible local servers. The docs say Devstral can be deployed locally, recommend vLLM for Devstral Small 2, and note that compatible servers from vLLM, llama.cpp, LM Studio, Ollama, and others can be used. ([Mistral AI][10])

Mythic adaptation:

```toml
[[providers]]
name = "local"
api_base = "http://localhost:8080/v1"
api_key_env_var = "LOCAL_API_KEY"
api_style = "openai"
backend = "generic"

[[models]]
name = "local-devstral"
provider = "local"
alias = "local"
temperature = 0.2
input_price = 0.0
output_price = 0.0
```

Design law:

```md
## Local Model Law

The CLI should not be locked to one cloud.

Support:

- OpenRouter
- Mistral API
- local OpenAI-compatible servers
- LM Studio
- Ollama
- llama.cpp
- vLLM
```

---

## 7.12 MCP Server Configuration

Mistral Vibe supports MCP server configuration through `config.toml`, with HTTP, streamable HTTP, and other server patterns shown in the docs. It supports headers, API-key env vars, API-key header names, and API-key formatting. ([Mistral AI][9])

Mythic adaptation:

```toml
[[mcp_servers]]
name = "local_docs"
transport = "http"
url = "http://localhost:8000"
api_key_env = "LOCAL_DOCS_API_KEY"
api_key_header = "Authorization"
api_key_format = "Bearer {token}"

[[mcp_servers]]
name = "norse_lore"
transport = "streamable-http"
url = "http://localhost:8001"
headers = { "X-Project" = "Norse-Saga-Engine" }
```

Design law:

```md
## MCP Law

MCP servers should be:

- named
- transport-aware
- credential-safe
- trust-scoped
- tool-filterable
- project-configurable
```

---

## 7.13 ACP Integration

The source tree includes `vibe/acp/` with `acp_agent_loop.py`, `entrypoint.py`, `acp_logger.py`, and a tools folder. ([GitHub][11])

The README also says Mistral Vibe can be used in editors and IDEs that support **Agent Client Protocol**. ([GitHub][3])

Mythic adaptation:

```text
mythic_cli/acp/
  entrypoint.py
  acp_agent_loop.py
  acp_logger.py
  tools/
```

Design law:

```md
## ACP Law

The agent should not be trapped in one terminal UI.

ACP makes the same agent usable from:

- Zed
- JetBrains
- VS Code-style clients
- external controllers
- future IDE bridges
```

---

## 7.14 Programmatic Mode

Mistral Vibe supports non-interactive programmatic mode through `--prompt`, stdin-style workflows, `--max-turns`, `--max-price`, `--enabled-tools`, and output formats including text, JSON, and streaming newline-delimited JSON. ([GitHub][3])

Mythic adaptation:

```bash
mythic --prompt "Analyze the codebase" --max-turns 5 --output json
mythic --prompt "Fix failing tests" --enabled-tools read_file --enabled-tools search_replace
cat error.log | mythic --prompt "Explain and propose a fix"
```

Design law:

```md
## Programmatic Mode Law

A serious CLI must support:

- interactive work
- one-shot prompts
- piped input
- bounded turns
- cost limits
- tool restrictions
- JSON output
- streaming output
- CI/CD use
```

---

## 7.15 Session Logging, Resume, and Continuation

Mistral Vibe supports session continuation and resumption using `--continue` / `-c` and `--resume SESSION_ID`, provided session logging is enabled. The source tree includes `vibe/core/session/` with `resume_sessions.py`, `session_loader.py`, `session_logger.py`, and `session_migration.py`. ([GitHub][3])

Mythic adaptation:

```text
.mythic/sessions/
  logs/
  checkpoints/
  migrations/
```

Commands:

```bash
mythic --continue
mythic --resume abc123
```

Design law:

```md
## Session Law

Every serious coding session should be recoverable.

The CLI should support:

- session logs
- continue last session
- resume by ID
- migration between session formats
- turn summaries
- exportable history
```

---

## 7.16 Trusted Folder System

Mistral Vibe includes a trusted folder system to prevent accidental execution in sensitive directories. Trusted folders are remembered in `~/.vibe/trusted_folders.toml`. ([GitHub][3])

Mythic adaptation:

```text
~/.mythic/trusted_folders.toml
```

Design law:

```md
## Trust Folder Law

The agent should not run with powerful tools in an untrusted directory.

A project becomes trusted only after explicit user confirmation.

Trust should be remembered, inspectable, and revocable.
```

---

## 7.17 AGENTS.md Support

The Agents & Skills docs note that Mistral Vibe has `AGENTS.md` support, currently functional when the file is in the root of the workspace. ([Mistral AI][12])

Mythic adaptation:

```text
AGENTS.md
MYTHIC.md
DOMAIN_MAP.md
ARCHITECTURE.md
INTERFACE.md
```

Design law:

```md
## Agent Instruction Law

Project-level agent instructions should live in repo files.

The agent should automatically load:

- AGENTS.md
- MYTHIC.md
- DOMAIN_MAP.md
- ARCHITECTURE.md
- INTERFACE.md
```

---

## 7.18 `search_replace.py`

The built-in tool list includes `search_replace.py`, which is especially relevant for coding agents because reliable edit application is one of the hardest parts of agentic coding. ([GitHub][7])

Mythic adaptation:

```text
mythic_cli/patching/
  search_replace.py
  patch_preview.py
  apply_patch.py
  conflict_detection.py
```

Design law:

```md
## Patch Law

File edits should be:

- previewable
- reversible
- diffable
- failure-safe
- protected against stale context
- protected against overwriting user work
```

---

## 7.19 `todo.py`

Mistral Vibe includes a `todo` tool to track the agent’s work. ([Mistral AI][2])

Mythic adaptation:

```text
mythic_cli/todo/
  todo_model.py
  todo_tool.py
  todo_view.py
```

Design law:

```md
## Todo Law

The agent should maintain visible working state.

A todo system should track:

- planned steps
- in-progress work
- completed work
- blocked work
- user approval needs
```

---

## 7.20 Notifications and Update Settings

Mistral Vibe supports notifications for approval-needed, question-needed, or task-complete states, and it has an auto-update setting enabled by default unless disabled in config. ([Mistral AI][9])

Mythic adaptation:

```toml
enable_auto_update = false
enable_notifications = true
```

Design law:

```md
## Notification Law

Long-running agent sessions should signal when:

- approval is needed
- user input is needed
- the task is complete
- an error blocks progress
```

---

## 7.21 Telemetry Toggle

The README says use of Vibe may include usage data collection and that telemetry can be disabled by setting `enable_telemetry = false` in `config.toml`. ([GitHub][3])

Mythic adaptation:

```toml
enable_telemetry = false
```

Design law:

```md
## Telemetry Law

Telemetry should be:

- explicit
- documented
- configurable
- easy to disable
- never mixed with secrets
```

For your own open-source CLI, I would default telemetry to **off** unless you have a very clear reason.

---

## 8. Suggested Plunder Priority

### Tier 1 — Highest Value

Study first:

```text
vibe/core/agent_loop.py
vibe/core/programmatic.py
vibe/core/tools/
vibe/core/tools/builtins/
vibe/core/config/
vibe/core/agents/
vibe/core/skills/
vibe/core/session/
vibe/cli/commands.py
vibe/cli/textual_ui/
vibe/cli/autocompletion/
```

These are the bones: agent loop, programmatic mode, tools, permissions, configs, agents, skills, session handling, slash commands, and terminal UI.

---

### Tier 2 — Mythic Engineering Power Systems

Study next:

```text
vibe/acp/
vibe/core/llm/
vibe/core/prompts/
vibe/core/system_prompt.py
vibe/core/plan_session.py
vibe/core/middleware.py
vibe/core/output_formatters.py
vibe/core/tracing.py
vibe/core/trusted_folders.py
vibe/cli/turn_summary/
vibe/cli/update_notifier/
vibe/cli/voice_manager/
```

These are the expansion systems: ACP, model/provider formatting, prompts, planning, middleware, output formats, tracing, trust safety, summaries, notifications, and voice.

---

### Tier 3 — Support Infrastructure

Study later:

```text
tests/
pyproject.toml
uv.lock
flake.nix
action.yml
vibe-acp.spec
CHANGELOG.md
CONTRIBUTING.md
```

These are useful for packaging, CI, test strategy, Nix/dev environment, ACP spec, release history, and contribution workflow.

---

## 9. What Not To Plunder Blindly

Be careful with:

* Mistral branding
* Devstral branding
* Mistral service-specific auth
* Codestral API key flow
* telemetry defaults
* auto-update behavior
* product-specific UI branding
* service endpoints
* pricing/cost assumptions
* model aliases that may change
* voice/audio features you do not need
* Nuage or account-plan-specific logic
* anything tied to Mistral commercial infrastructure

Clean strategy:

```md
Copy architecture aggressively.

Copy implementation selectively.

Rewrite branding, telemetry, provider defaults, service auth, and update behavior.
```

---

## 10. Recommended Local Study Workflow

### Step 1: Clone Upstream

```bash
git clone https://github.com/mistralai/mistral-vibe.git external/mistral-vibe
cd external/mistral-vibe
```

### Step 2: Inspect Structure

```bash
find vibe -maxdepth 3 -type d | sort
find vibe/core/tools -maxdepth 3 -type f | sort
find vibe/cli -maxdepth 3 -type f | sort
```

### Step 3: Create a Plunder Map

Create:

```text
docs/plunder/MISTRAL_VIBE_PLUNDER_MAP.md
```

Template:

```md
# Mistral Vibe Plunder Map

## Upstream

Project: Mistral Vibe  
Repository: mistralai/mistral-vibe  
License: Apache-2.0  
Language: Python  
Primary package: vibe/

## Targeted Areas

| Upstream Path | Local Target | Status | Notes |
|---|---|---|---|
| vibe/core/agent_loop.py | mythic_cli/core/agent_loop.py | studying | Main agent loop |
| vibe/core/programmatic.py | mythic_cli/core/programmatic.py | planned | Non-interactive mode |
| vibe/core/tools | mythic_cli/tools | planned | Tool registry and permissions |
| vibe/core/tools/builtins/search_replace.py | mythic_cli/patching/search_replace.py | planned | Safe edit primitive |
| vibe/core/agents | .mythic/agents | planned | Agent profile system |
| vibe/core/skills | .mythic/skills | planned | Skill parser/manager |
| vibe/core/session | mythic_cli/session | planned | Resume/session logs |
| vibe/acp | mythic_cli/acp | studying | IDE bridge |
| vibe/cli/textual_ui | mythic_cli/tui | studying | Terminal UI |
| vibe/cli/autocompletion | mythic_cli/autocomplete | planned | Slash/file autocomplete |
```

### Step 4: Copy One Subsystem at a Time

```bash
git checkout -b adapt-mistral-vibe-tools
```

### Step 5: Commit With Attribution

```bash
git commit -m "Adapt tool registry patterns from Mistral Vibe

- Adds Apache-2.0 attribution
- Marks modified files
- Updates THIRD_PARTY_NOTICES.md
- Reworks tool permissions for Mythic CLI"
```

---

## 11. README Attribution Template

```md
## Third-Party Attribution

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected architectural patterns and code from Mistral Vibe, also licensed under Apache-2.0.

Mistral Vibe is an open-source terminal-native coding assistant from Mistral AI.

This project is independent and is not affiliated with, endorsed by, or sponsored by Mistral AI or the Mistral Vibe project.
```

---

## 12. Mythic CLI Adaptation Map

### 12.1 Agent Core

Mistral Vibe inspiration:

```text
vibe/core/agent_loop.py
vibe/core/middleware.py
vibe/core/system_prompt.py
vibe/core/plan_session.py
```

Mythic target:

```text
mythic_cli/core/
  agent_loop.py
  middleware.py
  system_prompt.py
  plan_session.py
```

---

### 12.2 Tool Layer

Mistral Vibe inspiration:

```text
vibe/core/tools/
vibe/core/tools/builtins/
```

Mythic target:

```text
mythic_cli/tools/
  base.py
  manager.py
  permissions.py
  builtins/
```

---

### 12.3 Terminal UI

Mistral Vibe inspiration:

```text
vibe/cli/textual_ui/
vibe/cli/autocompletion/
vibe/cli/commands.py
```

Mythic target:

```text
mythic_cli/tui/
  app.py
  components/
  autocompletion/
  commands.py
```

---

### 12.4 Agents

Mistral Vibe inspiration:

```text
vibe/core/agents/
~/.vibe/agents/
```

Mythic target:

```text
.mythic/agents/
  architect.toml
  forge-worker.toml
  auditor.toml
  cartographer.toml
  scribe.toml
```

---

### 12.5 Skills

Mistral Vibe inspiration:

```text
vibe/core/skills/
~/.vibe/skills/
.vibe/skills/
.agents/skills/
```

Mythic target:

```text
.mythic/skills/
  architecture-audit/
  patch-forge/
  repo-cartography/
  test-repair/
  docs-scribe/
```

---

### 12.6 Session System

Mistral Vibe inspiration:

```text
vibe/core/session/
```

Mythic target:

```text
mythic_cli/session/
  session_logger.py
  session_loader.py
  resume_sessions.py
  session_migration.py
```

---

### 12.7 ACP Bridge

Mistral Vibe inspiration:

```text
vibe/acp/
vibe-acp.spec
```

Mythic target:

```text
mythic_cli/acp/
  acp_agent_loop.py
  entrypoint.py
  logger.py
  tools/
```

---

### 12.8 Config System

Mistral Vibe inspiration:

```text
vibe/core/config/
~/.vibe/config.toml
./.vibe/config.toml
~/.vibe/.env
~/.vibe/trusted_folders.toml
```

Mythic target:

```text
mythic_cli/config/
~/.mythic/config.toml
./.mythic/config.toml
~/.mythic/.env
~/.mythic/trusted_folders.toml
```

---

## 13. Final Checklist Before Publishing

Before pushing your adapted CLI publicly:

* [ ] Your repo has `LICENSE`.
* [ ] Your repo uses Apache-2.0 or another compatible strategy.
* [ ] Your repo has `NOTICE`.
* [ ] Your repo has `THIRD_PARTY_NOTICES.md`.
* [ ] Your README credits `mistralai/mistral-vibe`.
* [ ] Modified files have prominent change notices.
* [ ] Original copyright/SPDX/license headers are preserved.
* [ ] You removed Mistral/Devstral branding from your own product identity.
* [ ] You documented copied/adapted areas in a plunder map.
* [ ] You tested each adapted subsystem.
* [ ] You understand every copied dependency.
* [ ] Telemetry is disabled, removed, or made explicit.
* [ ] Auto-update behavior is disabled or clearly user-controlled.
* [ ] Tool permissions are safe by default.
* [ ] Auto-approve mode is explicit.
* [ ] Trusted-folder logic is preserved or replaced with your own safety gate.
* [ ] Session logs do not leak secrets.
* [ ] Provider configs do not hardcode API keys.
* [ ] MCP servers are trust-scoped.
* [ ] ACP behavior does not imply official Mistral compatibility unless actually tested.

---

## 14. Clean Rule

```text
Copy the architecture.
Respect the license.
Preserve attribution.
Mark your changes.
Do not steal the branding.
Rewrite provider-specific service logic.
Make telemetry explicit.
Make auto-approval dangerous by design.
Study tools, skills, agents, ACP, and config deeply.
```

Mistral Vibe is especially valuable because it is a **clean Python terminal-agent architecture** with:

* agent loop
* programmatic mode
* Textual-style terminal UI
* file/path autocomplete
* slash commands
* built-in tools
* tool permissions
* subagents
* structured user questions
* skills
* custom agents
* MCP
* ACP
* local/offline model support
* config.toml model/provider presets
* trusted folders
* session logging/resume
* notifications
* voice mode

For your own CLI project, the greatest treasure is probably:

```text
Mistral Vibe's Python tool system + agent profiles + skills + ACP bridge.
```

That is lean, practical, plunder-worthy steel.

[1]: https://docs.mistral.ai/mistral-vibe/overview?utm_source=chatgpt.com "Mistral Vibe | Mistral Docs"
[2]: https://docs.mistral.ai/mistral-vibe/terminal "CLI Introduction | Mistral Docs"
[3]: https://github.com/mistralai/mistral-vibe "GitHub - mistralai/mistral-vibe: Minimal CLI coding agent by Mistral · GitHub"
[4]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/core "mistral-vibe/vibe/core at main · mistralai/mistral-vibe · GitHub"
[5]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/cli "mistral-vibe/vibe/cli at main · mistralai/mistral-vibe · GitHub"
[6]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/core/tools "mistral-vibe/vibe/core/tools at main · mistralai/mistral-vibe · GitHub"
[7]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/core/tools/builtins "mistral-vibe/vibe/core/tools/builtins at main · mistralai/mistral-vibe · GitHub"
[8]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/core/skills "mistral-vibe/vibe/core/skills at main · mistralai/mistral-vibe · GitHub"
[9]: https://docs.mistral.ai/mistral-vibe/terminal/configuration "Configuration | Mistral Docs"
[10]: https://docs.mistral.ai/mistral-vibe/local?utm_source=chatgpt.com "Offline / Local | Mistral Docs"
[11]: https://github.com/mistralai/mistral-vibe/tree/main/vibe/acp "mistral-vibe/vibe/acp at main · mistralai/mistral-vibe · GitHub"
[12]: https://docs.mistral.ai/mistral-vibe/agents-skills?utm_source=chatgpt.com "Agents & Skills | Mistral Docs"
