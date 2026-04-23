# Mythic Vibe CLI Documentation Hub

Welcome to the active documentation hub for **Mythic Vibe CLI**, a method-driven command-line system for building software with explicit phases, durable artifacts, and cleaner collaboration handoffs.

If you are new, begin with `quickstart.md`. If you are contributing, begin with `ARCHITECTURE.md` and `DOMAIN_MAP.md`.

> Canonical navigation map: `docs/INDEX.md`.

---

## What this project does

Mythic Vibe CLI helps builders move from idea to implementation via a repeatable engineering loop:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

Rather than relying on memory alone, the CLI writes structured artifacts so sessions can pause and resume without losing rationale.

---

## Documentation map

### Start here

1. **[Quickstart](quickstart.md)**  
   Installation, setup, first operational loop, and troubleshooting.
2. **[System Vision](SYSTEM_VISION.md)**  
   Product goals, promises, anti-goals, and evolution strategy.
3. **[Architecture](ARCHITECTURE.md)**  
   Active runtime boundaries, component responsibilities, and dependency direction.

### Governance and boundaries

- **[Domain Map](DOMAIN_MAP.md)** — authoritative ownership map for active vs dormant domains.
- **[API Reference](api.md)** — CLI/module interfaces and filesystem contracts.
- **[Hardware Profiles](hardware_profiles.md)** — execution guidance for constrained and high-end environments.

### Continuity and release history

- **[Root DEVLOG](../DEVLOG.md)** — chronological record of meaningful decisions and sessions.
- **[Root CHANGELOG](../CHANGELOG.md)** — release-facing summary of what changed and why it matters.

---

## Recommended reading paths

### Path A — First-time user (10–15 minutes)

1. Read [Quickstart](quickstart.md).
2. Run one complete phase loop.
3. Skim [System Vision](SYSTEM_VISION.md).
4. Bookmark [API Reference](api.md) for commands and contracts.

### Path B — Contributor (20–30 minutes)

1. Read [Architecture](ARCHITECTURE.md).
2. Read [Domain Map](DOMAIN_MAP.md).
3. Read [API Reference](api.md).
4. Review [Root DEVLOG](../DEVLOG.md) for recent decisions.

### Path C — Maintainer / release owner

1. Review [Root CHANGELOG](../CHANGELOG.md).
2. Validate docs remain synchronized with behavior.
3. Verify boundary and dependency rules before merge.

---

## Documentation discipline

When behavior changes, update documentation in the same PR:

- Behavior or command contract changes -> `api.md` and/or `quickstart.md`
- Architecture or flow changes -> `ARCHITECTURE.md`
- Ownership/boundary changes -> `DOMAIN_MAP.md`
- Product intent changes -> `SYSTEM_VISION.md` and `README.md`
- Session continuity context -> `DEVLOG.md`
- User-facing release summary -> `CHANGELOG.md`

If docs and behavior diverge, treat it as a bug.

---

## Active product status note

This repository is a multi-project monorepo. The active product runtime path is **`mythic_vibe_cli/`**. Other trees include research material, vendor mirrors, and isolated historical/runtime experiments.
