# Mythic Vibe CLI

Mythic Vibe CLI is an open-source, method-first command-line tool for people who want to **ship software with continuity, architecture, and recoverable memory** rather than pure improvisation.

It helps you run an explicit engineering loop:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

The project is designed to be useful for first-time builders and still disciplined enough for maintainers who care about clean handoffs, repeatability, and artifact-driven collaboration.

Canonical Mythic Engineering source:
- https://github.com/hrabanazviking/Mythic-Engineering

---

## What changed in this documentation pass

This repository now includes a much deeper documentation suite for active product paths:

- Expanded operator-facing docs for setup, commands, architecture, API contracts, and governance.
- Added a durable `CHANGELOG.md` with semantic structure and release notes discipline.
- Added `docs/INDEX.md` as a stable navigation hub for docs consumers and contributors.
- Updated `DEVLOG.md` with this documentation sweep so future sessions inherit context instead of guesswork.

If you are returning after a break, start at **`docs/INDEX.md`** first.

---

## Why Mythic Vibe CLI exists

Many coding tools optimize for speed while underinvesting in continuity. Mythic Vibe CLI is opinionated about preserving reasoning in files so work can survive context loss, team turnover, and interrupted sessions.

Core goals:

1. **Reduce drift** between plans, code, and docs.
2. **Improve AI-assisted execution** by packaging project context into explicit prompt packets.
3. **Preserve intent and rationale** so later contributors can resume without reconstruction.
4. **Keep the workflow beginner-safe** while still useful in complex projects.

---

## Core capabilities

### 1) Method-first project initialization

Scaffolds a project with opinionated documentation/task structure aligned to Mythic Engineering.

### 2) Phase-oriented workflow operations

Supports repeated movement through:
- intent
- constraints
- architecture
- plan
- build
- verify
- reflect

### 3) Prompt bridge for ChatGPT/Codex workflows

Generates structured prompt packets from local context, for copy/paste usage with ChatGPT/Codex.

### 4) Response logging for continuity

Lets you persist summaries of AI output so context is retained in local artifacts.

### 5) Diagnostics and status checks

Surfaces missing files, invalid state, and method drift early.

### 6) Configuration layering

Supports user-level + project-level config plus environment overrides.

---

## Install

```bash
pip install -e .
```

### Prerequisites

- Python 3.10+
- Git
- A shell environment (bash, zsh, PowerShell, etc.)

Recommended:
- A virtual environment (`venv`, `uv`, `conda`)
- Linting/formatting tools in your editor

---

## Quick start

Initialize a new project scaffold:

```bash
mythic-vibe init --goal "Build a beginner-friendly TODO app" --noob
```

This creates Mythic-oriented scaffolding such as:

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

1) Generate a context packet:

```bash
mythic-vibe codex-pack \
  --phase plan \
  --task "Implement the CLI command parser and file templates" \
  --audience beginner
```

2) Open `mythic/codex_prompt.md` and paste the `Prompt To Paste` section into ChatGPT/Codex.

3) Log the assistant outcome:

```bash
mythic-vibe codex-log --phase build --response "Implemented parser with subcommands and docs updates"
```

4) Inspect status:

```bash
mythic-vibe status
```

---

## Configuration model

Config resolution precedence (low → high):

1. `~/.mythic-vibe.json`
2. `$XDG_CONFIG_HOME/mythic-vibe/config.json`
3. `<project>/.mythic-vibe.json`
4. Environment variable overrides

Current supported environment overrides:

- `MYTHIC_EXCERPT_LIMIT`
- `MYTHIC_PACKET_CHAR_BUDGET`
- `MYTHIC_AUTO_COMPACT`

Inspect effective configuration:

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

This project now keeps an explicit documentation governance layer to reduce drift in long-lived sessions:

- `docs/INDEX.md` is the canonical documentation map.
- `docs/DOCUMENTATION_STANDARDS.md` defines writing and update obligations.
- `docs/SESSION_HANDOFF_TEMPLATE.md` provides a structured end-of-session handoff.
- `DEVLOG.md` and `CHANGELOG.md` are maintained as paired historical records (narrative + release-facing).

When changing behavior, update docs in the same commit or PR. Treat documentation drift as a functional bug, not an editorial nicety.

---

## Command overview

Primary command families include:

- `init` / `imbue`
- `codex-pack` / `evoke`
- `doctor` / `scry`
- `checkin`
- `status`
- `sync`
- `method`
- `weave`
- `prune`
- `heal`
- `oath`
- `grimoire add|list`
- `config set`
- `db migrate`

For full command behavior and contracts, see `docs/api.md`.

---

## Repository posture (important)

This repository contains multiple historical, research, and vendor islands. The active product path is:

- **`mythic_vibe_cli/`**

Supporting active paths include:

- `tests/`
- `docs/`
- selected root governance records (`README`, `ARCHITECTURE`, `DATA_FLOW`, `DEVLOG`, `CHANGELOG`)

Most other trees are not active CLI runtime dependencies and should be treated as reference or isolated experiments unless explicitly integrated by architecture decision.

---

## Documentation map

Start here:

1. `docs/INDEX.md` — canonical docs navigator
2. `docs/quickstart.md` — setup + first loop
3. `docs/ARCHITECTURE.md` — active runtime architecture
4. `docs/DOMAIN_MAP.md` — ownership + boundaries
5. `docs/api.md` — integration contracts
6. `docs/SYSTEM_VISION.md` — product north star
7. `DEVLOG.md` — chronological continuity record
8. `CHANGELOG.md` — release-facing change history

---

## Development and quality checks

Typical local checks:

```bash
pytest -q
python -m mythic_vibe_cli.cli --help
mythic-vibe doctor
```

(Availability depends on environment and install mode.)

---

## License

Copyright (c) 2026 Volmarr Wyrd

Mythic Engineering is licensed under the Apache License, Version 2.0.
See `LICENSE` for details.

Unless required by applicable law or agreed to in writing, this project is distributed on an "AS IS" BASIS, without warranties or conditions of any kind.

---

## Distribution and privacy position

Mythic-Engineering is published as source code and project material.

The author does not require users to provide age, identity, government ID, biometric data, or similar personal information to access the source code in this repository.

The author may decline official binaries/installers/hosted distribution channels where publication would require age or identity verification.

Any third party who forks, hosts, redistributes, or packages this software does so independently and is solely responsible for legal/platform compliance in their own context.

See `LEGAL-NOTICE.md` for details.
