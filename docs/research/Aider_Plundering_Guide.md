# Aider Plundering Guide

## Purpose

This guide explains how to lawfully study, reuse, adapt, and “plunder” useful architecture from **Aider** for your own Apache-2.0 CLI project.

Aider is an open-source AI pair-programming tool that runs in the terminal, edits files in a local Git repo, maps the codebase, applies changes, runs tests/linters, supports many LLM providers, and can be scripted from the command line or Python. ([GitHub][1])

This is practical open-source hygiene, not legal advice.

---

## 1. Core Legal Position

Aider is licensed under **Apache License 2.0**, so it is in the same broad license family as the other lawful plunder targets we have been mapping. GitHub lists the repo as Apache-2.0 licensed, and the Aider FAQ says Aider is open source on GitHub under Apache 2.0. ([GitHub][1])

Apache-2.0 generally allows you to:

* copy code
* modify code
* redistribute modified versions
* use it commercially
* merge useful portions into your own Apache-2.0 project
* build derivative systems from adapted pieces

But you must preserve required license and attribution notices, mark modified files, and avoid implying that your project is official Aider branding. The Apache-2.0 text also makes clear that trademark rights are **not** granted except as needed for normal attribution. ([GitHub][2])

> Take the useful steel.
> Keep the maker’s mark.
> Forge your own blade.

---

## 2. Required Source Links

Use these as canonical upstream references in your repo docs.

### Main Links

* **Aider GitHub Repository** — main source repo. ([GitHub][1])
* **Aider License** — Apache License 2.0 text. ([GitHub][2])
* **Aider Documentation Home** — full docs index. ([Aider][3])
* **Configuration Docs** — command-line options, `.aider.conf.yml`, environment variables, and `.env` support. ([Aider][4])
* **In-Chat Commands** — `/add`, `/ask`, `/architect`, `/run`, `/test`, `/map`, `/undo`, `/web`, etc. ([Aider][5])
* **Repository Map Docs** — concise whole-repo symbol map and graph-ranking optimization. ([Aider][6])
* **Edit Formats Docs** — `whole`, `diff`, `diff-fenced`, `udiff`, editor formats. ([Aider][7])
* **Linting and Testing Docs** — automatic lint/test repair loops. ([Aider][8])
* **Scripting Docs** — one-shot `--message`, command-line scripting, Python scripting. ([Aider][9])
* **IDE Watch Mode Docs** — `--watch-files` and `AI!` / `AI?` trigger comments. ([Aider][10])
* **Coding Conventions Docs** — read-only convention files such as `CONVENTIONS.md`. ([Aider][11])
* **Model Aliases Docs** — model aliasing from CLI/config and priority rules. ([Aider][12])
* **FAQ** — open-source/license note and scripting reference. ([Aider][13])

---

## 3. Core Apache-2.0 Duties

## 3.1 Keep the License

Your project should include:

```text
LICENSE
```

Use Apache License 2.0 if your project is already Apache-2.0.

Apache-2.0 requires redistributed derivative works to provide the license, preserve applicable notices, and mark modified files. ([GitHub][2])

---

## 3.2 Preserve Notices

When copying files or meaningful chunks from Aider:

* preserve upstream copyright/license headers
* preserve SPDX headers if present
* preserve notices in copied files
* do not remove references to Aider upstream authorship
* do not claim copied code was written entirely from scratch

Suggested Python header:

```python
# Portions adapted from Aider-AI/aider.
# Upstream project: Aider, licensed under Apache License 2.0.
# Modified by Volmarr / RuneForgeAI, 2026.
# Licensed under the Apache License, Version 2.0.
```

Suggested Markdown header:

```md
<!--
Portions adapted from Aider-AI/aider.
Upstream project: Aider, licensed under Apache License 2.0.
Modified by Volmarr / RuneForgeAI, 2026.
Licensed under the Apache License, Version 2.0.
-->
```

---

## 3.3 Add Third-Party Notices

Recommended repo files:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/AIDER_PLUNDER_GUIDE.md
docs/plunder/AIDER_PLUNDER_MAP.md
```

Suggested `NOTICE`:

```md
# NOTICE

