---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/120329a8-9f29-4177-b10f-56719c134843.png](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/120329a8-9f29-4177-b10f-56719c134843.png)

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-18-viking-code-cli.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-18-viking-code-cli.jpg)

---

# Mythic Vibe CLI

**Version:** `0.1.0` · **Python:** `>=3.10` · **License:** `Apache-2.0` · **Tests:** `270 passing` · **Status:** Active development on `development`

Mythic Vibe CLI is an open-source, method-first command-line tool for builders who want to **ship software with continuity, architecture, and recoverable memory** — not just momentum.

It enforces an explicit engineering loop that keeps your reasoning alive on disk:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

The hall is wide enough for a first-time builder finding their footing, and disciplined enough for a seasoned maintainer who cares about clean handoffs, repeatable process, and artifacts that outlive any single session.

Canonical Mythic Engineering source:
- https://github.com/hrabanazviking/Mythic-Engineering

## Cross-Platform Pledge

Mythic Vibe CLI runs on **Windows, macOS, and Linux** without per-OS branches. Every dependency is open-source. We deliberately avoid:

- proprietary platform SDKs
- OS-specific signal handlers (no `SIGUSR1` tricks; subprocess control uses `terminate()` / `kill()` / `wait(timeout=...)`)
- Unix-only path conventions in production code
- closed third-party services as required dependencies

Where a feature would otherwise depend on a single platform, we either pick a pure-Python equivalent (e.g., `textual` for the TUI) or document the omission honestly.

## Active Runtime Path

This repository is a large mythic engineering workspace, but the installable CLI product lives in a deliberately narrow boundary:

- `mythic_vibe_cli/` for active runtime code
- `tests/` for active product verification
- `pyproject.toml` for packaging and command entrypoints
- `docs/` plus root governance records for architecture, boundary, and continuity

Dormant runtime islands, vendor mirrors, and research corpora are source material until an ADR and adapter contract say otherwise. Start with `REPO_BOUNDARY.md` and `docs/ACTIVE_PRODUCT_BOUNDARY.md` before wiring any cross-island dependency.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/ee5643a3-eb8a-4100-98ad-d4e8b9eeb1b0.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/ee5643a3-eb8a-4100-98ad-d4e8b9eeb1b0.jpg)

---

## What changed in the most recent passes

The scrolls have been deepened. This repository now carries a fuller documentation suite *and* a real, tested runtime layer that supports operator workflows end-to-end:

