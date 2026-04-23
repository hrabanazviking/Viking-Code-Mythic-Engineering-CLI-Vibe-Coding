# Mythic Vibe CLI Documentation Hub

Welcome to the canonical documentation hub for **Mythic Vibe CLI**, a method-driven command-line tool for building software through explicit engineering phases.

> If you are new, start with **Quickstart**. If you are contributing, read **Architecture** and **Domain Map** next.

---

## What this project is

Mythic Vibe CLI helps you move from idea to implementation with a repeatable workflow:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

Instead of relying on implicit memory, the CLI writes decisions into durable artifacts so you can pause, resume, and collaborate with less confusion.

---

## Documentation map

### Start here

1. **[Quickstart](quickstart.md)**
   Install, initialize, and run your first project loop.
2. **[System Vision](SYSTEM_VISION.md)**
   Product intent, quality bar, and long-term direction.
3. **[Architecture](ARCHITECTURE.md)**
   Active runtime boundaries and dependency direction.

### Governance and boundaries

- **[Domain Map](DOMAIN_MAP.md)** — source-of-truth ownership map for active vs dormant domains.
- **[API Reference](api.md)** — public Python and CLI integration surfaces.
- **[Hardware Profiles](hardware_profiles.md)** — deployment guidance for constrained and high-end machines.

---

## Who this is for

- **Solo builders** who need a reliable workflow, not just command sprawl.
- **Small teams** who want traceable decisions and better handoffs.
- **AI-assisted developers** who need structured context packets and method continuity.

---

## Recommended reading paths

### Path A: New user (10–15 minutes)

1. Read [Quickstart](quickstart.md)
2. Run one full CLI loop
3. Scan [System Vision](SYSTEM_VISION.md)

### Path B: Contributor / maintainer (20–30 minutes)

1. Read [Architecture](ARCHITECTURE.md)
2. Read [Domain Map](DOMAIN_MAP.md)
3. Review [API Reference](api.md)
4. Verify boundaries before opening a PR

---

## Documentation standards

When you update runtime behavior, update docs in the same PR:

- **Behavior change** -> `api.md` and/or `quickstart.md`
- **Boundary/ownership change** -> `ARCHITECTURE.md` and `DOMAIN_MAP.md`
- **Product direction change** -> `SYSTEM_VISION.md`

If docs and behavior diverge, treat it as a bug.

---

## Project status note

This repository is a multi-project monorepo. The active product path is **`mythic_vibe_cli/`**. Other trees include research, vendor mirrors, and historical/runtime experiments that are not primary CLI execution paths.