[Your CLI Project Name]

Copyright 2026 Volmarr / RuneForgeAI

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected portions of software from:

## Aider

Project: Aider  
Repository: Aider-AI/aider  
License: Apache License 2.0

Aider is an open-source AI pair-programming tool for the terminal.

This project is independent and is not affiliated with, endorsed by, or sponsored by Aider AI LLC, Aider-AI, or the Aider project.
```

Suggested `THIRD_PARTY_NOTICES.md`:

```md
# Third-Party Notices

This project includes or adapts material from third-party open-source projects.

## Aider

Project: Aider  
Repository: Aider-AI/aider  
License: Apache License 2.0  

Usage:

This project may include or adapt selected portions of Aider, especially architectural patterns related to:

- terminal AI pair programming
- Git-aware editing
- repository maps
- search/replace edit blocks
- unified diff edit formats
- model-specific edit formats
- chat command routing
- automatic commits
- lint/test repair loops
- scripting mode
- file watch mode
- coding convention files
- model aliases
- multi-provider LLM configuration
- browser/web scraping context
- chat history handling
- patch and diff utilities

This project is independent and is not affiliated with, endorsed by, or sponsored by Aider AI LLC, Aider-AI, or the Aider project.
```

---

## 4. Branding Warning

Apache-2.0 lets you reuse code. It does **not** let you steal the project’s identity.

Safe wording:

```md
This project includes code adapted from Aider-AI/aider.
```

Unsafe wording:

```md
This is the official Aider CLI.
```

Avoid names like:

* Official Aider Fork
* Aider Pro
* Aider Code Agent
* Aider Mythic Edition
* Aider AI Official CLI

Use “Aider” only for attribution and source description.

---

## 5. Repo Structure Worth Studying

Aider is primarily a Python project. The root repo has major areas including `.github`, `aider`, `benchmark`, `docker`, `requirements`, `scripts`, and `tests`; GitHub currently shows a large history, many stars/forks, and an active issue/PR ecosystem. ([GitHub][1])

The most important source directory is:

```text
aider/
```

The `aider/` package includes major files and folders such as:

```text
aider/
  coders/
  queries/
  resources/
  website/
  __main__.py
  analytics.py
  args.py
  commands.py
  diffs.py
  editor.py
  history.py
  io.py
  linter.py
  llm.py
  main.py
  models.py
  openrouter.py
  prompts.py
  repo.py
  repomap.py
  run_cmd.py
  scrape.py
  sendchat.py
  urls.py
  utils.py
  voice.py
  watch.py
  watch_prompts.py
```

The visible repo tree confirms the presence of these core files, including `commands.py`, `linter.py`, `llm.py`, `main.py`, `models.py`, `repo.py`, `repomap.py`, `run_cmd.py`, `scrape.py`, `sendchat.py`, `voice.py`, and `watch.py`. ([GitHub][14])

---

## 6. Highest-Value Plunder Targets

## 6.1 `aider/coders/` — Core Editing Engines

This is probably the richest directory to study.

The `aider/coders/` directory contains multiple coder implementations and prompt files, including architect mode, ask mode, context mode, edit block formats, fenced edit blocks, patch mode, search/replace, unified diff, and whole-file editing. ([GitHub][15])

Likely valuable files:

```text
aider/coders/base_coder.py
aider/coders/base_prompts.py
aider/coders/architect_coder.py
aider/coders/architect_prompts.py
aider/coders/ask_coder.py
aider/coders/context_coder.py
aider/coders/editblock_coder.py
aider/coders/editblock_prompts.py
aider/coders/search_replace.py
aider/coders/patch_coder.py
aider/coders/patch_prompts.py
aider/coders/udiff_coder.py
aider/coders/udiff_prompts.py
aider/coders/wholefile_coder.py
aider/coders/wholefile_prompts.py
```

### Why It Matters

Aider’s edit-format design is one of its biggest treasures. It supports multiple edit formats because different model families follow different editing instructions with different reliability. The docs describe `whole`, `diff`, `diff-fenced`, `udiff`, and editor-specific variants. ([Aider][7])

### Mythic CLI Adaptation

```text
mythic_cli/coders/
  base_coder.py
  architect_coder.py
  ask_coder.py
  patch_coder.py
  search_replace_coder.py
  unified_diff_coder.py
  whole_file_coder.py
  prompts/