- **A modular runtime layer** under `mythic_vibe_cli/runtime/` provides eight composable primitives (file mutation queue, output guard, event bus, timings, slash command catalog, source-info provenance, exec, event log). Each is tested directly and re-exported from `mythic_vibe_cli.runtime`. Several are adapted from `badlogic/pi-mono` (MIT) — see **Acknowledgements** below.
- **A plugin system** with eight life-cycle hooks (`before_/after_` × `scan/packet/verify/reflect`) wired through `PluginHookDispatcher`. Plugins can also contribute slash commands. See `docs/plugins.md`.
- **A bounded event log** at `mythic/events.jsonl` (last 200 entries, atomic rotation). Every dispatcher emit appends one line; the TUI reads it for the Recent Events panel.
- **`mythic-vibe shell`** — a minimal interactive REPL that dispatches each line back through `app.main(argv)` so the full argparse + handler stack runs per command.
- **`mythic-vibe tui`** — a Textual-based TUI showing project status in a four-panel grid plus a Recent Events feed, with `/` opening a slash-command picker → preview → live command runner with elapsed-time tick.
- **`verify`** runs durable verification gates (commands, changed files, docs, invariants) and writes a permanent record under `mythic/verifications/`. Optional `--record` promotes the artifact to `latest.json` and updates project state.
- **`workflow plan`** orchestrates Mythic's six roles (Skald, Architect, Forge, Auditor, Cartographer, Scribe), checks packet readiness, and emits a durable `mythic/workflow_plan.json`.
- **`plunder`** — lawful single-file reuse from Apache-2.0/MIT upstream repositories with provenance manifests under `mythic/imports/`.
- **AI providers**: `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, `openrouter` adapters live under `mythic_vibe_cli/ai/providers/`. Optional dependencies; the `copy-paste` provider always works.
- Expanded operator-facing docs (`docs/runtime.md`, `docs/plugins.md`, `docs/COMMAND_CONTRACTS.md`).
- A durable `CHANGELOG.md` with semantic structure and release-note discipline.
- `docs/INDEX.md` as a stable navigation hub for docs consumers and contributors.
- `DEVLOG.md` updated entry-by-entry so future sessions inherit context instead of guesswork.

If you are returning after a break, light your fire at **`docs/INDEX.md`** first — the threads are waiting there.

---

## Why Mythic Vibe CLI was forged

Most coding tools chase speed and treat continuity as a luxury. Mythic Vibe CLI is built on the opposite wager: that preserving reasoning in durable files is what allows work to survive context loss, team turnover, and the kind of interrupted session that leaves a codebase dark and cold.

The forge was lit for four things:

1. **Reduce drift** between plans, code, and docs — so what was decided stays readable beside what was built.
2. **Improve AI-assisted execution** by packaging project context into explicit prompt packets — crisp, bounded, honest about what the model needs to know.
3. **Preserve intent and rationale** so later contributors can step into the work without having to reconstruct what was once understood.
4. **Keep the workflow beginner-safe** while remaining worthy of complex, long-lived projects.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/178756ea-06c6-429e-817a-607113ebaa08.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/178756ea-06c6-429e-817a-607113ebaa08.jpg)

---

## Core capabilities

### 1) Method-first project initialization

Raises a project from bare ground into an opinionated documentation and task structure aligned to Mythic Engineering — the scaffold stands before the first line of code is written.

### 2) Phase-oriented workflow operations

Guides you through repeated, deliberate movement across the full loop:
- intent
- constraints
- architecture
- plan
- build
- verify
- reflect

Every pass through the loop deposits artifacts. Nothing important is left only in memory.

### 3) Prompt bridge for ChatGPT/Codex workflows

Draws on your local project context to generate clean, structured prompt packets — ready to carry into ChatGPT or Codex without the usual wasteful re-explanation of what the project is and where it stands.

### 4) Response logging for continuity

Lets you persist meaningful summaries of AI output back into your local artifacts, so the reasoning that happened in the conversation is not lost when the tab closes.

### 5) Diagnostics, status, and verification gates

`doctor` / `scry` surface missing files, invalid state, and method drift. `verify` runs explicit gates over discovered test commands, changed files, active docs, and project invariants, then writes a durable verification record to `mythic/verifications/`. Optional `--record` promotes the artifact to `latest.json` so `next` and `resume` can read it and recommend a next move.

### 6) Configuration layering

Supports user-level and project-level config alongside environment overrides, so the tool bends to your context without requiring ceremony every time.

### 7) Operator guidance and completions

Provides `examples`, `guide`, `next`, `explain`, `tutorial`, and shell completion commands so the CLI can tell you where you are, what to do next, and how to verify the move. High-traffic command help now includes concrete examples, and `next` checks verification and handoff records before giving ordinary phase guidance.

### 8) Six-role workflow orchestration

`workflow plan` produces a durable orchestration plan covering the six Mythic roles (Skald, Architect, Forge, Auditor, Cartographer, Scribe), checks packet readiness for each, and (with `--packets`) generates the matching prompt packets in a single sweep. Plan output lands in `mythic/workflow_plan.json`.

### 9) Lawful plunder of single-file primitives

`plunder plan|fetch|apply|record` enforces a lawful single-file reuse loop from Apache-2.0 / MIT upstream repos. Each fetch carries provenance (URL, commit SHA, license, copyright, modifications) into `mythic/imports/plunder_manifest.json`. Per-file attribution headers stay with the code; `THIRD_PARTY_NOTICES.md` records the upstream license text. See **Acknowledgements** below for what currently lives downstream.

### 10) Plugin system with eight lifecycle hooks

Plugins register via a manifest under `~/.mythic-vibe/grimoire/` (or per-project) and can subscribe to `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, `after_reflect`. Plugins may also contribute slash commands. Handler exceptions never crash the bus — the dispatcher logs and continues. See `docs/plugins.md` for a worked example.

### 11) Interactive surfaces — REPL + TUI

- `mythic-vibe shell` opens a minimal REPL that dispatches each typed line back through the full CLI stack. Handles `/help`, `/quit`, EOF, Ctrl+C; bare commands without a leading `/` work too.
- `mythic-vibe tui` (requires the `[tui]` extra) opens a Textual-based four-panel grid (status / verification / latest handoff / plugins) with a Recent Events feed below, `r` to refresh, `q` to quit, and `/` to open a filterable slash-command picker. From the picker preview, `r` or Enter runs a builtin slash command in a subprocess and shows live elapsed time + final exit code.

### 12) Six AI provider adapters (optional)

