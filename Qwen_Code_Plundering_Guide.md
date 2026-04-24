# Qwen Code Plundering Guide

## Purpose

This guide explains how to lawfully study, reuse, adapt, and “plunder” useful architecture from **Qwen Code** for your own Apache-2.0 CLI project.

Qwen Code is an open-source AI agent that lives in the terminal, optimized for Qwen-series models, but also designed to support multiple providers and protocols. The README says it can help understand large codebases, automate tedious work, and provide a Claude Code-like agentic workflow with tools, Skills, SubAgents, terminal-first usage, and IDE integrations. ([GitHub][1])

This is practical open-source hygiene, not legal advice.

---

## 1. Core Legal Position

### License Match

Qwen Code is licensed under **Apache License 2.0**. The GitHub repo lists the license as Apache-2.0, and the repository includes a root `LICENSE` file. ([GitHub][1])

Apache-2.0 generally allows you to:

* Copy code.
* Modify code.
* Merge code into your own project.
* Redistribute modified versions.
* Use it commercially.
* Build your own Apache-2.0 project from adapted pieces.

In plain Viking terms:

> Take the useful steel.
> Keep the maker’s mark.
> Forge your own blade.

---

## 2. Required Source Links

Use these as canonical references in your own project docs.

### Main Project Links

* [Qwen Code GitHub Repository](https://github.com/QwenLM/qwen-code)
* [Qwen Code LICENSE](https://github.com/QwenLM/qwen-code/blob/main/LICENSE)
* [Qwen Code Documentation](https://qwenlm.github.io/qwen-code-docs/en/)
* [Qwen Code Architecture Overview](https://qwenlm.github.io/qwen-code-docs/en/developers/architecture/)
* [Qwen Code Commands](https://qwenlm.github.io/qwen-code-docs/en/users/features/commands/)
* [Qwen Code SubAgents](https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/)
* [Qwen Code Skills](https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/)
* [Qwen Code Headless Mode](https://qwenlm.github.io/qwen-code-docs/en/users/features/headless/)
* [Qwen Code MCP Docs](https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/)
* [Qwen Code Approval Modes](https://qwenlm.github.io/qwen-code-docs/en/users/features/approval-mode/)
* [Qwen Code Sandboxing](https://qwenlm.github.io/qwen-code-docs/en/users/features/sandbox/)
* [Qwen Code Hooks](https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/)
* [Qwen Code LSP Support](https://qwenlm.github.io/qwen-code-docs/en/users/features/lsp/)
* [Qwen Code Model Providers](https://qwenlm.github.io/qwen-code-docs/en/users/configuration/model-providers/)
* [Qwen Code TypeScript SDK](https://qwenlm.github.io/qwen-code-docs/en/developers/sdk-typescript/)
* [Qwen Code Extensions Guide](https://qwenlm.github.io/qwen-code-docs/en/developers/extensions/getting-started-extensions/)

---

## 3. Important Upstream Relationship

Qwen Code is not just “randomly similar” to Gemini CLI. Its README explicitly says:

> “This project is based on Google Gemini CLI.”

It also says Qwen Code’s main contribution focuses on **parser-level adaptations to better support Qwen-Coder models**. ([GitHub][1])

That means your attribution should probably acknowledge both:

1. **QwenLM/qwen-code**
2. **Google Gemini CLI**, where inherited code or structure remains relevant

This matters because some example extension code in Qwen’s docs still carries Google copyright and Apache-2.0 SPDX notices. ([Qwen][2])

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

When copying files or meaningful chunks, preserve any existing copyright, SPDX, license, or attribution headers.

Do not delete headers like:

```ts
/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */
```

If a copied Qwen file contains Qwen, Alibaba, Google, Gemini CLI, or other third-party notices, keep them.

---

### 4.3 Mark Modified Files

When you modify copied/adapted files, add a clear notice.

#### TypeScript

```ts
// Portions adapted from QwenLM/qwen-code.
// Qwen Code is licensed under the Apache License, Version 2.0.
// Modified by Volmarr / RuneForgeAI, 2026.
```

#### Markdown

```md
<!--
Portions adapted from QwenLM/qwen-code.
Qwen Code is licensed under the Apache License, Version 2.0.
Modified by Volmarr / RuneForgeAI, 2026.
-->
```

#### Python

```python
# Portions adapted from QwenLM/qwen-code.
# Qwen Code is licensed under the Apache License, Version 2.0.
# Modified by Volmarr / RuneForgeAI, 2026.
```

---

### 4.4 Add a Third-Party Notice File

Even if you do not find a root `NOTICE` file in Qwen Code, you should still keep your own notice file because you are intentionally adapting upstream code.

Recommended files:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/QWEN_CODE_PLUNDER_GUIDE.md
docs/plunder/QWEN_CODE_PLUNDER_MAP.md
```

---

## 5. Suggested `NOTICE`

```md
# NOTICE

[Your CLI Project Name]

Copyright 2026 Volmarr / RuneForgeAI

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected portions of software from:

## Qwen Code

Project: Qwen Code  
Repository: QwenLM/qwen-code  
License: Apache License 2.0

Qwen Code is an open-source AI agent that lives in the terminal.

## Google Gemini CLI

Qwen Code identifies itself as based on Google Gemini CLI.  
Where adapted Qwen Code material contains inherited Gemini CLI / Google notices, those notices are preserved.

This project is independent and is not affiliated with, endorsed by, or sponsored by QwenLM, Alibaba Cloud, Google, or the Gemini CLI team.
```

---

## 6. Suggested `THIRD_PARTY_NOTICES.md`

```md
# Third-Party Notices

This project includes or adapts material from third-party open-source projects.

## Qwen Code

Project: Qwen Code  
Repository: QwenLM/qwen-code  
License: Apache License 2.0  

Usage:

This project may include or adapt selected portions of Qwen Code, especially architectural patterns related to:

- Terminal AI agent architecture
- CLI/core package separation
- Interactive terminal UI
- Headless mode
- Model provider configuration
- Qwen-Coder parser adaptations
- SubAgents
- Agent Skills
- MCP integration
- Approval modes
- Sandboxing
- Hooks
- Scheduled tasks
- LSP integration
- IDE companion patterns
- Extension packaging
- SDK access

## Google Gemini CLI

Qwen Code states that it is based on Google Gemini CLI.

Where Qwen Code files contain inherited Google/Gemini notices, this project preserves those notices.

This project is independent and is not affiliated with, endorsed by, or sponsored by QwenLM, Alibaba Cloud, Google, or the Gemini CLI team.
```

---

## 7. Branding Warning

Apache-2.0 lets you reuse code. It does **not** let you steal product identity.

Safe wording:

```md
This project includes code adapted from QwenLM/qwen-code.
```

Unsafe wording:

```md
This is the official Qwen Code CLI.
```

Avoid naming your project:

* Qwen Code Pro
* Official Qwen CLI
* Alibaba Code Agent
* Qwen-Coder Official CLI
* Gemini-Qwen Official Fork

Use Qwen, Alibaba, Google, and Gemini names only for attribution.

---

## 8. Repo Structure Worth Studying

Qwen Code is a TypeScript/Node monorepo. The root repo includes `.qwen`, `docs-site`, `docs`, `eslint-rules`, `integration-tests`, `packages`, and scripts, with 5,582 commits and an active release stream at the time checked. ([GitHub][1])

The `packages` folder currently includes:

```text
packages/
  channels/
  cli/
  core/
  sdk-java/
  sdk-typescript/
  vscode-ide-companion/
  web-templates/
  webui/
  zed-extension/
```

That package split is very valuable because it shows Qwen Code expanding beyond “just a terminal app” into SDKs, IDE companions, web UI, channels, and extensions. ([GitHub][3])

---

## 9. Highest-Value Plunder Targets

## 9.1 `packages/core`

This is one of the richest targets.

Qwen’s architecture docs describe `packages/core` as the backend that receives requests from `packages/cli`, orchestrates model API interactions, constructs prompts, manages tool registration/execution, and maintains session state. ([Qwen][4])

The current `packages/core/src` tree includes:

```text
packages/core/src/
  agents/
  config/
  confirmation-bus/
  constants/
  core/
  extension/
  followup/
  hooks/
  ide/
  lsp/
  mcp/
  memory/
  models/
  output/
  permissions/
  prompts/
  qwen/
  services/
  skills/
  subagents/
  telemetry/
  test-utils/
  tools/
  utils/
```

This is a strong map for building your own serious CLI backend. ([GitHub][5])

### Likely Plunder Value

| Upstream Area      | Why It Is Interesting                              |
| ------------------ | -------------------------------------------------- |
| `agents`           | Multi-agent orchestration patterns.                |
| `config`           | Config loading, precedence, settings structure.    |
| `confirmation-bus` | Approval/event flow between UI and tool execution. |
| `core`             | Main backend agent loop.                           |
| `extension`        | Extension loading model.                           |
| `followup`         | Follow-up suggestions after agent turns.           |
| `hooks`            | Lifecycle/event extension points.                  |
| `ide`              | IDE integration bridge.                            |
| `lsp`              | Language Server Protocol intelligence.             |
| `mcp`              | External tool/data source integration.             |
| `memory`           | Local memory/context behavior.                     |
| `models`           | Model provider abstraction.                        |
| `output`           | Structured output/rendering logic.                 |
| `permissions`      | Approval mode and tool permission law.             |
| `prompts`          | Prompt construction and system behavior.           |
| `qwen`             | Qwen-specific parser/model adaptations.            |
| `skills`           | Agent Skills system.                               |
| `subagents`        | Specialized role agents.                           |
| `tools`            | Built-in tool registry and execution.              |

---

## 9.2 `packages/cli`

Qwen’s architecture docs describe `packages/cli` as the user-facing terminal layer: input handling, slash commands, `@file` inclusion, `!command` shell execution, history, rendering, themes, UI customization, and local config handling. ([Qwen][4])

The current `packages/cli/src` tree includes:

```text
packages/cli/src/
  acp-integration/
  commands/
  config/
  constants/
  core/
  dualOutput/
  export/
  i18n/
  nonInteractive/
  patches/
  remoteInput/
  services/
  test-utils/
  ui/
  utils/
  gemini.tsx
  nonInteractiveCli.ts
  nonInteractiveCliCommands.ts
```

This is very useful for terminal UX, headless mode, patches, export, remote input, and ACP/IDE-style integration. ([GitHub][6])

### Likely Plunder Value

| Upstream Area          | Why It Is Interesting                              |
| ---------------------- | -------------------------------------------------- |
| `commands`             | Slash-command architecture.                        |
| `nonInteractive`       | Headless execution internals.                      |
| `nonInteractiveCli.ts` | Script/CI mode entrypoint.                         |
| `patches`              | Patch preview/apply flow.                          |
| `ui`                   | Terminal rendering and interaction design.         |
| `dualOutput`           | Output to terminal plus structured/export targets. |
| `export`               | Session/result export logic.                       |
| `i18n`                 | Internationalization structure.                    |
| `remoteInput`          | Nonlocal/channel input handling.                   |
| `acp-integration`      | IDE/agent protocol integration.                    |

---

## 9.3 `.qwen` Project Capability System

The repo’s `.qwen` folder includes:

```text
.qwen/
  agents/
  commands/qc/
  skills/
```

That is directly useful for your own `.mythic` system. ([GitHub][7])

Suggested adaptation:

```text
.qwen/agents/       -> .mythic/agents/
.qwen/commands/     -> .mythic/commands/
.qwen/skills/       -> .mythic/skills/
QWEN.md             -> MYTHIC.md or AGENTS.md
```

---

## 10. SubAgents: Very High-Value Plunder Target

Qwen Code’s docs define SubAgents as specialized AI assistants for focused tasks, configured with task-specific prompts, tools, and behavior. ([Qwen][8])

SubAgents are stored in:

```text
.qwen/agents/       # project-level, highest precedence
~/.qwen/agents/     # user-level fallback
extensions          # extension-provided agents
```

The docs say SubAgents use Markdown files with YAML frontmatter. ([Qwen][8])

### Suggested Mythic Adaptation

```text
.mythic/agents/
  architect.md
  forge-worker.md
  auditor.md
  cartographer.md
  scribe.md
  warden.md
  seer.md
```

Example:

```md
---
name: architect
description: Defines module boundaries, ownership, and long-range structure.
model: inherit
tools:
  - read_file
  - search
  - grep
---

# Architect

You are The Architect.

Owns:

- Domain boundaries
- Architecture maps
- Refactor plans
- Module ownership
- Structural drift detection

Never owns:

- Random implementation churn
- Unreviewed rewrites
- Silent behavior changes
```

---

## 11. Agent Skills: Very High-Value Plunder Target

Qwen Skills are modular capability packages. Each Skill contains a required `SKILL.md` plus optional scripts, templates, examples, or reference files. ([Qwen][9])

The docs show this structure:

```text
my-skill/
  SKILL.md
  reference.md
  examples.md
  scripts/
    helper.py
  templates/
    template.txt
```

Project and personal skills live at `.qwen/skills/<skill-name>/SKILL.md` and `~/.qwen/skills/<skill-name>/SKILL.md`. ([Qwen][9])

### Suggested Mythic Adaptation

```text
.mythic/skills/
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
  qwen-code-plunder/
    SKILL.md
```

Example:

```md
---
name: architecture-audit
description: Audit a codebase for boundary violations, ownership confusion, drift, unsafe coupling, and missing documentation.
---

# Architecture Audit

## Instructions

1. Read `DOMAIN_MAP.md`, `ARCHITECTURE.md`, and nearby `README.md` files.
2. Identify boundary violations.
3. Identify duplicated ownership.
4. Identify files that need `INTERFACE.md` updates.
5. Return a concrete refactor plan.

## Output Format

Return:

1. Findings
2. Risk level
3. Affected files
4. Recommended changes
5. Required documentation updates
```

---

## 12. Headless Mode: High-Value Plunder Target

Qwen’s headless mode lets it run from scripts and automation without the interactive UI. It accepts prompts from command-line arguments or stdin, returns text or JSON, supports piping/redirection, provides exit codes, and can resume project-scoped sessions. ([Qwen][10])

Useful patterns:

```bash
qwen --prompt "What is machine learning?"
echo "Explain this code" | qwen
cat README.md | qwen --prompt "Summarize this documentation"
```

The docs also describe `--system-prompt` and `--append-system-prompt` for run-specific prompt control. ([Qwen][10])

### Suggested Mythic Adaptation

```bash
mythic --prompt "audit this repo for architecture drift"
cat error.log | mythic --prompt "explain this failure"
mythic -p "review this patch" \
  --system-prompt "You are The Auditor." \
  --append-system-prompt "Report only blocking issues."
```

Design law:

```md
## Headless Law

A serious AI CLI must support:

- Interactive terminal work
- Scripted one-shot execution
- Stdin input
- Structured output
- CI/CD usage
- Session resume
- Prompt override
- Append-only run instructions
```

---

## 13. MCP: High-Value Plunder Target

Qwen Code can connect to external tools and data sources through MCP. The docs list use cases like files/repos, databases, internal services, and repeatable workflows exposed as tools or prompts. ([Qwen][11])

Qwen supports MCP configuration through `.qwen/settings.json` or `qwen mcp` commands, with project and user scopes. It supports `stdio`, `http`, and legacy `sse` transports. ([Qwen][11])

The docs also describe safety controls:

* `trust: true` to skip confirmations for a server
* `includeTools` / `excludeTools`
* global `mcp.allowed`
* global `mcp.excluded`

([Qwen][11])

### Suggested Mythic Adaptation

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
      "timeout": 15000,
      "includeTools": ["search_docs", "read_doc"]
    },
    "github": {
      "httpUrl": "http://localhost:3000/mcp",
      "headers": {
        "Authorization": "Bearer $GITHUB_TOKEN"
      },
      "trust": false
    }
  }
}
```

Design law:

```md
## MCP Law

External tools should be:

- Named
- Scoped
- Filterable
- Trust-gated
- Transport-agnostic
- Configurable at user and project levels
```

---

## 14. Approval Modes: High-Value Plunder Target

Qwen Code has four permission modes:

| Mode        | File Editing        | Shell Commands        | Risk    |
| ----------- | ------------------- | --------------------- | ------- |
| `plan`      | No edits            | No shell execution    | Lowest  |
| `default`   | Manual approval     | Manual approval       | Low     |
| `auto-edit` | Auto-approved edits | Manual shell approval | Medium  |
| `yolo`      | Auto-approved       | Auto-approved         | Highest |

([Qwen][12])

The docs recommend Plan Mode for safe exploration, Default Mode for controlled work, Auto-Edit for daily development, and YOLO only for trusted automation in controlled environments. ([Qwen][12])

### Suggested Mythic Adaptation

```json
{
  "permissions": {
    "defaultMode": "plan",
    "confirmShellCommands": true,
    "confirmFileEdits": true
  }
}
```

Design law:

```md
## Permission Law

The agent may think freely.

The agent may read within the approved workspace.

The agent may only modify or execute according to the active approval mode.

Dangerous automation must be explicit, visible, and reversible.
```

---

## 15. Sandboxing: High-Value Plunder Target

Qwen sandboxing can be enabled by environment variable, CLI flag, or `settings.json`. It supports provider selection through `QWEN_SANDBOX=true|false|docker|podman|sandbox-exec`. On macOS it can use Seatbelt profiles; on Linux/Windows it requires Docker or Podman when sandboxing is enabled. ([Qwen][13])

The docs also describe custom sandbox images, custom Seatbelt profiles, custom Docker/Podman flags, and proxying outbound network access. ([Qwen][13])

### Suggested Mythic Adaptation

```bash
# Enable sandboxing for one command
mythic -s -p "run tests safely"

# Enable sandboxing for this shell
export MYTHIC_SANDBOX=true

# Force Docker
export MYTHIC_SANDBOX=docker
```

Project config:

```json
{
  "tools": {
    "sandbox": true
  }
}
```

Design law:

```md
## Sandbox Law

Sandboxing is the physical boundary.

Approval mode is the decision boundary.

Both must exist.
```

---

## 16. Hooks: Very Interesting Plunder Target

Qwen hooks run custom scripts/programs at lifecycle points such as before tool execution, after tool execution, session start/end, and other key events. The docs say hooks can monitor/audit tool use, enforce security policies, inject context, integrate external systems, and modify tool inputs or responses. ([Qwen][14])

The hook architecture includes:

* Hook Registry
* Hook Planner
* Hook Runner
* Hook Aggregator
* Hook Event Handler

Hooks can execute in parallel by default, or sequentially when order matters. Project-level hooks require trusted folder status, and hooks have timeouts to avoid hanging. ([Qwen][14])

### Suggested Mythic Adaptation

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "^bash$",
        "hooks": [
          {
            "type": "command",
            "command": "python .mythic/hooks/check_shell_risk.py"
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "^(startup|resume)$",
        "hooks": [
          {
            "type": "command",
            "command": "python .mythic/hooks/load_project_law.py"
          }
        ]
      }
    ]
  }
}
```

Design law:

```md
## Hook Law

Hooks are not random scripts.

They are controlled ritual gates:

- Before tool use
- After tool use
- On session start
- On session end
- On subagent start
- On approval need
- On failure
```

---

## 17. Scheduled Tasks: Interesting Plunder Target

Qwen scheduled tasks can run prompts on a schedule using `/loop`, and scheduled prompts can even call other commands or skills. The docs show `/loop 20m /review-pr 1234`, meaning a packaged workflow can be rerun periodically. ([Qwen][15])

Under the hood, Qwen uses tools like:

* `CronCreate`
* `CronList`
* `CronDelete`

Scheduled tasks have IDs, a session can hold up to 50 scheduled tasks, and the scheduler enqueues due tasks only when the session is idle. ([Qwen][15])

### Suggested Mythic Adaptation

```text
/loop 30m run architecture drift check
/loop 1h /audit-current-branch
/loop list
/loop clear
```

Design law:

```md
## Scheduled Task Law

Scheduled prompts should never interrupt an active turn.

They should queue until the agent is idle.

They should be visible, listable, cancellable, and bounded.
```

---

## 18. LSP: Very Strategic Plunder Target

Qwen Code has experimental native LSP support. Its docs say LSP enables go-to-definition, find references, diagnostics, code actions, hover information, and call hierarchy analysis. ([Qwen][16])

The docs show `.lsp.json` configuration and language server setup for TypeScript/JavaScript, Python, Go, Rust, C/C++, and Java. ([Qwen][16])

### Suggested Mythic Adaptation

```json
{
  "typescript": {
    "command": "typescript-language-server",
    "args": ["--stdio"],
    "extensionToLanguage": {
      ".ts": "typescript",
      ".tsx": "typescriptreact",
      ".js": "javascript",
      ".jsx": "javascriptreact"
    }
  },
  "python": {
    "command": "pylsp",
    "args": []
  },
  "rust": {
    "command": "rust-analyzer",
    "args": []
  }
}
```

Design law:

```md
## LSP Law

Do not make the model guess what the language server already knows.

Use LSP for:

- Definitions
- References
- Diagnostics
- Hover/type information
- Code actions
- Call hierarchy
```

---

## 19. Model Providers: Very Important Plunder Target

Qwen supports multiple providers and protocols. The README says authentication supports API keys for Alibaba Cloud Model Studio or supported providers including OpenAI, Anthropic, Google GenAI, and other compatible endpoints. ([GitHub][1])

The Model Providers docs distinguish between:

* **Provider Models**: defined in `modelProviders`, with complete atomic configuration and metadata.
* **Runtime Models**: created dynamically from raw model IDs via CLI, env vars, or settings.

The docs also note that `modelProviders` uses a replace-style merge strategy, where project settings replace the user settings section instead of merging it. ([Qwen][17])

### Suggested Mythic Adaptation

```json
{
  "modelProviders": {
    "openrouter": [
      {
        "id": "qwen/qwen3.6-plus",
        "name": "Qwen 3.6 Plus via OpenRouter",
        "envKey": "OPENROUTER_API_KEY",
        "baseUrl": "https://openrouter.ai/api/v1"
      }
    ],
    "openai": [
      {
        "id": "gpt-5.5-thinking",
        "name": "GPT-5.5 Thinking",
        "envKey": "OPENAI_API_KEY"
      }
    ],
    "anthropic": [
      {
        "id": "claude-sonnet-4-20250514",
        "name": "Claude Sonnet 4",
        "envKey": "ANTHROPIC_API_KEY"
      }
    ]
  },
  "security": {
    "auth": {
      "selectedType": "openrouter"
    }
  },
  "model": {
    "name": "qwen/qwen3.6-plus"
  }
}
```

Design law:

```md
## Model Provider Law

A model provider should be a complete, named, reusable configuration.

Do not scatter model IDs, API keys, base URLs, and generation options across random config layers.
```

---

## 20. TypeScript SDK: Useful Plunder Target

Qwen Code has an experimental `@qwen-code/sdk` for programmatic access. It requires Node.js 20+ and a Qwen Code executable installed and accessible in `PATH`. ([Qwen][18])

The SDK docs list support for query options, message types, permission modes, custom permission handlers, external MCP servers, SDK-embedded MCP servers, aborting a query, and error handling. ([Qwen][18])

### Suggested Mythic Adaptation

Create your own SDK package:

```text
packages/
  sdk-typescript/
  sdk-python/
```

Use cases:

```ts
import { query } from "@mythic-cli/sdk";

const result = await query({
  prompt: "Audit this repo for architecture drift.",
  permissionMode: "plan",
});
```

Design law:

```md
## SDK Law

The CLI should not only be an app.

It should also be a programmable engine.
```

---

## 21. Extensions: Very Strong Plunder Target

Qwen’s extension guide shows extensions with:

```text
my-first-extension/
  example.ts
  qwen-extension.json
  package.json
  tsconfig.json
```

The extension manifest can declare MCP servers, and the docs show use of `${extensionPath}` so the extension works regardless of install location. ([Qwen][2])

### Suggested Mythic Adaptation

```text
mythic-extension.json
package.json
src/
  mcp-server.ts
commands/
  repo-audit.md
MYTHIC.md
```

Example:

```json
{
  "name": "mythic-repo-auditor",
  "version": "1.0.0",
  "mcpServers": {
    "repoAuditor": {
      "command": "node",
      "args": ["${extensionPath}/dist/mcp-server.js"],
      "cwd": "${extensionPath}"
    }
  }
}
```

Design law:

```md
## Extension Law

Extensions should be portable, declarative, and path-independent.

They should be able to provide:

- Tools
- Commands
- Context files
- Agents
- Skills
- Templates
```

---

## 22. Commands: Useful Plunder Target

Qwen supports slash commands, `@` commands for introducing files, `!` commands for shell execution, and custom commands. The commands docs also list bundled skill-like workflows such as `/review`, `/loop`, and `/qc-helper`. ([Qwen][19])

### Suggested Mythic Commands

```text
/audit
/architect
/forge
/scribe
/cartograph
/review
/loop
/plan
/mcp
/agents
/skills
/status
```

Example custom command:

```md
# architecture-audit

Act as The Architect.

Audit the current repository for:

- Domain boundary violations
- Duplicate ownership
- Unsafe coupling
- Missing interface docs
- Outdated architecture docs

Return:

1. Findings
2. Severity
3. Affected files
4. Repair plan
5. Documentation updates
```

---

## 23. Code Review: Strong Workflow Target

Qwen’s commands docs describe `/review` as reviewing code changes with **5 parallel agents plus deterministic analysis**. ([Qwen][19])

That is extremely aligned with your multi-agent vibe coding system.

### Suggested Mythic Adaptation

```text
/review
/review --branch
/review --staged
/review --pr 123
/review --comment
```

Design:

```md
## Review Agent Swarm

Use parallel reviewers:

1. Architecture Reviewer
2. Bug Reviewer
3. Security Reviewer
4. Test Reviewer
5. Documentation Reviewer

Then run deterministic checks:

- Git diff
- Test status
- Lint status
- File ownership map
- Public interface changes
```

---

## 24. Qwen-Specific Parser Adaptations

This is one of the most important reasons to study Qwen Code specifically instead of only Gemini CLI.

The README says Qwen Code is based on Google Gemini CLI and that its main contribution is parser-level adaptations for Qwen-Coder models. ([GitHub][1])

### Why This Matters

Different model families emit:

* Tool calls differently
* Code blocks differently
* Thinking-mode metadata differently
* Patch syntax differently
* JSON differently
* Function arguments differently

So Qwen’s parser adaptations may be some of the most valuable code to study if your CLI will support:

* Qwen
* OpenRouter
* local models
* LM Studio
* Ollama
* non-OpenAI-native tool calling
* mixed provider routing

Suggested Mythic design:

```text
mythic_cli/parsers/
  openai_parser.ts
  anthropic_parser.ts
  gemini_parser.ts
  qwen_parser.ts
  openrouter_parser.ts
  local_model_parser.ts
```

Design law:

```md
## Parser Law

Do not pretend all models speak the same protocol.

Normalize model output into a common internal event format:

- Assistant message
- Tool call
- Tool result
- Patch proposal
- Approval request
- Final response
```

---

## 25. Suggested Plunder Priority

### Tier 1 — Load-Bearing Architecture

Study first:

```text
packages/core/src/core
packages/core/src/tools
packages/core/src/permissions
packages/core/src/models
packages/core/src/qwen
packages/core/src/config
packages/core/src/mcp
packages/core/src/subagents
packages/core/src/skills
packages/cli/src/nonInteractive
packages/cli/src/ui
packages/cli/src/commands
packages/cli/src/patches
```

---

### Tier 2 — Mythic Engineering Power Systems

Study next:

```text
packages/core/src/hooks
packages/core/src/lsp
packages/core/src/memory
packages/core/src/extension
packages/core/src/confirmation-bus
packages/core/src/followup
packages/cli/src/dualOutput
packages/cli/src/export
packages/cli/src/remoteInput
packages/cli/src/acp-integration
.qwen/agents
.qwen/skills
.qwen/commands
```

---

### Tier 3 — Ecosystem / Expansion Systems

Study later:

```text
packages/channels
packages/sdk-typescript
packages/sdk-java
packages/vscode-ide-companion
packages/zed-extension
packages/webui
packages/web-templates
integration-tests
docs-site
eslint-rules
scripts
```

---

## 26. What Not To Plunder Blindly

Be careful with:

* Qwen branding
* Alibaba branding
* Google/Gemini branding
* Alibaba Cloud Coding Plan assumptions
* Deprecated Qwen OAuth logic
* Provider-specific auth flows
* Telemetry defaults
* Service endpoints
* Billing/quota behavior
* Any hardcoded model names that may become outdated
* Anything tied to Chinese/international ModelStudio differences
* Anything you cannot maintain yourself

The README notes that Qwen OAuth was discontinued on April 15, 2026, and users should switch to API key, Coding Plan, OpenRouter, Fireworks, or another supported provider. ([GitHub][1])

Design law:

```md
## Service-Specific Code Law

Copy architecture freely.

Copy implementation carefully.

Rewrite provider-specific auth, billing, telemetry, and service assumptions.
```

---

## 27. Recommended Local Study Workflow

### Step 1: Clone Upstream

```bash
git clone https://github.com/QwenLM/qwen-code.git external/qwen-code
cd external/qwen-code
```

### Step 2: Inspect Structure

```bash
find packages -maxdepth 3 -type d | sort
find .qwen -maxdepth 3 -type f | sort
find docs -maxdepth 3 -type f | sort
```

### Step 3: Create a Plunder Map

Create:

```text
docs/plunder/QWEN_CODE_PLUNDER_MAP.md
```

Template:

```md
# Qwen Code Plunder Map

## Upstream

Project: Qwen Code  
Repository: QwenLM/qwen-code  
License: Apache-2.0  
Based on: Google Gemini CLI  

## Targeted Areas

| Upstream Path | Local Target | Status | Notes |
|---|---|---|---|
| packages/core/src/qwen | mythic_cli/parsers/qwen | studying | Qwen-Coder parser adaptations |
| packages/core/src/models | mythic_cli/models | planned | Multi-provider model config |
| packages/core/src/permissions | mythic_cli/permissions | planned | Approval modes |
| packages/core/src/subagents | .mythic/agents | planned | Role-agent system |
| packages/core/src/skills | .mythic/skills | planned | Skill packet system |
| packages/core/src/mcp | mythic_cli/mcp | planned | MCP integration |
| packages/core/src/hooks | mythic_cli/hooks | planned | Lifecycle extension points |
| packages/core/src/lsp | mythic_cli/lsp | studying | Code intelligence layer |
| packages/cli/src/nonInteractive | mythic_cli/headless | planned | Automation / CI mode |
| packages/cli/src/patches | mythic_cli/patching | planned | Patch preview/apply |
```

### Step 4: Copy One Subsystem at a Time

```bash
git checkout -b adapt-qwen-code-parser-patterns
```

### Step 5: Commit With Attribution

```bash
git commit -m "Adapt parser architecture patterns from Qwen Code

- Adds Apache-2.0 attribution
- Preserves upstream Qwen/Gemini notices where present
- Marks modified files
- Reworks parser layer for Mythic CLI model providers"
```

---

## 28. Suggested README Attribution

```md
## Third-Party Attribution

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected architectural patterns and code from Qwen Code, also licensed under Apache-2.0.

Qwen Code is an open-source terminal AI agent from QwenLM.

Qwen Code identifies itself as based on Google Gemini CLI. Where adapted files contain inherited Google/Gemini notices, those notices are preserved.

This project is independent and is not affiliated with, endorsed by, or sponsored by QwenLM, Alibaba Cloud, Google, or the Gemini CLI team.
```

---

## 29. Mythic CLI Adaptation Map

### 29.1 Agent Core

Qwen inspiration:

```text
packages/core/src/core
packages/core/src/agents
packages/core/src/subagents
packages/core/src/tools
```

Mythic target:

```text
mythic_cli/agent_core/
  loop.ts
  router.ts
  subagents.ts
  tool_executor.ts
```

---

### 29.2 Qwen/Model Parser Layer

Qwen inspiration:

```text
packages/core/src/qwen
packages/core/src/models
```

Mythic target:

```text
mythic_cli/parsers/
  qwen_parser.ts
  openai_parser.ts
  anthropic_parser.ts
  gemini_parser.ts
  local_model_parser.ts
```

---

### 29.3 Tool Law

Qwen inspiration:

```text
packages/core/src/tools
packages/core/src/permissions
packages/core/src/confirmation-bus
```

Mythic target:

```text
mythic_cli/tools/
  registry.ts
  executor.ts
  permissions.ts
  approvals.ts
```

---

### 29.4 Skills

Qwen inspiration:

```text
packages/core/src/skills
.qwen/skills
```

Mythic target:

```text
.mythic/skills/
  architecture-audit/
  repo-cartography/
  patch-forge/
  test-repair/
  doc-scribe/
```

---

### 29.5 SubAgents

Qwen inspiration:

```text
packages/core/src/subagents
.qwen/agents
```

Mythic target:

```text
.mythic/agents/
  architect.md
  forge-worker.md
  auditor.md
  cartographer.md
  scribe.md
```

---

### 29.6 MCP Gate

Qwen inspiration:

```text
packages/core/src/mcp
docs/features/mcp
```

Mythic target:

```text
mythic_cli/mcp/
  config.ts
  server_registry.ts
  tool_bridge.ts
  resource_bridge.ts
```

---

### 29.7 Headless Automation

Qwen inspiration:

```text
packages/cli/src/nonInteractive
packages/cli/src/nonInteractiveCli.ts
packages/cli/src/dualOutput
```

Mythic target:

```text
mythic_cli/headless/
  run.ts
  stdin.ts
  output_json.ts
  stream_events.ts
```

---

### 29.8 Hooks and Scheduled Tasks

Qwen inspiration:

```text
packages/core/src/hooks
scheduled tasks docs
```

Mythic target:

```text
mythic_cli/hooks/
mythic_cli/scheduler/
```

---

## 30. Final Checklist Before Publishing

Before pushing your adapted CLI publicly:

* [ ] Your repo has `LICENSE`.
* [ ] Your repo uses Apache-2.0 or another compatible strategy.
* [ ] Your repo has `NOTICE`.
* [ ] Your repo has `THIRD_PARTY_NOTICES.md`.
* [ ] Your README credits Qwen Code.
* [ ] Your README credits Gemini CLI where inherited Qwen material makes that relevant.
* [ ] Modified files have prominent change notices.
* [ ] Original copyright/SPDX headers are preserved.
* [ ] You removed Qwen/Alibaba/Google/Gemini branding from your own product identity.
* [ ] You did not copy deprecated Qwen OAuth assumptions.
* [ ] You did not blindly copy Alibaba Cloud billing or Coding Plan logic.
* [ ] You documented copied/adapted areas in a plunder map.
* [ ] You tested each adapted subsystem.
* [ ] You can explain every copied dependency.
* [ ] Dangerous modes cannot be silently enabled.
* [ ] MCP tools are trust-scoped and filterable.
* [ ] Patch handling protects user work.
* [ ] Provider-specific auth is rewritten for your own CLI’s config law.

---

## 31. Clean Rule

```text
Copy the architecture.
Respect the license.
Preserve attribution.
Mark your changes.
Do not steal the branding.
Rewrite provider-specific service logic.
Study Qwen’s parser adaptations carefully.
Keep the agentic terminal wisdom.
```

Qwen Code is especially valuable because it is a **Gemini CLI-derived TypeScript agentic terminal architecture adapted for Qwen-Coder-style models**.

The real treasure is not one file.

The treasure is the pattern language:

* CLI/core separation
* provider flexibility
* parser adaptation
* SubAgents
* Skills
* MCP
* headless mode
* approvals
* sandboxing
* hooks
* LSP
* scheduled tasks
* extension architecture
* SDK access

For your own CLI, Qwen Code is not just another tool to copy.

It is a map of how a serious open-source AI coding agent evolves once it starts becoming an ecosystem.

[1]: https://github.com/QwenLM/qwen-code "GitHub - QwenLM/qwen-code: An open-source AI agent that lives in your terminal. · GitHub"
[2]: https://qwenlm.github.io/qwen-code-docs/en/developers/extensions/getting-started-extensions/ "Getting Started with Qwen Code Extensions | Qwen Code Docs"
[3]: https://github.com/QwenLM/qwen-code/tree/main/packages "qwen-code/packages at main · QwenLM/qwen-code · GitHub"
[4]: https://qwenlm.github.io/qwen-code-docs/en/developers/architecture/ "Qwen Code Architecture Overview | Qwen Code Docs"
[5]: https://github.com/QwenLM/qwen-code/tree/main/packages/core/src "qwen-code/packages/core/src at main · QwenLM/qwen-code · GitHub"
[6]: https://github.com/QwenLM/qwen-code/tree/main/packages/cli/src "qwen-code/packages/cli/src at main · QwenLM/qwen-code · GitHub"
[7]: https://github.com/QwenLM/qwen-code/tree/main/.qwen "qwen-code/.qwen at main · QwenLM/qwen-code · GitHub"
[8]: https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/ "Subagents | Qwen Code Docs"
[9]: https://qwenlm.github.io/qwen-code-docs/en/users/features/skills/ "Agent Skills | Qwen Code Docs"
[10]: https://qwenlm.github.io/qwen-code-docs/en/users/features/headless/ "Headless Mode | Qwen Code Docs"
[11]: https://qwenlm.github.io/qwen-code-docs/en/users/features/mcp/ "Connect Qwen Code to tools via MCP | Qwen Code Docs"
[12]: https://qwenlm.github.io/qwen-code-docs/en/users/features/approval-mode/ "Approval Mode | Qwen Code Docs"
[13]: https://qwenlm.github.io/qwen-code-docs/en/users/features/sandbox/ "Sandbox | Qwen Code Docs"
[14]: https://qwenlm.github.io/qwen-code-docs/en/users/features/hooks/ "Qwen Code Hooks Documentation | Qwen Code Docs"
[15]: https://qwenlm.github.io/qwen-code-docs/en/users/features/scheduled-tasks/ "Run Prompts on a Schedule | Qwen Code Docs"
[16]: https://qwenlm.github.io/qwen-code-docs/en/users/features/lsp/ "Language Server Protocol (LSP) Support | Qwen Code Docs"
[17]: https://qwenlm.github.io/qwen-code-docs/en/users/configuration/model-providers/ "Model Providers | Qwen Code Docs"
[18]: https://qwenlm.github.io/qwen-code-docs/en/developers/sdk-typescript/ "Typescript SDK | Qwen Code Docs"
[19]: https://qwenlm.github.io/qwen-code-docs/en/users/features/commands/ "Commands | Qwen Code Docs"