```

Design law:

```md
## Edit Format Law

Do not force every model into one patch format.

Different models need different editing protocols:

- whole-file replacement
- search/replace blocks
- fenced search/replace blocks
- unified diff
- model-specific patch format
- architect/editor split
```

---

## 6.2 Repository Map — `aider/repomap.py`

Aider’s repo map is extremely worth studying.

The docs say Aider builds a concise map of the whole Git repo, including important classes, methods, functions, types, and call signatures. This helps the model understand code relationships without dumping the whole repository into context. ([Aider][6])

The repo map also uses graph ranking to select the most important parts of the codebase that fit inside a token budget. The docs mention `--map-tokens`, dynamic sizing, and relevance based on current chat state. ([Aider][6])

### Plunder Targets

```text
aider/repomap.py
aider/queries/
aider/queries/tree-sitter-language-pack/
aider/queries/tree-sitter-languages/
```

The `queries` directory contains Tree-sitter query resources, which are part of how Aider extracts code symbols from many languages. ([GitHub][16])

### Mythic CLI Adaptation

```text
mythic_cli/repomap/
  symbol_extractor.py
  graph_ranker.py
  token_budget.py
  language_queries/
  repo_map_renderer.py
```

Design law:

```md
## Repo Map Law

Do not make the model read the entire repo.

Give it a compressed map of:

- files
- symbols
- classes
- functions
- interfaces
- key signatures
- dependencies
- likely relevant modules
```

This is one of the most important things to steal conceptually for your **Norse Saga Engine** and **Mythic CLI** work.

---

## 6.3 Git Integration — `aider/repo.py`

Aider’s README emphasizes Git integration: it automatically commits changes with sensible commit messages and lets users diff, manage, and undo AI changes with normal Git tools. ([GitHub][1])

Plunder targets:

```text
aider/repo.py
aider/diffs.py
aider/commands.py
```

Interesting command patterns:

```text
/commit
/diff
/undo
/git
```

The command docs show `/commit`, `/diff`, `/git`, and `/undo` as built-in in-chat commands. ([Aider][5])

### Mythic CLI Adaptation

```text
mythic_cli/git/
  repo_state.py
  diff_view.py
  commit_manager.py
  undo_manager.py
  dirty_tree_guard.py
```

Design law:

```md
## Git Safety Law

Every AI edit should be Git-visible.

The CLI should:

- detect dirty state
- protect user edits
- show diffs
- commit AI changes separately
- generate useful commit messages
- allow safe undo
```

---

## 6.4 Command Router — `aider/commands.py`

Aider’s in-chat slash-command system is very useful. It supports commands like `/add`, `/ask`, `/architect`, `/code`, `/commit`, `/diff`, `/drop`, `/lint`, `/map`, `/model`, `/run`, `/test`, `/tokens`, `/undo`, `/voice`, and `/web`. ([Aider][5])

Plunder targets:

```text
aider/commands.py
aider/args.py
aider/args_formatter.py
aider/io.py
```

### Mythic CLI Adaptation

```text
mythic_cli/commands/
  registry.py
  add.py
  ask.py
  architect.py
  forge.py
  audit.py
  map.py
  test.py
  run.py
  model.py
  undo.py
```

Suggested commands:

```text
/architect
/forge
/audit
/cartograph
/scribe
/add
/drop
/read-only
/map
/map-refresh
/run
/test
/lint
/diff
/commit
/undo
/model
/tokens
/web
```

Design law:

```md
## Command Law

Slash commands are not just UX sugar.

They are explicit control surfaces for:

