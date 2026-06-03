# Repository Boundary

This repository contains one active packaged product and several dormant or reference code islands. The active product must stay independently installable, testable, and importable without importing those islands directly.

## Active Runtime Path

The active runtime is `mythic_vibe_cli/`.

Code under this path may import the Python standard library, declared package dependencies, and other modules inside `mythic_vibe_cli/`. It must not directly import dormant top-level repository packages such as `ai`, `core`, `systems`, `sessions`, `imports`, `yggdrasil`, `mindspark_thoughtform`, `ollama`, `whisper`, or `chatterbox`.

## Dormant Islands

Dormant islands remain source, reference, research, or optional integration material until an adapter makes the boundary explicit. Optional integrations must be reached through a small module inside `mythic_vibe_cli/`, guarded by configuration or feature flags, and documented by an ADR when the boundary is non-trivial.

## Required Checks

Before merging boundary-sensitive work, run:

```bash
mythic-vibe doctor --repo-boundary --path .
```

The command verifies this file, the active product boundary docs, dormant island docs, and the ADRs that define the import rules.
