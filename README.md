# Mythic Vibe CLI

An open-source vibe-coding CLI that **automatically follows the Mythic Engineering method** and is intentionally beginner-friendly.

Canonical Mythic Engineering source:
- https://github.com/hrabanazviking/Mythic-Engineering

## Why this is better now

This now supports a **ChatGPT Plus ($20/mo) friendly Codex workflow**:
- Generate a structured prompt packet from your local project context.
- Paste it into ChatGPT/Codex.
- Log the assistant output back into Mythic tracking.

No API key is required for this copy/paste flow.

## What this CLI enforces

- Architecture-first scaffolding aligned to Mythic Engineering docs.
- Required documentation starter files (`docs/`, `tasks/`, `MYTHIC_ENGINEERING.md`, `mythic/`).
- A phase-based execution loop:
  `intent -> constraints -> architecture -> plan -> build -> verify -> reflect`
- Progress tracking so you can keep collaborators in the loop with structured updates.

## Install

```bash
pip install -e .
```

## Quick start (new project)

```bash
mythic-vibe init --goal "Build a beginner-friendly TODO app" --noob
```

This creates a Mythic-oriented scaffold including:
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

## Import full Mythic markdown corpus

To import **all `.md` files** from the canonical Mythic Engineering repo into your project:

```bash
mythic-vibe import-md
```

By default this writes into `docs/mythic_source/` and creates an index file:
- `docs/mythic_source/_import_index.json`

Custom destination:

```bash
mythic-vibe import-md --target docs/reference/mythic
```

## ChatGPT Plus / Codex bridge flow

1) Generate a packet:

```bash
mythic-vibe codex-pack \
  --phase plan \
  --task "Implement the CLI command parser and file templates" \
  --audience beginner
```

2) Open `mythic/codex_prompt.md` and paste the `Prompt To Paste` section into ChatGPT/Codex.

3) Log the response summary:

```bash
mythic-vibe codex-log --phase build --response "Implemented parser with subcommands and docs updates"
```

4) Check current status:

```bash
mythic-vibe status
```

## Manual check-ins (without codex-log)

```bash
mythic-vibe checkin --phase intent --update "Defined user outcome and anti-goals"
```

## Method sync commands

Sync latest method notes from GitHub:

```bash
mythic-vibe sync
```

Print currently loaded method notes:

```bash
mythic-vibe method
```

---

![https://raw.githubusercontent.com/hrabanazviking/Mythic-Engineering/refs/heads/main/Viking_Apache_V2_1.jpg](https://raw.githubusercontent.com/hrabanazviking/Mythic-Engineering/refs/heads/main/Viking_Apache_V2_1.jpg)

## License

Copyright (c) 2026 Volmarr Wyrd

Mythic Engineering is licensed under the Apache License, Version 2.0.
See the [LICENSE](LICENSE) file for details.

Unless required by applicable law or agreed to in writing, this project is distributed on an "AS IS" BASIS, without warranties or conditions of any kind.

---

## Distribution and Privacy Position

Mythic-Engineering is published here as source code and project material.

The author does not require users to provide age, identity, government ID, biometric data, or similar personal information in order to access or use the source code in this repository.

The author may decline to provide official binaries, installers, hosted services, app-store releases, or other official distribution channels where doing so would require age verification, identity verification, or similar personal-data collection.

Any third party who forks, packages, redistributes, deploys, hosts, or otherwise makes this software available does so independently and is solely responsible for compliance with applicable law, platform policy, and distribution requirements in their own jurisdiction and context.

See [LEGAL-NOTICE.md](LEGAL-NOTICE.md) for details.

---

![https://raw.githubusercontent.com/hrabanazviking/Mythic-Engineering/refs/heads/main/IMG_0407.jpeg](https://raw.githubusercontent.com/hrabanazviking/Mythic-Engineering/refs/heads/main/IMG_0407.jpeg)

---

[Back to main](https://github.com/hrabanazviking/Mythic-Engineering)

---
