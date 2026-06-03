# Lawful Code-Raiding Guide: Reusing Apache-2.0 Code from Kimi CLI

## Purpose

This guide explains how to safely reuse code from **MoonshotAI/kimi-cli** inside your own Apache-2.0 CLI project.

Kimi CLI is published as an **Apache-2.0** project, and its README describes it as a terminal AI agent that can read and edit code, execute shell commands, fetch web pages, and plan actions during execution. ([GitHub][1])

This is not legal advice. It is a practical open-source hygiene guide.

---

## Core Rule

Because both projects use **Apache License 2.0**, you can reuse, modify, merge, and redistribute Kimi CLI code inside your own CLI project, as long as you preserve the required license and attribution notices.

Apache-2.0 grants permission to reproduce, create derivative works from, sublicense, and distribute the work in source or object form. ([GitHub][2])

In Viking terms:

> Take the useful steel.
> Keep the maker’s mark.
> Forge it into your own weapon.

---

# 1. What You Are Allowed To Do

Under Apache-2.0, you may:

* Copy code from Kimi CLI.
* Modify that code.
* Merge it into your own CLI project.
* Rewrite parts of it.
* Ship it inside your own Apache-2.0 repo.
* Use it commercially.
* Build your own branding, architecture, and agent system around it.

You do **not** need to ask MoonshotAI for permission if you follow the Apache-2.0 terms.

---

# 2. What You Must Do

## 2.1 Keep an Apache-2.0 License File

Your project should include a root-level file:

```text
LICENSE
```

That file should contain the Apache License 2.0 text.

Apache requires that recipients of redistributed work or derivative works receive a copy of the license. ([GitHub][2])

---

## 2.2 Preserve Attribution Notices

When you copy code, keep any copyright, patent, trademark, and attribution notices that apply to the copied material.

Apache-2.0 requires derivative works to retain applicable notices from the original source form. ([GitHub][2])

Do **not** remove original headers just because you changed the code.

---

## 2.3 Mark Modified Files

If you modify files copied from Kimi CLI, mark them clearly.

Apache-2.0 requires modified files to carry prominent notices stating that the files were changed. ([GitHub][2])

Example Python header:

```python
# Portions adapted from MoonshotAI/kimi-cli.
# Modified by Volmarr / RuneForgeAI, 2026.
# Licensed under the Apache License, Version 2.0.
```

Example Markdown header:

```md
<!--
Portions adapted from MoonshotAI/kimi-cli.
Modified by Volmarr / RuneForgeAI, 2026.
Licensed under the Apache License, Version 2.0.
-->
```

Example TypeScript header:

```ts
// Portions adapted from MoonshotAI/kimi-cli.
// Modified by Volmarr / RuneForgeAI, 2026.
// Licensed under the Apache License, Version 2.0.
```

---

## 2.4 Add a NOTICE File

Kimi CLI includes a `NOTICE` file. It identifies **Kimi Code CLI**, credits **Moonshot AI**, and says the project contains or reuses Apache-2.0 licensed code from **OpenAI Codex**. ([GitHub][3])

Because Kimi CLI has a `NOTICE`, your derivative project should include a readable attribution notice too. Apache-2.0 requires derivative distributions to include relevant NOTICE attributions when the source project includes a NOTICE file. ([GitHub][2])

Create or update:

```text
NOTICE
```

Suggested template:

```md
# NOTICE

[Your CLI Project Name]

Copyright 2026 Volmarr / RuneForgeAI

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts portions of software from:

## Kimi Code CLI

Copyright 2025 Moonshot AI

Licensed under the Apache License, Version 2.0.

Original project: MoonshotAI/kimi-cli

Kimi Code CLI includes software developed at Moonshot AI.

The Kimi Code CLI project also contains or reuses Apache-2.0 licensed code from:

## OpenAI Codex

Copyright 2025 OpenAI

This attribution is preserved because portions of Kimi Code CLI identify OpenAI Codex as an upstream source.
```

---

# 3. What You Should Not Do

## 3.1 Do Not Use Their Branding as Your Own