- context management
- model switching
- repo mapping
- testing
- shell execution
- Git state
- role switching
- safety boundaries
```

---

## 6.5 Architect Mode

Aider’s command docs include `/architect`, described as an architect/editor mode using two different models. The edit-format docs also explain that editor formats are used in architect mode, where the architect model resolves the task and gives plain-text instructions while the editor model produces the actual syntactic edits. ([Aider][5])

Plunder targets:

```text
aider/coders/architect_coder.py
aider/coders/architect_prompts.py
aider/coders/editor_*_coder.py
aider/coders/editor_*_prompts.py
```

### Mythic CLI Adaptation

```text
mythic_cli/roles/
  architect.py
  editor.py
  forge_worker.py
  auditor.py
```

Design law:

```md
## Architect/Editor Split

Separate design from mechanical editing.

The Architect decides:

- what should change
- why it should change
- what boundaries must hold

The Editor applies:

- exact file edits
- syntactic patches
- minimal mechanical transformation
```

This fits your existing **Architect / Forge Worker / Auditor / Scribe** model extremely well.

---

## 6.6 Lint/Test Repair Loop — `aider/linter.py`

Aider can automatically lint and test code after it makes changes. The docs say it can fix problems detected by linters and test suites; it can use built-in linters, custom `--lint-cmd`, per-language lint commands, `/test`, `--test-cmd`, and `--auto-test`. ([GitHub][1])

Plunder targets:

```text
aider/linter.py
aider/run_cmd.py
aider/commands.py
```

### Mythic CLI Adaptation

```text
mythic_cli/quality/
  lint_runner.py
  test_runner.py
  repair_loop.py
  command_result.py
```

Design law:

```md
## Repair Loop Law

A coding agent should not stop at "I edited the file."

It should:

