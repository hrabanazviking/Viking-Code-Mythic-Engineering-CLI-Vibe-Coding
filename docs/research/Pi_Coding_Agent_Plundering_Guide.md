# Pi (pi-coding-agent) Plundering Guide

## Purpose

This guide explains how to lawfully study, reuse, adapt, and "plunder" useful architecture from **Pi**, the coding-agent published as `@mariozechner/pi-coding-agent` and developed in the `badlogic/pi-mono` monorepo at `packages/coding-agent`. ([GitHub][1], [npm][2])

Pi describes itself as a **minimal terminal coding harness**: "Adapt pi to your workflows, not the other way around, without having to fork and modify pi internals." Extensibility is its core thesis — TypeScript Extensions, Skills, Prompt Templates, Themes, and Pi Packages — and it ships in four operating modes: **interactive**, **print/JSON**, **RPC**, and **SDK**. ([GitHub][1])

This is practical open-source hygiene, not legal advice.

---

## 1. Core Legal Position

Pi is licensed under the **MIT License** at the monorepo root. The repository's license file is the canonical MIT text with `Copyright (c) 2025 Mario Zechner`. ([GitHub][3])

MIT is the most permissive license in our usual plunder set. It allows you to:

* copy code
* modify code
* redistribute modified versions
* use it commercially
* merge useful portions into your own project
* relicense the combined work under your own license (so long as the MIT text and copyright travel with the embedded portions)

MIT requires only one practical duty when redistributing: **preserve the MIT copyright notice and the permission/disclaimer text in copies and substantial portions of the Software**. There is no NOTICE-file obligation, no modification-marking obligation, no patent grant, and no trademark restriction in the MIT text itself. ([GitHub][3])

Because our own CLI ships under Apache-2.0, **MIT-licensed code can be embedded in an Apache-2.0 project**: keep the MIT notice attached to the embedded code, then your own additive material follows the project's Apache-2.0 license. The two licenses are compatible in this direction.

> Take the useful steel.
> Keep the maker's mark.
> Forge your own blade.

---

## 2. Required Source Links

Use these as canonical upstream references in your repo docs.

### Main Links

* **pi-mono GitHub Repository** — main monorepo source. ([GitHub][1])
* **pi-mono LICENSE** — MIT License text. ([GitHub][3])
* **pi-coding-agent npm package** — distribution surface (`@mariozechner/pi-coding-agent`). ([npm][2])
* **pi.dev** — project home page. ([pi.dev][4])
* **`packages/coding-agent` README** — feature surface, quick start, providers, mode summary. ([GitHub][5])
* **`packages/coding-agent/docs`** — full doc set for compaction, extensions, skills, prompt-templates, providers, RPC, sessions, settings, themes, TUI, and more. ([GitHub][6])
* **`packages/coding-agent/src`** — source tree (cli, core, modes, utils, bun). ([GitHub][7])
* **`packages/coding-agent/test`** — high-coverage Vitest suite. ([GitHub][8])
* **`packages/coding-agent/CHANGELOG.md`** — release-history attribution anchor. ([GitHub][9])

---

## 3. Core MIT Duties

## 3.1 Keep the License

Your project should already include:

```text
LICENSE
```

If your project is Apache-2.0, that file remains authoritative for *your* code. For Pi-derived material you also need the MIT copyright/permission text travelling with that material — typically as a per-file header or as a section in `THIRD_PARTY_NOTICES.md`.

MIT's only redistribution requirement is that the original copyright + permission text accompany the embedded code. ([GitHub][3])

---

## 3.2 Preserve Notices

When copying or adapting Pi files or meaningful chunks:

* preserve the upstream MIT copyright line (`Copyright (c) 2025 Mario Zechner`)
* preserve the MIT permission paragraph and disclaimer (do not strip them)
* mark adapted files so the lineage is visible
* do not claim Pi-derived code was written entirely from scratch

Suggested Python header (when porting TypeScript to Python):

```python
# Portions adapted from badlogic/pi-mono (packages/coding-agent).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md.
```

Suggested TypeScript header (if you embed Pi code in a TS module):