Apache-2.0 does **not** grant permission to use the licensor’s trade names, trademarks, service marks, or product names, except for reasonable attribution. ([GitHub][2])

So this is okay:

```md
This project contains code adapted from MoonshotAI/kimi-cli.
```

This is not okay:

```md
This is the official Kimi CLI by MoonshotAI.
```

Also avoid naming your tool:

* Kimi CLI
* Kimi Code
* Moonshot CLI
* Official Kimi Agent
* MoonshotAI Agent

Unless you are only using those names for attribution.

---

## 3.2 Do Not Hide the Source of Copied Code

Bad:

```md
All code written from scratch by this project.
```

Good:

```md
This project contains original code plus adapted portions from MoonshotAI/kimi-cli, used under the Apache License 2.0.
```

---

## 3.3 Do Not Copy Secrets, Tokens, Generated Build Artifacts, or Private Config

Only copy source code, docs, tests, architecture patterns, and reusable public assets.

Avoid copying:

* API keys
* Local config files
* User-specific settings
* Generated caches
* Build artifacts
* Branding assets that may have separate trademark concerns
* Anything not clearly covered by the repo license

---

# 4. Best Code-Raiding Workflow

## Step 1: Clone Kimi CLI Separately

Keep it outside your own repo while studying it.

```bash
git clone https://github.com/MoonshotAI/kimi-cli.git external/kimi-cli
```

Do not immediately dump the whole thing into your project.

---

## Step 2: Identify the Subsystems Worth Reusing

Good places to study:

| Area             | Why It Matters                                |
| ---------------- | --------------------------------------------- |
| `src/kimi_cli`   | Main CLI and agent structure                  |
| `packages`       | Internal abstractions and reusable components |
| `sdks`           | SDK patterns                                  |
| `tests`          | Normal test structure                         |
| `tests_ai`       | AI behavior testing patterns                  |
| `tests_e2e`      | End-to-end CLI testing                        |
| `AGENTS.md`      | Agent behavior rules                          |
| `pyproject.toml` | Python project structure                      |
| `Makefile`       | Development workflow                          |
| `docs`           | Architecture and usage patterns               |
| `web`            | Embedded UI or web panel patterns             |

---

## Step 3: Copy One Subsystem at a Time

Do not copy everything at once.

Use a controlled process:

```text
1. Pick one subsystem.
2. Copy it into a temporary branch.
3. Rename modules to fit your project.
4. Add attribution headers.
5. Update NOTICE.
6. Run tests.
7. Commit with clear attribution.
```

Example branch:

```bash
git checkout -b adapt-kimi-cli-terminal-loop
```

Example commit message:

```text
Adapt terminal loop structure from MoonshotAI/kimi-cli

- Preserves Apache-2.0 attribution
- Adds modified-file notices
- Updates NOTICE with MoonshotAI and inherited OpenAI Codex attribution
- Renames modules for RuneForgeAI CLI architecture
```

---

# 5. Recommended Repo Files

Your repo should contain:

```text
LICENSE
NOTICE
README.md
THIRD_PARTY_NOTICES.md
```

`THIRD_PARTY_NOTICES.md` is optional, but useful if your project starts incorporating code from multiple open-source sources.

---

# 6. Suggested `THIRD_PARTY_NOTICES.md`

```md
# Third-Party Notices

This project includes or adapts code from third-party open-source projects.

## MoonshotAI/kimi-cli

License: Apache License 2.0

Usage:

- Selected CLI architecture patterns
- Selected agent-loop patterns
- Selected testing or development workflow patterns
- Selected utility code where explicitly marked in source files

Attribution:

Kimi Code CLI  
Copyright 2025 Moonshot AI

## OpenAI Codex

License: Apache License 2.0

Usage:

This attribution is inherited where code adapted from MoonshotAI/kimi-cli identifies OpenAI Codex as an upstream Apache-2.0 source.

Attribution:

OpenAI Codex  
Copyright 2025 OpenAI
```

---

# 7. Suggested File Header Policy

