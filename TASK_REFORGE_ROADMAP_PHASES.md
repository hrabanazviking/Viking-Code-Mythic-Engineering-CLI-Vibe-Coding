# Task: Reforge Roadmap Phase Implementation

**Created:** 2026-06-02
**Branch:** `development`
**Roadmap:** `Mythic_Vibe_CLI_Reforge_Roadmap.md`
**Owner role:** Architect + Forge Worker + Auditor

## Target

Implement the roadmap phases in order, starting with Phase 0 and advancing only after each phase has a clear artifact, verification path, and documentation update.

## Current State

- The repository is on `development` at commit `e6e91cd`.
- `TODO.md` is historical and points at older v1.0 planning surfaces.
- `Mythic_Vibe_CLI_Reforge_Roadmap.md` defines the new rebirth direction: Mythic should become a terminal-based coding companion CLI, not primarily a DevOps-style command catalog.
- `docs/PRODUCT_INTENT.md` does not exist yet.
- `mythic_vibe_cli/cli.py` is a thin public re-export into `mythic_vibe_cli/app.py`.
- The console scripts `mythic` and `mythic-vibe` both currently target `mythic_vibe_cli.cli:main`.
- A prior REPL exists in `mythic_vibe_cli/repl.py`, and older docs/devlog entries mention `mythic-vibe shell`.

## Phase Order

1. Phase 0: Create `docs/PRODUCT_INTENT.md` and make product intent unambiguous. Completed in commit `68de233`.
2. Phase 1: Rebuild the default `mythic` entrypoint so it launches the companion shell by default while preserving admin access to older commands. Completed in commit `9ce2e25`.
3. Phase 2: Ensure the minimal interactive shell includes startup banner, repo detection, model display, input loop, slash routing, normal prompt routing, and `/help`, `/status`, `/model`, `/exit`. Completed in commit `4c529eb`.
4. Phase 3: Make natural-language shell requests trigger repository context inspection. Completed in the next Phase 3 implementation commit after `4c529eb`.
5. Phase 4+: Continue in roadmap order after verification of the prior phase.

## Phase 0 Proposed Files

- `docs/PRODUCT_INTENT.md`
- `docs/INDEX.md` or related docs index if needed to make the new intent discoverable
- `README.md` only if Phase 0 needs a short pointer to prevent future misunderstanding

## Constraints

- Do not delete existing command code.
- Preserve old command functionality as internal or admin-accessible machinery.
- Keep active product code inside `mythic_vibe_cli/`.
- Do not introduce dependencies from active product code into dormant islands.
- Avoid absolute paths and hardcoded user-specific configuration.
- Add tests when code behavior changes.
- Keep documentation current with each completed phase.

## Verification Plan

- For Phase 0: confirm `docs/PRODUCT_INTENT.md` exists and states the corrected product definition, primary entrypoint, secondary slash-command role, and preservation rule.
- For code phases: run targeted unit tests for the entrypoint, REPL, slash routing, and status/model behavior.
- Run broader tests only after scoped changes pass or when shared command behavior is touched.

## Next Step

Complete Phase 2 verification and then begin Phase 3 context-builder work.