```ts
// Portions adapted from badlogic/pi-mono (packages/coding-agent).
// Upstream project: pi (pi-coding-agent), licensed under the MIT License.
// Copyright (c) 2025 Mario Zechner.
// Adapted by Volmarr / RuneForgeAI, 2026.
```

Suggested Markdown header (when copying a doc):

```md
<!--
Portions adapted from badlogic/pi-mono (packages/coding-agent).
Upstream project: pi (pi-coding-agent), licensed under the MIT License.
Copyright (c) 2025 Mario Zechner.
Modified by Volmarr / RuneForgeAI, 2026.
-->
```

---

## 3.3 Add Third-Party Notices

Recommended repo files (already standard in this project):

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
docs/plunder/PI_PLUNDER_GUIDE.md
docs/plunder/PI_PLUNDER_MAP.md
```

Suggested addition to `THIRD_PARTY_NOTICES.md`:

```md
## Pi (pi-coding-agent)

Project: pi (pi-coding-agent)
Repository: badlogic/pi-mono (packages/coding-agent)
License: MIT License
Copyright: Copyright (c) 2025 Mario Zechner

This project may include or adapt selected portions of pi-coding-agent,
especially architectural patterns related to:

- agent session runtime and event-driven turn loop
- multi-mode execution (interactive, print/JSON, RPC, SDK)
- compaction and branch-summarization strategies
- skills, prompt templates, and TypeScript extensions
- session manager with branching and serialization
- slash-command and keybinding subsystems
- output guard and stdout-cleanliness invariants
- multi-provider model registry and resolver
- auth storage with subscription and API-key flows
- bash, edit, write, read, find, grep, ls tools
- file mutation queue
- RPC JSONL protocol for process integration
- HTML export pipeline
- terminal UI components and theme system

This project is independent and is not affiliated with, endorsed by, or
sponsored by Mario Zechner, the pi-mono authors, or pi.dev.

Full MIT permission text reproduced below:

[paste the upstream LICENSE here]
```

Pasting the upstream MIT text in `THIRD_PARTY_NOTICES.md` is the simplest way to satisfy MIT's preservation duty for code embedded across multiple files.

---

## 4. Branding Warning

MIT, like Apache-2.0, lets you reuse code. It does **not** let you steal the project's identity.

Safe wording:

```md
This project includes code adapted from badlogic/pi-mono (packages/coding-agent).
```

Unsafe wording:

```md
This is the official Pi CLI.
```

Avoid names like:

* Official Pi Fork
* Pi Pro
* Pi Coding Agent
* Pi Mythic Edition
* Pi.dev Official CLI

The upstream project's identity is `pi`, the npm package is `@mariozechner/pi-coding-agent`, and the home page is `pi.dev`. Reuse "Pi" only for attribution and source description, never as your own product name. The `pi.dev` domain is donated branding from `exe.dev` per the upstream README — treat the entire identity stack as off-limits for derivative branding.

---

## 5. Repo Structure Worth Studying

Pi-mono is a **TypeScript / Node.js** monorepo. Most of the existing plunder guides target Python projects; Pi is the first TypeScript target in this set, and that has implications you should plan around (see Section 8 — *Cross-Language Translation Notes*).

The `packages/coding-agent` package is the artifact we care about. Its top-level layout:

```text
packages/coding-agent/
  CHANGELOG.md
  README.md
  package.json
  tsconfig.build.json
  tsconfig.examples.json
  vitest.config.ts
  docs/
  examples/
  scripts/
  src/
  test/