Use headers only for files that contain meaningful copied or adapted code.

## Lightly Adapted File

Use this when the structure is still clearly from Kimi CLI:

```python
# Portions adapted from MoonshotAI/kimi-cli.
# Original work Copyright 2025 Moonshot AI.
# Modified by Volmarr / RuneForgeAI, 2026.
# Licensed under the Apache License, Version 2.0.
```

## Heavily Rewritten File

Use this when the original inspired the design, but much of the code has been rewritten:

```python
# Inspired by architectural patterns from MoonshotAI/kimi-cli.
# This file has been substantially rewritten for [Your Project Name].
# Modified by Volmarr / RuneForgeAI, 2026.
# Licensed under the Apache License, Version 2.0.
```

## Original File With No Copied Code

No third-party header needed.

```python
# Copyright 2026 Volmarr / RuneForgeAI.
# Licensed under the Apache License, Version 2.0.
```

---

# 8. Practical Copying Strategy

## Best Things to Reuse Directly

These are usually safer to adapt:

* CLI command structure
* Test organization
* Config loading patterns
* Agent loop patterns
* Tool registration structure
* Logging patterns
* Terminal UX ideas
* Documentation structure
* Build commands
* Packaging setup

## Things to Rewrite More Carefully

These may be deeply tied to Kimi’s own ecosystem:

* Authentication
* Kimi-specific APIs
* Moonshot-specific service integrations
* Branding strings
* Telemetry
* Web UI branding
* Model routing tied to Kimi services
* Marketplace or extension integrations

## Things to Avoid Copying Blindly

* Logos
* Product names
* API endpoints that require Kimi credentials
* Private assumptions about Moonshot infrastructure
* Anything with unclear generated or binary provenance

---

# 9. The best parts to study are likely:

Agent loop structure
CLI/session architecture
ACP integration
MCP handling
Web UI/session management
Skills system
Tests and e2e patterns
Config/provider architecture
Build/release workflow

# 10. Clean Attribution Checklist

Before publishing your adapted code, verify:

* [ ] Your repo has an Apache-2.0 `LICENSE`.
* [ ] Your repo has a `NOTICE`.
* [ ] Your `NOTICE` credits MoonshotAI/kimi-cli.
* [ ] Your `NOTICE` preserves inherited OpenAI Codex attribution where relevant.
* [ ] Copied files have modification notices.
* [ ] Original copyright notices are preserved.
* [ ] Your README does not imply official MoonshotAI affiliation.
* [ ] You removed Kimi/Moonshot branding from your own product identity.
* [ ] You renamed modules, commands, and package names appropriately.
* [ ] Tests pass after integration.
* [ ] You documented which subsystems were adapted.

---

# 11. Recommended README Attribution Section

Add this near the bottom of your README:

```md
## Third-Party Attribution

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts portions of software from MoonshotAI/kimi-cli, also licensed under Apache-2.0.

Kimi Code CLI is copyright 2025 Moonshot AI.

Some attribution may also be inherited from Kimi Code CLI for Apache-2.0 licensed portions originally derived from OpenAI Codex.

This project is independent and is not affiliated with, endorsed by, or sponsored by Moonshot AI or OpenAI.
```

---

# 12. Final Rule of Thumb

You can copy Apache-2.0 code aggressively, but not silently.

The clean rule is:

> **Copy the code. Keep the license. Preserve the notices. Mark your changes. Do not steal the branding.**

That gives you a lawful, open-source, battle-ready path for using Kimi CLI as raw material for your own CLI forge.

[1]: https://github.com/MoonshotAI/kimi-cli "GitHub - MoonshotAI/kimi-cli: Kimi Code CLI is your next CLI agent. · GitHub"
[2]: https://github.com/MoonshotAI/kimi-cli/blob/main/LICENSE "kimi-cli/LICENSE at main · MoonshotAI/kimi-cli · GitHub"
[3]: https://github.com/MoonshotAI/kimi-cli/blob/main/NOTICE "kimi-cli/NOTICE at main · MoonshotAI/kimi-cli · GitHub"
