---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/120329a8-9f29-4177-b10f-56719c134843.png](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/120329a8-9f29-4177-b10f-56719c134843.png)

---

# Mythic Vibe CLI

Mythic Vibe CLI is an open-source, method-first command-line tool for builders who want to **ship software with continuity, architecture, and recoverable memory** — not just momentum.

It enforces an explicit engineering loop that keeps your reasoning alive on disk:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

The hall is wide enough for a first-time builder finding their footing, and disciplined enough for a seasoned maintainer who cares about clean handoffs, repeatable process, and artifacts that outlive any single session.

Canonical Mythic Engineering source:
- https://github.com/hrabanazviking/Mythic-Engineering

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/ee5643a3-eb8a-4100-98ad-d4e8b9eeb1b0.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/ee5643a3-eb8a-4100-98ad-d4e8b9eeb1b0.jpg)

---

## What changed in this documentation pass

The scrolls have been deepened. This repository now carries a fuller documentation suite built for the people who actually have to work here:

- Expanded operator-facing docs for setup, commands, architecture, API contracts, and governance.
- Added a durable `CHANGELOG.md` with semantic structure and release notes discipline.
- Added `docs/INDEX.md` as a stable navigation hub for docs consumers and contributors.
- Updated `DEVLOG.md` with this documentation sweep so future sessions inherit context instead of guesswork.

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

### 5) Diagnostics and status checks

Surfaces missing files, invalid state, and method drift early — before they compound into the kind of confusion that costs an afternoon to unravel.

### 6) Configuration layering

Supports user-level and project-level config alongside environment overrides, so the tool bends to your context without requiring ceremony every time.

---

## Install

Step through the door:

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

When you change behavior, update the docs in the same commit or PR. Treat documentation drift as a functional bug, not an editorial nicety.

---

## Command overview

The hall offers many instruments. Primary command families include:

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
6. `docs/SYSTEM_VISION.md` — product north star
7. `DEVLOG.md` — chronological continuity record
8. `CHANGELOG.md` — release-facing change history

---

## Development and quality checks

Before you offer your work to the hall, run the standard checks:

```bash
pytest -q
python -m mythic_vibe_cli.cli --help
mythic-vibe doctor
```

---
---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/Viking_Apache_V2_1.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/Viking_Apache_V2_1.jpg)

## License

Copyright (c) 2026 Volmarr Wyrd

Mythic Engineering is licensed under the Apache License, Version 2.0.
See the [LICENSE](LICENSE) file for details.

Unless required by applicable law or agreed to in writing, this project is distributed on an "AS IS" BASIS, without warranties or conditions of any kind.

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