```

The most important source directory is:

```text
packages/coding-agent/src/
```

Its tree:

```text
src/
  bun/                              # Bun-runtime shims and bindings
  cli/
    args.ts                         # arg parsing
    config-selector.ts
    file-processor.ts
    initial-message.ts
    list-models.ts
    session-picker.ts
  cli.ts                            # CLI entrypoint
  config.ts                         # configuration model
  core/
    compaction/
      branch-summarization.ts
      compaction.ts
      index.ts
      utils.ts
    export-html/                    # HTML export pipeline
    extensions/
      index.ts
      loader.ts
      runner.ts
      types.ts
      wrapper.ts
    tools/
      bash.ts
      edit-diff.ts
      edit.ts
      file-mutation-queue.ts
      find.ts
      grep.ts
      index.ts
      ls.ts
      path-utils.ts
      read.ts
      render-utils.ts
      tool-definition-wrapper.ts
      truncate.ts
      write.ts
    agent-session-runtime.ts
    agent-session-services.ts
    agent-session.ts
    auth-guidance.ts
    auth-storage.ts
    bash-executor.ts
    defaults.ts
    diagnostics.ts
    event-bus.ts
    exec.ts
    footer-data-provider.ts
    index.ts
    keybindings.ts
    messages.ts
    model-registry.ts
    model-resolver.ts
    output-guard.ts
    package-manager.ts
    prompt-templates.ts
    resolve-config-value.ts
    resource-loader.ts
    sdk.ts
    session-cwd.ts
    session-manager.ts
    settings-manager.ts
    skills.ts
    slash-commands.ts
    source-info.ts
    system-prompt.ts
    telemetry.ts
    timings.ts
  index.ts                          # public package surface
  main.ts                           # process boot
  migrations.ts                     # settings migrations
  modes/
    interactive/
      assets/
      components/
      interactive-mode.ts
      theme/
    rpc/
      jsonl.ts
      rpc-client.ts
      rpc-mode.ts
      rpc-types.ts
    print-mode.ts
    index.ts
  package-manager-cli.ts
  utils/
    changelog.ts
    child-process.ts
    clipboard-image.ts
    clipboard-native.ts
    clipboard.ts
    exif-orientation.ts
    frontmatter.ts
    fs-watch.ts
    git.ts
    image-convert.ts
    image-resize.ts
    mime.ts
    paths.ts
    photon.ts
    pi-user-agent.ts
    shell.ts
    sleep.ts
    tools-manager.ts
    version-check.ts
```

The full documentation surface lives at:

```text
packages/coding-agent/docs/
  compaction.md
  custom-provider.md
  development.md
  extensions.md
  json.md
  keybindings.md
  models.md
  packages.md
  prompt-templates.md
  providers.md
  quickstart.md
  rpc.md
  sdk.md
  session-format.md
  sessions.md
  settings.md
  shell-aliases.md
  skills.md
  terminal-setup.md
  termux.md
  themes.md
  tmux.md
  tui.md
  usage.md
  windows.md
```

The test surface is unusually thorough — about ninety Vitest files covering agent-session behaviors, compaction, extensions, RPC, SDK, sessions, settings, theme export, and integration flows. The tests double as canonical executable spec for many subsystems and are themselves valuable plunder targets when porting a feature. ([GitHub][8])

---

## 6. Highest-Value Plunder Targets

The richest material to study, ranked by leverage for our own CLI:

## 6.1 `src/core/agent-session*.ts` — Agent Loop Trio

The session runtime is split into three files, which is itself a useful pattern:

```text
src/core/agent-session.ts            # public session shape and orchestration
src/core/agent-session-runtime.ts    # the actual turn loop
src/core/agent-session-services.ts   # injected services / dependencies
```

The split separates *what a session is* from *how a turn runs* from *what the turn calls into*. That dependency-direction clarity is worth copying directly into Mythic Vibe CLI's workflow runner when we lift the always-blocked `workflow run` into real provider execution.

## 6.2 `src/core/compaction/` — Context Window Management

```text
src/core/compaction/
  branch-summarization.ts
  compaction.ts
  index.ts
  utils.ts
```

Branch summarization is the standout idea: when context fills, summarize a branch of history rather than dropping it, so future turns can still walk back into the summarized branch. Multiple Vitest files cover compaction scenarios (auto-compaction queue, serialization, summary reasoning, thinking-model interaction), so the test files are canonical executable spec.

## 6.3 `src/core/tools/` — Default Toolset

```text
src/core/tools/
  bash.ts
  edit.ts
  edit-diff.ts
  file-mutation-queue.ts
  find.ts
  grep.ts
  ls.ts
  read.ts
  render-utils.ts
  truncate.ts
  write.ts