`mythic_vibe_cli/ai/providers/` contains adapters for `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, and `openrouter`. The `copy-paste` provider always works (it just renders the packet you would have shipped). The model adapters are gated behind the `[ai]` extra and pick up credentials from environment variables.

### 13) Method excerpt embedding

`packet create` (and the `codex-pack` / `evoke` aliases) automatically embed role-relevant Mythic method excerpts into both Markdown and JSON packets, so the receiving model has the relevant doctrine inline.

---

## Install

The package name is **`mythic-vibe-cli`**. Once installed, two console entrypoints land on your `PATH`:

- `mythic-vibe` — the canonical command
- `mythic` — short alias

> **PyPI status (2026-04):** the project is in active alpha development on the `development` branch and is **not yet published to PyPI**. Until the first PyPI release, install from GitHub or from a local clone using one of the patterns below. Once published, `pip install mythic-vibe-cli` will become the canonical form.

### Recommended — isolated install via `pipx` (for end users)

`pipx` puts the CLI in its own isolated environment so it never collides with your project's Python packages. This is the cleanest install for someone who just wants to *use* Mythic Vibe CLI.

```bash
pipx install "git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
mythic-vibe --version
```

To upgrade later:

```bash
pipx upgrade mythic-vibe-cli
```

To pull in optional extras at install time (Textual TUI, AI providers, rich UI), use the PEP 508 direct-URL form so `pipx` resolves the extras correctly:

```bash
pipx install "mythic-vibe-cli[tui,ai,ux] @ git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
```

### Plain `pip` from GitHub (into the active environment)

```bash
python -m pip install "git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
mythic-vibe --version
```

With extras:

```bash
python -m pip install "mythic-vibe-cli[tui] @ git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
```

### Editable install from a local clone (for contributors)

This is the install for anyone who plans to modify, debug, or run tests against the CLI. The `-e` flag means "editable": `pip` records a link to your working tree instead of copying it, so source changes take effect immediately without re-installing.

Linux / macOS:

```bash
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --version
```

Windows PowerShell:

```powershell
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --version
```

### Optional extras

The CLI ships with a small core and several opt-in extras. Add them after the package spec in square brackets — works with all install styles above:

| Extra | Adds | Wheels installed |
|---|---|---|
| `tui` | Textual TUI (`mythic-vibe tui`) | `textual>=0.80` |
| `ai` | AI provider adapters | `anthropic>=0.34`, `google-genai>=1.0`, `openai>=1.40` |
| `ux` | Optional rich-text UI polish (set `MYTHIC_RICH=1` to enable) | `rich>=13.0` |
| `dev` | Full development stack (tests, lint, type, build, plus all of the above) | adds `pytest`, `pytest-cov`, `ruff`, `mypy`, `build`, `twine`, `mkdocs` |

Examples (note the **PEP 508 direct-URL form** — `package[extras] @ git+URL@branch` — which is what `pip` and `pipx` both expect for VCS installs with extras):

```bash
# pipx with extras
pipx install "mythic-vibe-cli[tui] @ git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"

# pip with extras
python -m pip install "mythic-vibe-cli[tui,ai] @ git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"

# Editable from a local clone with everything (contributors)
python -m pip install -e ".[dev]"
```

### Prerequisites

- Python 3.10+ (also tested on 3.11 / 3.12 / 3.13)
- Git
- A shell environment — bash, zsh, fish, PowerShell, or similar

Recommended:

- A virtual environment (`venv`, `uv`, `conda`)
- Linting/formatting tools in your editor (the project uses `ruff` and `mypy`)

For deeper platform-specific setup (`uv`, release-quality dev installs, shell completion, optional rich rendering), see `docs/INSTALL.md`.

### Verify the install

```bash
mythic-vibe --version
mythic-vibe --help
mythic-vibe doctor
```

`mythic-vibe doctor` reports the active project's structural health and is a good first sanity check.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/6cd73309-165e-44ff-aee3-d66afb691e78.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/6cd73309-165e-44ff-aee3-d66afb691e78.jpg)

---

## Quick start

Speak your intent and let the scaffold rise:

```bash
mythic-vibe init --goal "Build a beginner-friendly TODO app" --noob
```

This weaves Mythic-oriented scaffolding into place:

- `docs/PHILOSOPHY.md`
- `docs/ARCHITECTURE.md`
- `docs/DOMAIN_MAP.md`
- `docs/DATA_FLOW.md`
- `docs/DEVLOG.md`
- `tasks/current_GOALS.md`
- `mythic/plan.md`
- `mythic/loop.md`
- `mythic/status.json`
- `MYTHIC_ENGINEERING.md`

For complete onboarding, read `docs/quickstart.md`.

---

## ChatGPT Plus / Codex bridge workflow

When the work ahead calls for a sharper blade than local tooling alone provides, this is how you cross the bridge cleanly.

1) Generate a context packet from what is already known locally:

```bash
mythic-vibe codex-pack \
  --phase plan \
  --task "Implement the CLI command parser and file templates" \
  --audience beginner