1. edit
2. lint
3. test
4. read failures
5. repair
6. repeat within safe bounds
7. summarize what changed
```

---

## 6.7 Scripting Mode

Aider can be scripted from the command line or Python. Its docs show `--message` / `-m` for one-shot tasks that apply edits and exit, plus `--message-file` for loading instructions from a file. ([Aider][9])

Plunder targets:

```text
aider/main.py
aider/args.py
aider/sendchat.py
```

### Mythic CLI Adaptation

```bash
mythic --message "audit this repo for architecture drift"
mythic -m "add docstrings to these files" src/*.py
mythic --message-file docs/tasks/refactor_plan.md
```

Design law:

```md
## Scriptability Law

A serious AI CLI must support:

- interactive mode
- one-shot mode
- message-file mode
- shell scripting
- CI-friendly execution
- deterministic exit behavior
```

---

## 6.8 Watch Mode / IDE Comment Triggers — `aider/watch.py`

Aider can run with `--watch-files`, watch files in the repo, and respond to special AI comments. Comments with `AI!` trigger edits; comments with `AI?` trigger answers. ([Aider][10])

Plunder targets:

```text
aider/watch.py
aider/watch_prompts.py
```

### Mythic CLI Adaptation

```text
# Refactor this function to use the new routing layer. AI!
# Explain why this method exists. AI?
```

Design law:

```md
## Watch Mode Law

The editor can become the command surface.

AI comments should support:

- question triggers
- edit triggers
- file-local tasks
- lightweight IDE integration
- low-friction developer workflow
```

This is very compatible with your desire for CLI agents that can work alongside VS Code, GitHub, and repo docs without needing a heavy IDE plugin.

---

## 6.9 Coding Conventions / Read-Only Context

Aider supports loading coding convention files as read-only context. The docs recommend creating something like `CONVENTIONS.md` and loading it with `/read CONVENTIONS.md` or `aider --read CONVENTIONS.md`; `.aider.conf.yml` can always load conventions files. ([Aider][11])

Plunder targets:

```text
aider/commands.py
aider/prompts.py
aider/io.py
```

### Mythic CLI Adaptation

```text
MYTHIC.md
AGENTS.md
CONVENTIONS.md
DOMAIN_MAP.md
ARCHITECTURE.md
INTERFACE.md
```

Suggested config:

```yaml
read:
  - MYTHIC.md
  - AGENTS.md
  - DOMAIN_MAP.md
  - ARCHITECTURE.md
  - CONVENTIONS.md
```

Design law:

```md
## Standing Instruction Law

Project law should be loaded as read-only context.

The agent may obey it.

The agent may cite it.

The agent may not casually rewrite it.
```

---

## 6.10 Model Configuration and Aliases

Aider supports many LLM providers, including OpenAI, Anthropic, Gemini, Groq, LM Studio, xAI, Azure, Cohere, DeepSeek, Ollama, OpenRouter, GitHub Copilot, Vertex AI, Amazon Bedrock, and OpenAI-compatible APIs. The docs index lists all these provider sections. ([Aider][3])

Aider also supports model aliases from command line and config files, with priority order: command-line aliases, config aliases, then built-in aliases. ([Aider][12])

Plunder targets:

```text
aider/models.py
aider/llm.py
aider/openrouter.py
aider/args.py
```

### Mythic CLI Adaptation

```yaml
alias:
  - "architect:anthropic/claude-opus-4.6"
  - "forge:qwen/qwen3.5-coder"
  - "auditor:gpt-5.5-thinking"
  - "local:lmstudio/stheno-8b"
```

Design law:

```md
## Model Alias Law

Humans should not have to remember long provider model IDs.

Use role-based aliases:

- architect
- forge
- auditor
- scribe
- local
- cheap
- fast
- deep
```

---

## 6.11 Web and Image Context

Aider’s README says users can add images and web pages to the chat for screenshots, reference docs, and visual context. Its command docs include `/web` for scraping a webpage and sending it into the chat. ([GitHub][1])

Plunder targets:

```text
aider/scrape.py
aider/urls.py
aider/copypaste.py
```

### Mythic CLI Adaptation

```text
/web https://docs.example.com/api
/paste screenshot.png
/read docs/reference.md
```

Design law:

```md
## External Context Law

A coding agent should be able to ingest:

- docs URLs
- screenshots
- copied text
- local docs
- error logs
- design notes
```

---

## 6.12 Chat History and Shareable Logs

Aider stores/shareable chat logs; the FAQ says users can share `.aider.chat.history.md` by publishing it and using Aider’s share viewer. ([Aider][13])

Plunder targets:

```text
aider/history.py
aider/mdstream.py
aider/io.py
```

### Mythic CLI Adaptation

```text
.mythic/history/
  chat.history.md
  session.jsonl
  summaries/
```

Design law:

```md
## Session Memory Law

Every important coding session should leave behind:

- chat transcript
- changed files
- commands run
- test/lint results
- final summary
- follow-up tasks
```

---

## 6.13 Benchmark System

Aider has a `benchmark/` directory and publishes LLM leaderboards in its docs. The docs index includes code editing and refactoring leaderboards, benchmark notes, and contributed results. ([Aider][3])

Plunder targets:

```text
benchmark/
aider/website/docs/leaderboards/
tests/
```

### Mythic CLI Adaptation

```text
benchmarks/
  code_editing/
  refactoring/
  bug_fixing/
  doc_update/
  repo_map_quality/
```

Design law:

```md
## Benchmark Law

Do not judge a coding agent only by vibes.

Test it against repeatable tasks:

- edit accuracy
- patch correctness
- refactor safety
- test repair
- repo map usefulness
- multi-file change success
```

---

## 7. Suggested Plunder Priority

### Tier 1 — Highest Value

Study first:

```text
aider/coders/
aider/repomap.py
aider/repo.py
aider/commands.py
aider/diffs.py
aider/linter.py
aider/run_cmd.py
aider/models.py
aider/llm.py
aider/main.py
```

These are the bones: edit engines, repo map, Git, commands, lint/test loop, models, and runtime.

---

### Tier 2 — Mythic Engineering Power Systems

Study next:

```text
aider/watch.py
aider/watch_prompts.py
aider/prompts.py
aider/history.py
aider/sendchat.py
aider/io.py
aider/scrape.py
aider/openrouter.py
aider/voice.py
```

These are workflow multipliers: IDE trigger comments, standing prompts, session memory, web context, provider integration, and voice.

---

### Tier 3 — Support Infrastructure

Study later:

```text
tests/
benchmark/
docker/
requirements/
scripts/
aider/website/
```

These are build, packaging, docs, benchmark, and ecosystem support systems.

---

## 8. What Not To Plunder Blindly

Be careful with:

* Aider branding
* analytics defaults
* web UI branding
* provider-specific assumptions
* install scripts
* undocumented internal behavior
* model defaults that may change
* benchmark data without understanding methodology
* prompt wording that is too Aider-specific
* files with third-party code or assets you have not reviewed
* any system that commits with flags you do not want in your own workflow

The clean strategy:

```md
Copy architecture aggressively.

Copy implementation selectively.

Rewrite branding, analytics, provider defaults, and project-specific assumptions.
```

---

## 9. Recommended Local Study Workflow

### Step 1: Clone Upstream

```bash
git clone https://github.com/Aider-AI/aider.git external/aider
cd external/aider
```

### Step 2: Inspect Structure

```bash
find aider -maxdepth 2 -type f | sort
find aider/coders -maxdepth 1 -type f | sort
find tests -maxdepth 2 -type f | sort
```

### Step 3: Create a Plunder Map

Create:

```text
docs/plunder/AIDER_PLUNDER_MAP.md
```

Template:

```md
# Aider Plunder Map

## Upstream

Project: Aider  
Repository: Aider-AI/aider  
License: Apache-2.0  

## Targeted Areas

| Upstream Path | Local Target | Status | Notes |
|---|---|---|---|
| aider/coders/base_coder.py | mythic_cli/coders/base.py | studying | Core coder loop |
| aider/coders/search_replace.py | mythic_cli/patching/search_replace.py | planned | Search/replace edit blocks |
| aider/repomap.py | mythic_cli/repomap/ | planned | Whole-repo symbol map |
| aider/repo.py | mythic_cli/git/repo_state.py | planned | Git state and commits |
| aider/commands.py | mythic_cli/commands/registry.py | planned | Slash command routing |
| aider/linter.py | mythic_cli/quality/lint_runner.py | planned | Lint/test repair loop |
| aider/watch.py | mythic_cli/watch/ | studying | AI comment triggers |
| aider/models.py | mythic_cli/models/registry.py | planned | Model metadata and aliases |
```

### Step 4: Copy One Subsystem at a Time

```bash
git checkout -b adapt-aider-repomap-patterns
```

### Step 5: Commit With Attribution

```bash
git commit -m "Adapt repository-map patterns from Aider

- Adds Apache-2.0 attribution
- Marks modified files
- Updates THIRD_PARTY_NOTICES.md
- Reworks repo map for Mythic CLI architecture"
```

---

## 10. README Attribution Template

```md
## Third-Party Attribution

This project is licensed under the Apache License, Version 2.0.

This project includes or adapts selected architectural patterns and code from Aider, also licensed under Apache-2.0.

Aider is an open-source AI pair-programming tool for the terminal.

This project is independent and is not affiliated with, endorsed by, or sponsored by Aider AI LLC, Aider-AI, or the Aider project.
```

---

## 11. Mythic CLI Adaptation Map

### 11.1 Coder Core

Aider inspiration:

```text
aider/coders/base_coder.py
aider/coders/*_coder.py
aider/coders/*_prompts.py
```

Mythic target:

```text
mythic_cli/coders/
  base.py
  architect.py
  editor.py
  search_replace.py
  unified_diff.py
  whole_file.py
```

---

### 11.2 Repo Map

Aider inspiration:

```text
aider/repomap.py
aider/queries/
```

Mythic target:

```text
mythic_cli/repomap/
  extractor.py
  graph_rank.py
  renderer.py
  token_budget.py
```

---

### 11.3 Git Safety

Aider inspiration:

```text
aider/repo.py
aider/diffs.py
```

Mythic target:

```text
mythic_cli/git/
  repo.py
  diff.py
  commit.py
  undo.py
```

---

### 11.4 Commands

Aider inspiration:

```text
aider/commands.py
```

Mythic target:

```text
mythic_cli/commands/
  registry.py
  architect.py
  forge.py
  audit.py
  map.py
  test.py
  run.py
```

---

### 11.5 Quality Loop

Aider inspiration:

```text
aider/linter.py
aider/run_cmd.py
```

Mythic target:

```text
mythic_cli/quality/
  lint.py
  test.py
  repair_loop.py
```

---

### 11.6 Watch Mode

Aider inspiration:

```text
aider/watch.py
aider/watch_prompts.py
```

Mythic target:

```text
mythic_cli/watch/
  file_watcher.py
  ai_comment_parser.py
  trigger_router.py
```

---

### 11.7 Model Layer

Aider inspiration:

```text
aider/models.py
aider/llm.py
aider/openrouter.py
```

Mythic target:

```text
mythic_cli/models/
  providers.py
  aliases.py
  metadata.py
  openrouter.py
  local.py
```

---

## 12. Final Checklist Before Publishing

Before pushing your adapted CLI publicly:

* [ ] Your repo has `LICENSE`.
* [ ] Your repo uses Apache-2.0 or a compatible strategy.
* [ ] Your repo has `NOTICE`.
* [ ] Your repo has `THIRD_PARTY_NOTICES.md`.
* [ ] Your README credits Aider where relevant.
* [ ] Modified files have prominent change notices.
* [ ] Original copyright/SPDX/license headers are preserved.
* [ ] You removed Aider branding from your own product identity.
* [ ] You documented copied/adapted areas in a plunder map.
* [ ] You tested each adapted subsystem.
* [ ] You understand every copied dependency.
* [ ] Git operations protect user work.
* [ ] Patch/edit formats fail safely.
* [ ] Auto-commit behavior is configurable.
* [ ] Lint/test loops have bounded retry behavior.
* [ ] Analytics or telemetry defaults are removed or made explicit.
* [ ] Provider-specific assumptions are rewritten for your own config law.

---

## 13. Clean Rule

```text
Copy the architecture.
Respect the license.
Preserve attribution.
Mark your changes.
Do not steal the branding.
Rewrite provider-specific assumptions.
Protect Git history.
Study the repo map deeply.
```

Aider is especially valuable because it is not just another terminal agent. It is a mature pattern-library for **Git-native AI pair programming**:

* repository maps
* edit formats
* search/replace blocks
* architect/editor split
* auto-commit discipline
* lint/test repair loops
* slash-command UX
* scripting mode
* IDE comment triggers
* model aliases
* convention files
* web/context ingestion
* benchmark culture

For your own CLI project, the greatest treasure is probably:

```text
Aider's repo map + edit formats + Git discipline.
```

That trio is battle-tested steel.

[1]: https://github.com/aider-ai/aider "GitHub - Aider-AI/aider: aider is AI pair programming in your terminal · GitHub"
[2]: https://github.com/Aider-AI/aider/blob/main/LICENSE.txt "aider/LICENSE.txt at main · Aider-AI/aider · GitHub"
[3]: https://aider.chat/docs/ "Aider Documentation | aider"
[4]: https://aider.chat/docs/config.html "Configuration | aider"
[5]: https://aider.chat/docs/usage/commands.html "In-chat commands | aider"
[6]: https://aider.chat/docs/repomap.html "Repository map | aider"
[7]: https://aider.chat/docs/more/edit-formats.html "Edit formats | aider"
[8]: https://aider.chat/docs/usage/lint-test.html "Linting and testing | aider"
[9]: https://aider.chat/docs/scripting.html "Scripting aider | aider"
[10]: https://aider.chat/docs/usage/watch.html "Aider in your IDE | aider"
[11]: https://aider.chat/docs/usage/conventions.html "Specifying coding conventions | aider"
[12]: https://aider.chat/docs/config/model-aliases.html "Model Aliases | aider"
[13]: https://aider.chat/docs/faq.html "FAQ | aider"
[14]: https://github.com/Aider-AI/aider/tree/main/aider "aider/aider at main · Aider-AI/aider · GitHub"
[15]: https://github.com/Aider-AI/aider/tree/main/aider/coders "aider/aider/coders at main · Aider-AI/aider · GitHub"
[16]: https://github.com/Aider-AI/aider/tree/main/aider/queries "aider/aider/queries at main · Aider-AI/aider · GitHub"