```

Pi's default toolset is intentionally tight: `read`, `write`, `edit`, `bash`. These four are the floor for a competent agent. The file-mutation-queue serializes destructive edits so concurrent tool calls cannot stomp each other — a pattern Mythic should adopt before any provider-driven `workflow run` lands. The `edit-diff.ts` and `truncate.ts` patterns address the long-running pain of "AI generates a bad diff then loops" without introducing a heavyweight diff library.

## 6.4 `src/core/extensions/` — TypeScript Extension Loader

```text
src/core/extensions/
  index.ts
  loader.ts
  runner.ts
  types.ts
  wrapper.ts
```

Pi's extensions are TypeScript files that the agent can load at run time and call as if they were first-class tools. The `loader.ts` / `runner.ts` / `wrapper.ts` triplet shows how to expose a *typed* extension surface without resorting to `eval` or untyped JSON. Mythic Vibe's `plugins/` system can borrow the layered load + run + wrap pattern even though we stay in Python.

## 6.5 `src/core/skills.ts` and `src/core/prompt-templates.ts`

Skills are user-discoverable named capabilities, and prompt templates are reusable parameterizable prompts. Pi treats both as first-class, namespaced, discoverable from `npm` or `git` via Pi Packages. Mythic's `ai/prompts/roles.py` already moves in this direction; promoting *templates* and *skills* to first-class artifacts (with frontmatter, manifests, and packetable metadata) is the natural next step.

## 6.6 `src/core/session-manager.ts` and `src/core/session-cwd.ts`

The session manager handles serialization, branching, and listing of sessions, with a separate working-directory abstraction. Mythic's `handoff.py` is the analog. The Pi pattern of branching as a first-class operation (with corresponding `agent-session-tree-navigation.test.ts`) is something Mythic could grow into the workflow history ledger we just landed.

## 6.7 `src/modes/rpc/` — JSONL RPC Mode

```text
src/modes/rpc/
  jsonl.ts
  rpc-client.ts
  rpc-mode.ts
  rpc-types.ts