```

2) Open `mythic/codex_prompt.md` and paste the `Prompt To Paste` section into ChatGPT/Codex.

3) When the assistant returns, log its outcome so the reasoning does not vanish:

```bash
mythic-vibe codex-log --phase build --response "Implemented parser with subcommands and docs updates"
```

4) Inspect where the work stands:

```bash
mythic-vibe status
```

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/2628f01e-d7fd-4923-84de-e19630282130.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/2628f01e-d7fd-4923-84de-e19630282130.jpg)

---

## Configuration model

The tool reads configuration from multiple sources and honors the closest one. Precedence flows low to high:

1. `~/.mythic-vibe.json`
2. `$XDG_CONFIG_HOME/mythic-vibe/config.json`
3. `<project>/.mythic-vibe.json`
4. Environment variable overrides

These environment variables override any file-based value at runtime:

- `MYTHIC_EXCERPT_LIMIT`
- `MYTHIC_PACKET_CHAR_BUDGET`
- `MYTHIC_AUTO_COMPACT`
- `MYTHIC_METHOD_SOURCE`
- `MYTHIC_TIMING` — when set to `1` / `true` / `yes` / `on`, prints a startup-and-command profile to stderr (`argparse`, `configure_output`, `handler:<command>`, `TOTAL`)

To see what the tool is actually reading in your current project:

```bash
mythic-vibe config --path .
```

Example config:

```json
{
  "codex": {
    "excerpt_limit": 2200,
    "packet_char_budget": 14000,
    "auto_compact": true
  }
}
```

---

## Documentation governance and continuity

Documentation is not decoration here — it is the thread that connects this session to the next one, and the one after that. This project carries an explicit governance layer to keep that thread from fraying:

- `docs/INDEX.md` is the canonical documentation map — start every return visit there.
- `docs/DOCUMENTATION_STANDARDS.md` defines writing obligations and update expectations for contributors.
- `docs/SESSION_HANDOFF_TEMPLATE.md` provides a structured end-of-session handoff that future-you will be glad exists.
- `DEVLOG.md` and `CHANGELOG.md` are maintained as paired historical records — narrative continuity alongside release-facing history.
- `docs/runtime.md` and `docs/plugins.md` are the operator-facing guides for the runtime primitives and the plugin system, respectively.
- `docs/COMMAND_CONTRACTS.md` records the durable contract surface of every CLI command.

When you change behavior, update the docs in the same commit or PR. Treat documentation drift as a functional bug, not an editorial nicety.

---

## Command overview

Mythic Vibe CLI exposes the following command families. Run `mythic-vibe <command> --help` for full options on each.

### Project lifecycle
- `init` / `start` / `imbue` — initialize Mythic scaffolding
- `status` — show current Mythic progress summary
- `state` — inspect and validate Mythic project state
- `doctor` / `scry` — validate project structure and run diagnostics

### Authoring loop
- `checkin` — log a Mythic phase update and advance tracking
- `reflect` — create a reflection handoff for the current session
- `resume` — summarize the latest handoff and suggest the next step
- `handoff` — create, inspect, or list session handoff records
- `weave` — record documentation synchronization checkpoint
- `prune` — suggest dead-code pruning workflow
- `heal` — guide a test-healing workflow

### Context + packets
- `scan` — build a local project index for AI context
- `import-md` — import all Markdown files from the Mythic Engineering repo
- `codex-pack` / `evoke` — generate a copy-paste-ready prompt packet
- `codex-log` — record a check-in update after receiving an AI response
- `packet` — create, show, or list reusable packet artifacts
- `workflow` — plan role-based Mythic workflow orchestration (six-role plans, packet readiness)

### Verification + governance
- `verify` — run verification gates (commands, changed files, docs, invariants) and write a durable record
- `oath` — display the responsible AI usage oath
- `method` — inspect and sync the active Mythic Engineering method profile
- `sync` — sync Mythic Engineering method notes from GitHub

### Extensibility
- `grimoire add|list` — manage plugins (registration)
- `plugin list|inspect|disable` — health, hook declarations, and pause control
- `plunder plan|fetch|apply|record` — lawful single-file reuse from open-source upstreams
- `ai` — manage optional AI provider integrations
- `slash list` — inspect the slash command catalog (built-in + plugin-contributed)

### Operator helpers
- `examples` — copy-paste command examples
- `guide` — compact operator guide
- `next` — show the next recommended phase and command
- `explain` — explain phases and artifacts
- `tutorial` — first full workflow tutorial
- `completion` — print shell completion script
- `config set` — show or manage configuration values
- `db migrate` — database maintenance tasks

### Interactive surfaces
- `shell` — open the minimal REPL
- `tui` — open the Textual TUI (requires the `[tui]` extra)

For full command behavior and contracts, see `docs/api.md` and `docs/COMMAND_CONTRACTS.md`.

---

## Runtime primitives

`mythic_vibe_cli/runtime/` holds eight small, single-purpose primitives that the rest of the CLI builds on. Each is self-contained, tested directly under `tests/`, and re-exported from `mythic_vibe_cli.runtime`.

| Primitive | Purpose | Wired today |
|---|---|---|
| `file_mutation_queue` | Per-resolved-path serialization for mutation operations (symlinks share the same queue via `os.path.realpath`) | Packet write paths |
| `output_guard` | Reroute `sys.stdout` writes to `sys.stderr` while preserving a "real stdout" path for protocol output | Every `--json` command |
| `event_bus` | Synchronous publish/subscribe with exception-isolated handlers | `PluginHookDispatcher` |
| `timings` | Lightweight elapsed-time profiling, env-gated by `MYTHIC_TIMING` | `app.main()` startup boundaries |
| `slash_commands` | Typed catalog of slash command names + sources (`builtin` / `extension` / `prompt` / `skill` / `plugin`) | `slash list`, `shell` `/help`, TUI picker |
| `source_info` | Provenance dataclass for extension/plugin/skill/prompt-contributed artifacts | `SlashCommandInfo`; `slash list` |
| `exec` | Subprocess execution with timeout and cancel-event (cross-platform; missing binaries return `code=127` instead of raising) | `verify/test_runner.py`, `verify/git_diff.py`, `handoff.py`, `context/scanner.py` |
| `event_log` | Bounded JSONL append-and-tail at `mythic/events.jsonl` (last 200 entries; atomic rotation) | `PluginHookDispatcher.emit()`; TUI Recent Events panel |

For deeper coverage and composition patterns, read `docs/runtime.md`.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/Viking_Apache_V2_1.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/Viking_Apache_V2_1.jpg)

---

## Repository posture (important)

This repository holds multiple historical, research, and vendor islands accumulated over the life of the project. Not everything here is the active product. The living path is:

- **`mythic_vibe_cli/`**

Supporting active paths include:

- `tests/`
- `docs/`
- selected root governance records (`README`, `ARCHITECTURE`, `DATA_FLOW`, `DEVLOG`, `CHANGELOG`)

Most other trees are not active CLI runtime dependencies. Treat them as reference material or isolated experiments unless an architecture decision has explicitly drawn them into the product path.

---

## Documentation map

If you do not know where to stand, begin here and follow the stones in order:

1. `docs/INDEX.md` — canonical docs navigator
2. `docs/quickstart.md` — setup + first loop
3. `docs/ARCHITECTURE.md` — active runtime architecture
4. `docs/DOMAIN_MAP.md` — ownership + boundaries
5. `docs/api.md` — integration contracts
6. `docs/COMMAND_CONTRACTS.md` — durable contract surface for every command
7. `docs/runtime.md` — runtime primitives guide
8. `docs/plugins.md` — plugin authoring + dispatcher contract
9. `docs/SYSTEM_VISION.md` — product north star
10. `DEVLOG.md` — chronological continuity record
11. `CHANGELOG.md` — release-facing change history

---

## Development and quality checks

Before you offer your work to the hall, run the standard checks:

```bash
pytest -q
python -m ruff check mythic_vibe_cli tests
python -m mypy mythic_vibe_cli
python -m mythic_vibe_cli --help
mythic-vibe doctor
```

The full test suite lives under `tests/` (currently 270 tests + 14 subtests). CI runs the same gates in `.github/workflows/ci.yml`.

---

## Acknowledgements — third-party material

Mythic Vibe CLI is independent and original work, but it gratefully adapts a small number of well-tested primitives from open-source upstreams under their permissive licenses. We hold ourselves to the standard recorded in `MYTHIC_ENGINEERING_PLUNDERING_WORKFLOW.md` (License Gate, Boundary Law, Verification Law, Attribution Law) for every line of plundered material:

- Per-file headers name the upstream source, license, copyright holder, and the date adapted.
- The repo-root `THIRD_PARTY_NOTICES.md` reproduces the upstream permission text verbatim and lists every adapted file in a plunder map.
- The repo-root `NOTICE` file records this project's own Apache-2.0 attribution.
- Plunder operations themselves are tracked under `mythic/imports/plunder_manifest.json` when fetched via the `plunder` command.

### Pi (pi-coding-agent)

- **Project:** pi (pi-coding-agent) — package `packages/coding-agent`
- **Repository:** [badlogic/pi-mono](https://github.com/badlogic/pi-mono)
- **License:** MIT License
- **Copyright:** Copyright (c) 2025 Mario Zechner

The following Mythic runtime primitives are adapted from pi-coding-agent under the MIT permission notice reproduced in `THIRD_PARTY_NOTICES.md`. Each carries the standard per-file header and is independently tested in this repository:

| Mythic file | Pi upstream file |
|---|---|
| `mythic_vibe_cli/runtime/file_mutation_queue.py` | `packages/coding-agent/src/core/tools/file-mutation-queue.ts` |
| `mythic_vibe_cli/runtime/output_guard.py` | `packages/coding-agent/src/core/output-guard.ts` |
| `mythic_vibe_cli/runtime/event_bus.py` | `packages/coding-agent/src/core/event-bus.ts` |
| `mythic_vibe_cli/runtime/timings.py` | `packages/coding-agent/src/core/timings.ts` |
| `mythic_vibe_cli/runtime/slash_commands.py` | `packages/coding-agent/src/core/slash-commands.ts` |
| `mythic_vibe_cli/runtime/source_info.py` | `packages/coding-agent/src/core/source-info.ts` (synthetic factory only; PathMetadata-dependent factory not ported) |
| `mythic_vibe_cli/runtime/exec.py` | `packages/coding-agent/src/core/exec.ts` (Node-stdio quirk handler not needed in Python) |

`mythic_vibe_cli/runtime/event_log.py` is original to this project.

This project is independent and is **not** affiliated with, endorsed by, or sponsored by Mario Zechner, the pi-mono authors, or pi.dev.

### Required dependencies (declared in `pyproject.toml`)

- **Textual** (`textual>=0.80`) — pure-Python TUI framework, MIT-licensed, by Will McGugan and contributors. Used by `mythic-vibe tui`. Optional under the `[tui]` extra.
- **Rich** (`rich>=13.0`) — pure-Python rich-text rendering library, MIT-licensed, by Will McGugan and contributors. Optional under the `[ux]` extra.
- **anthropic** (`anthropic>=0.34`), **google-genai** (`google-genai>=1.0`), **openai** (`openai>=1.40`) — official client SDKs for the respective AI providers. Optional under the `[ai]` extra and only loaded when the matching adapter is selected.

The full upstream license text for plundered material lives in `THIRD_PARTY_NOTICES.md`. License files for installed dependencies ship with the corresponding wheels.

---

## License

Copyright (c) 2026 Volmarr Wyrd

Mythic Vibe CLI is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for the full license text and [NOTICE](NOTICE) for the project attribution.

For third-party material adapted into this codebase, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Per the Apache-2.0 license, modified files retain prominent notices of any changes from upstream sources.

Unless required by applicable law or agreed to in writing, this project is distributed on an "AS IS" BASIS, without warranties or conditions of any kind, either express or implied.

---

## Distribution and Privacy Position

Mythic Vibe CLI is published here as source code and project material.

The author does not require users to provide age, identity, government ID, biometric data, or similar personal information in order to access or use the source code in this repository.

The author may decline to provide official binaries, installers, hosted services, app-store releases, or other official distribution channels where doing so would require age verification, identity verification, or similar personal-data collection.

Any third party who forks, packages, redistributes, deploys, hosts, or otherwise makes this software available does so independently and is solely responsible for compliance with applicable law, platform policy, and distribution requirements in their own jurisdiction and context.

See [LEGAL-NOTICE.md](LEGAL-NOTICE.md) for details.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-23-RuneForgeAI.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-23-RuneForgeAI.jpg)

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/IMG_0407.jpeg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/IMG_0407.jpeg)

---