```

A complete process-integration protocol for embedding pi inside another process. JSONL framing, typed messages, a client + a mode, and a working real-world consumer (`openclaw/openclaw`). When Mythic lifts `workflow run` into provider execution, an analogous JSONL RPC surface makes embedding Mythic in editors, agents, or other CLIs a small additive step instead of a rewrite.

## 6.8 `src/core/event-bus.ts`

Internal event-driven coordination. Many of the ~30 core modules emit and listen on the bus rather than calling each other directly. Mythic's command surface has not yet needed this, but as the workflow runner grows, an event bus is the right shape for `before_*` / `after_*` plugin hooks, telemetry, and live-status panels.

## 6.9 `src/core/output-guard.ts`

A guard that protects stdout cleanliness — important because pi runs in modes where stdout is the protocol surface (print/JSON, RPC). The dedicated `stdout-cleanliness.test.ts` enforces it. Mythic already has output policies (`output.py`); this guard pattern is worth borrowing before any provider call can pollute stdout.

## 6.10 `src/core/model-registry.ts` and `src/core/model-resolver.ts`

A versioned registry of tool-capable models per provider, plus a resolver that reads `--model` / `/model` choices and resolves them through the registry. Mythic's `ai/providers/` is structurally similar but does not yet have an explicit *registry of tool-capable models per provider*. The Pi pattern is a clean upgrade path.

## 6.11 `src/core/auth-storage.ts` and `src/core/auth-guidance.ts`

Pi separates *credential storage* from *credential UX*. `auth-storage.ts` is the data layer; `auth-guidance.ts` is the interactive flow that nudges a user toward a working subscription or API-key configuration. Mythic does not yet have either; when we add provider execution, copying both halves at the same time prevents the usual "credentials work in CI but break for new users" regression.

## 6.12 `src/core/keybindings.ts`

A typed keybinding system with migration support (`keybindings-migration.test.ts`). Useful when V2 Phase 3 (TUI) lands.

## 6.13 `src/core/slash-commands.ts`

Slash command registry separated from the TUI. The pattern lets the same `/foo` work in interactive mode and in the SDK. Mythic Vibe CLI is sub-command-shaped today; if a TUI ever needs a slash surface, this is the borrowable shape.

## 6.14 `src/core/export-html/`

A complete HTML export pipeline for sessions, with explicit XSS tests (`export-html-xss.test.ts`) and whitespace-fidelity tests. Useful when Mythic grows session sharing.

## 6.15 `src/utils/clipboard*.ts` and `src/utils/image-*.ts`

Cross-platform clipboard reading (including image paste handling, EXIF orientation, BMP conversion). If Mythic ever supports image input from terminal paste, the Pi clipboard handlers are a battle-tested template.

## 6.16 `test/` — Executable Specification

The Vitest suite is one of the strongest assets of this codebase. ~90 test files, including:

- agent-session behavior matrix (auto-compaction queue, branching, concurrent, dynamic providers, dynamic tools, retry, runtime events, stats, tree navigation)
- compaction (auto, extensions, serialization, summary reasoning, thinking-model)
- RPC (JSONL framing, prompt-response semantics, client-clone)
- SDK (codex cache probe, openrouter attribution, session manager, skills)
- platform edge cases (bash close hang on Windows, clipboard image BMP conversion)
- export-html XSS / whitespace
- streaming render debug
- stdout cleanliness (the guard's invariant)

When porting any subsystem, port the corresponding tests first and use them as the definition of done.

---

## 7. Lower-Value or Risky Areas

Some of pi-mono's territory is less useful as plunder material:

* **`packages/coding-agent/src/bun/`** — Bun-runtime-specific shims. Useful only if you also target Bun.
* **`src/utils/photon.ts`** — looks specific to image processing via the photon image library; only worth lifting if you need that exact dependency.
* **`docs/termux.md` / `docs/windows.md` / `docs/tmux.md`** — platform tip docs. Reference only; they reflect Pi's deployment story, not generic patterns.
* **`pi-user-agent.ts`** — string identifying pi to providers. Replace with your own UA; do not preserve `pi-coding-agent/x.y.z`.
* **The `package-manager.ts` / `package-manager-cli.ts` surfaces** — these manage Pi's own package format (Pi Packages on npm/git). If Mythic ever grows a similar package format, the *shape* is borrowable but the *names* and *npm assumptions* are not.

---

## 8. Cross-Language Translation Notes

Pi is **TypeScript on Node.js (with optional Bun runtime)**. Mythic Vibe CLI is **Python**. Direct copy-paste plunder is therefore much narrower than for the Aider, Goose, Codex, Gemini, Mistral, or Qwen guides. Most plunder from Pi is **architectural**, not source-level.

What translates cleanly:

* file layout and dependency direction (e.g. the agent-session runtime/services split)
* schemas and protocol shapes (RPC JSONL frames, session format, settings layout)
* algorithm shapes (branch summarization, file mutation queue serialization)
* test specifications (tests are pseudocode you can re-implement in pytest)
* documentation surface (docs/* topics map nicely to docs/)

What does **not** translate cleanly:

* TypeScript types, decorators, and class hierarchies — port to dataclasses + protocols
* the Bun-specific runtime shims
* npm-driven extension loading — port to entry points / setuptools plugins
* the React-style TUI components (under `src/modes/interactive/components/`) — port to whatever TUI engine V2 Phase 3 picks (Textual is the V2 default)

When porting a Pi subsystem, **prefer test-first**: copy the relevant `test/*.ts` files into `tests/test_pi_<subsystem>.py` as a *spec* (not as runnable code), and re-implement the production code to satisfy that spec in Python. This forces you to re-derive the design instead of mechanically transliterating, which preserves the architecture without dragging TS-isms into the Python layer.

---

## 9. Prompt Patterns Worth Borrowing

The following are *patterns*, not exact strings — pi's prompt strings are MIT-protected text and you should paraphrase rather than copy verbatim:

* **System-prompt locality** — `src/core/system-prompt.ts` builds the system prompt from a small set of lookups, not a giant template. Mythic's role catalogue should follow the same composition discipline.
* **Per-tool prompts** — Pi pairs each tool's implementation with its description text, kept next to the implementation file. Mythic's `ai/prompts/roles.py` should grow per-tool descriptions in the same place as the tool runner code.
* **Compaction prompts** — see `src/core/compaction/branch-summarization.ts` for the shape of "summarize this branch of history into something an agent can resume from." Worth replicating as a Mythic prompt template once we add cross-session continuity.
* **Output-format constraints** — the tools enforce *output shape* in the tool description, not in post-processing. This is much more reliable than parsing model output after the fact.

---

## 10. Suggested Mythic Mapping

Pi inspiration on the left; Mythic Vibe CLI target path on the right.

### 10.1 Agent Loop

```text
pi: src/core/agent-session.ts
    src/core/agent-session-runtime.ts
    src/core/agent-session-services.ts

mythic: mythic_vibe_cli/runtime/
          session.py
          turn_loop.py
          services.py
```

Lifts the runtime/services split into the Mythic codebase when `workflow run` becomes provider-capable.

### 10.2 Compaction

```text
pi: src/core/compaction/branch-summarization.ts
    src/core/compaction/compaction.ts

mythic: mythic_vibe_cli/runtime/compaction/
          branch_summarization.py
          compaction.py
```

A Mythic compaction surface plugs into the workflow history ledger (`mythic/workflow_history.json`) we already landed.

### 10.3 Tools

```text
pi: src/core/tools/{bash, edit, write, read, find, grep, ls}.ts
    src/core/tools/file-mutation-queue.ts

mythic: mythic_vibe_cli/tools/
          bash.py
          edit.py
          write.py
          read.py
          find.py
          grep.py
          ls.py
          file_mutation_queue.py
```

Mutation queue lands first; it is the safety primitive.

### 10.4 Extensions / Skills / Prompt Templates

```text
pi: src/core/extensions/
    src/core/skills.ts
    src/core/prompt-templates.ts

mythic: mythic_vibe_cli/plugins/        (existing — add wrapper / runner discipline)
        mythic_vibe_cli/skills/         (new)
        mythic_vibe_cli/prompts/        (existing roles.py — add templates submodule)
```

### 10.5 Sessions and Handoff

```text
pi: src/core/session-manager.ts
    src/core/session-cwd.ts
    docs/session-format.md

mythic: mythic_vibe_cli/handoff.py      (existing — grow branching)
        mythic_vibe_cli/runtime/session_cwd.py (new)
        docs/SESSION_FORMAT.md          (new)
```

### 10.6 RPC Mode

```text
pi: src/modes/rpc/{jsonl, rpc-client, rpc-mode, rpc-types}.ts

mythic: mythic_vibe_cli/modes/rpc/
          jsonl.py
          client.py
          mode.py
          types.py
```

### 10.7 Slash Commands and Keybindings (TUI surface)

```text
pi: src/core/slash-commands.ts
    src/core/keybindings.ts

mythic: mythic_vibe_cli/tui/
          slash_commands.py
          keybindings.py
```

These land as part of V2 Phase 3 (TUI). Pre-tagging the target paths now lets the TUI slice cite this guide instead of inventing a layout.

### 10.8 Output Guard

```text
pi: src/core/output-guard.ts
    test/stdout-cleanliness.test.ts

mythic: mythic_vibe_cli/output_guard.py
        tests/test_stdout_cleanliness.py
```

### 10.9 Model Registry / Resolver

```text
pi: src/core/model-registry.ts
    src/core/model-resolver.ts

mythic: mythic_vibe_cli/ai/registry.py    (existing — grow a tool-capable index)
        mythic_vibe_cli/ai/model_resolver.py (new)
```

### 10.10 Auth Storage and Guidance

```text
pi: src/core/auth-storage.ts
    src/core/auth-guidance.ts

mythic: mythic_vibe_cli/ai/auth/
          storage.py
          guidance.py
```

### 10.11 HTML Export

```text
pi: src/core/export-html/

mythic: mythic_vibe_cli/exporters/
          html.py
```

---

## 11. Do / Do Not

**Do:**

* preserve the `Copyright (c) 2025 Mario Zechner` line on adapted material
* keep the MIT permission text in `THIRD_PARTY_NOTICES.md`
* port the corresponding tests *first* when borrowing a subsystem
* paraphrase prompt strings rather than copying them verbatim
* describe your project as "adapted from badlogic/pi-mono"
* respect Pi's contribution rules (auto-close of new issues/PRs from new contributors); upstream contribution is a different exercise from plunder, and this guide does not authorize speaking on Pi's behalf

**Do not:**

* call your derivative "pi", "Pi CLI", "Pi.dev", or anything that implies official Pi affiliation
* copy `pi-user-agent.ts` verbatim and ship with the upstream UA string
* embed Pi's `package.json` `author` / `name` fields
* lift the Bun-runtime shims unless you actually target Bun
* drag the React-style TUI component tree into a Python project
* assume MIT lets you remove the copyright notice — it does not
* copy the upstream npm package metadata into your own `pyproject.toml`

---

## 12. Final Checklist Before Publishing

Before pushing your adapted CLI publicly:

* [x] Your repo has `LICENSE`.
* [x] Your repo's own license is recorded (Apache-2.0 in this project).
* [x] Your repo has `NOTICE`.
* [x] Your repo has `THIRD_PARTY_NOTICES.md` with the full upstream MIT text.
* [ ] Your README credits Pi where relevant ("adapted from badlogic/pi-mono"). _(deferred until the queue is wired into a user-facing surface)_
* [x] Modified files have a per-file header citing pi-mono and noting modification.
* [x] Original `Copyright (c) 2025 Mario Zechner` line is preserved in adapted files.
* [x] You removed Pi branding from your own product identity.
* [x] You documented copied/adapted areas in a plunder map. _(see `THIRD_PARTY_NOTICES.md` § "Plunder Map")_
* [x] You ported the corresponding Pi tests as the spec for each plundered subsystem.
* [x] You replaced the user-agent string and any `pi-` named identifiers in your runtime. _(N/A for the file-mutation-queue slice; will re-verify each future slice.)_
* [x] You did not copy the upstream `package.json`, npm publishing config, or distribution metadata.
* [x] If you ship an extension/skill loader, you redocumented it as your own format — do not claim Pi Package compatibility unless you actually implement it correctly. _(N/A — no extension loader in this slice.)_
* [x] You did not vendor the React-style TUI components into a non-React stack.
* [x] Auth storage UX is rewritten for *your* providers, not Pi's subscription matrix. _(N/A — no auth code in this slice.)_
* [x] RPC JSONL message types are defined in your own schema file, not lifted as `rpc-types.ts`. _(N/A — no RPC code in this slice.)_
* [x] You acknowledged the cross-language translation gap in any README that lists "ported from Pi" subsystems. _(Recorded in DEVLOG and the per-file header; README update deferred with the user-facing wiring.)_

---

## 13. Clean Rule

```text
Copy the architecture.
Respect the MIT notice.
Translate, do not transliterate.
Port the tests first.
Replace the user agent.
Do not steal the branding.
```

Pi is especially valuable because it is the **first MIT-licensed terminal coding agent** in our plunder set, and because its design treats *extensibility* — not just edit fidelity or repo-mapping — as the load-bearing concern. The greatest treasure for our own CLI is probably:

```text
Pi's runtime/services split + compaction branch summarization + tool mutation queue.
```

That trio addresses the three problems that block any serious provider-driven `workflow run`: turn-loop discipline, context-window survival, and write-conflict safety.

---

[1]: https://github.com/badlogic/pi-mono "GitHub - badlogic/pi-mono: AI agent toolkit · GitHub"
[2]: https://www.npmjs.com/package/@mariozechner/pi-coding-agent "@mariozechner/pi-coding-agent · npm"
[3]: https://github.com/badlogic/pi-mono/blob/main/LICENSE "pi-mono/LICENSE at main · badlogic/pi-mono · GitHub"
[4]: https://pi.dev "pi.dev"
[5]: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md "pi-mono/packages/coding-agent/README.md at main · GitHub"
[6]: https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent/docs "pi-mono/packages/coding-agent/docs at main · GitHub"
[7]: https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent/src "pi-mono/packages/coding-agent/src at main · GitHub"
[8]: https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent/test "pi-mono/packages/coding-agent/test at main · GitHub"
[9]: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/CHANGELOG.md "pi-mono/packages/coding-agent/CHANGELOG.md at main · GitHub"
