# Task: Reforge Roadmap Phase Implementation

**Created:** 2026-06-02
**Branch:** `development`
**Roadmap:** `Mythic_Vibe_CLI_Reforge_Roadmap.md`
**Owner role:** Architect + Forge Worker + Auditor

## Target

Implement the roadmap phases in order, starting with Phase 0 and advancing only after each phase has a clear artifact, verification path, and documentation update.

## Current State

- The repository is on `development` with Phase 9 implemented and verification passing locally.
- `TODO.md` is historical and points at older v1.0 planning surfaces.
- `Mythic_Vibe_CLI_Reforge_Roadmap.md` defines the new rebirth direction: Mythic should become a terminal-based coding companion CLI, not primarily a DevOps-style command catalog.
- `docs/PRODUCT_INTENT.md` records the companion-shell product intent.
- `mythic_vibe_cli/cli.py` is a thin public re-export into `mythic_vibe_cli/app.py`.
- The console scripts `mythic` and `mythic-vibe` both currently target `mythic_vibe_cli.cli:main`.
- A prior REPL exists in `mythic_vibe_cli/repl.py`, and older docs/devlog entries mention `mythic-vibe shell`.

## Phase Order

1. Phase 0: Create `docs/PRODUCT_INTENT.md` and make product intent unambiguous. Completed in commit `68de233`.
2. Phase 1: Rebuild the default `mythic` entrypoint so it launches the companion shell by default while preserving admin access to older commands. Completed in commit `9ce2e25`.
3. Phase 2: Ensure the minimal interactive shell includes startup banner, repo detection, model display, input loop, slash routing, normal prompt routing, and `/help`, `/status`, `/model`, `/exit`. Completed in commit `4c529eb`.
4. Phase 3: Make natural-language shell requests trigger repository context inspection. Completed in commit `e581afd`.
5. Phase 4: Wire model selection and provider-backed natural prompts into the companion shell. Completed in commit `8c76eec`.
6. Phase 5: Add the local SQLite memory spine at `.mythic/memory.sqlite`, wire companion-shell natural prompts into it, and answer "What were we doing last time?" from durable memory. Completed in the current Phase 5 implementation commits.
7. Phase 6: Add a read-only configurable private knowledge reader with SQLite-first support, shell `/knowledge` access, and natural knowledge-search prompts. Completed in the current Phase 6 implementation commit.
8. Phase 7: Add the GitHub workspace system: default workspace root, clone/open/status, branch creation/tracking, PR draft preparation, and natural clone/branch proposal prompts. Completed in the current Phase 7 implementation commit.
9. Phase 8: Add the Patch Proposal System: in-memory patch staging, generating diffs, applying patches, rejecting patches, and `/diff`, `/apply`, `/reject` slash commands. Completed in the current Phase 8 implementation commit.
10. Phase 9: Test Runner: integrating test execution into the companion shell, summarizing failures, and feeding failures into the model for self-healing. Completed in the current Phase 9 implementation commit.
11. Phase 10: TUI Integration: making the TUI the core visual cockpit for the companion shell with a tabbed interface. Completed in the current Phase 10 implementation commit.
12. Phase 11: Legacy Command Demotion: suppressing legacy commands from the main help screen to emphasize the shell. Completed in the current Phase 11 implementation commit.
13. Phase 12: Documentation Rewrite: updating docs folder with new paradigm documents. Completed in the current Phase 12 implementation commit.
14. Phase 13: Quarantine Non-Code Debris: organized unused media, research, and old documents into graveyard/. Completed in the current Phase 13 implementation commit.
15. Phase 14+: Continue in roadmap order.

## Phase 9 Proposed Files

- `mythic_vibe_cli/verify/test_runner.py` (updated to summarize failures)
- `mythic_vibe_cli/repl.py` (updated to handle `/test` and test failures)
- `mythic_vibe_cli/runtime/slash_commands.py` (updated with `/test`)
- `tests/test_test_cli.py` (new tests)
- Documentation records (`CHANGELOG.md`, `DEVLOG.md`, `README.md`, `docs/COMMAND_CONTRACTS.md`, this task brief)

## Phase 8 Proposed Files

- `mythic_vibe_cli/patch/__init__.py`
- `mythic_vibe_cli/patch/manager.py`
- `mythic_vibe_cli/patch/README_AI.md`
- `tests/test_patch_manager.py`
- `tests/test_patch_cli.py`
- `mythic_vibe_cli/repl.py` (updated)
- `mythic_vibe_cli/runtime/slash_commands.py` (updated)
- Documentation records (`CHANGELOG.md`, `DEVLOG.md`, `README.md`, `docs/COMMAND_CONTRACTS.md`, this task brief)

## Phase 7 Proposed Files

- `mythic_vibe_cli/workspaces/__init__.py`
- `mythic_vibe_cli/workspaces/manager.py`
- `mythic_vibe_cli/workspaces/README_AI.md`
- `mythic_vibe_cli/app.py`
- `mythic_vibe_cli/commands.py`
- `mythic_vibe_cli/repl.py`
- `mythic_vibe_cli/runtime/slash_commands.py`
- `tests/test_workspace_manager.py`
- `tests/test_workspace_cli.py`
- `tests/test_repl.py`
- Documentation records (`CHANGELOG.md`, `DEVLOG.md`, `README.md`, `docs/COMMAND_CONTRACTS.md`, this task brief)

## Phase 6 Proposed Files

- `mythic_vibe_cli/knowledge/__init__.py`
- `mythic_vibe_cli/knowledge/reader.py`
- `mythic_vibe_cli/config.py`
- `mythic_vibe_cli/app.py`
- `mythic_vibe_cli/commands.py`
- `mythic_vibe_cli/repl.py`
- `mythic_vibe_cli/runtime/slash_commands.py`
- `tests/test_knowledge_reader.py`
- `tests/test_knowledge_cli.py`
- `tests/test_repl.py`
- Documentation records (`CHANGELOG.md`, `DEVLOG.md`, `README.md`, `docs/COMMAND_CONTRACTS.md`, this task brief)

## Phase 5 Proposed Files

- `mythic_vibe_cli/memory/spine.py`
- `mythic_vibe_cli/repl.py`
- `mythic_vibe_cli/app.py`
- `mythic_vibe_cli/commands.py`
- `tests/test_memory_spine.py`
- `tests/test_memory_cli.py`
- `tests/test_repl.py`
- Documentation records (`CHANGELOG.md`, `DEVLOG.md`, `README.md`, `docs/COMMAND_CONTRACTS.md`, this task brief)

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

## Phase 7 Verification

- Focused tests: `python -m pytest tests/test_workspace_manager.py tests/test_workspace_cli.py tests/test_repl.py tests/test_cli_kernel.py`
- Lint: `ruff check mythic_vibe_cli/workspaces mythic_vibe_cli/app.py mythic_vibe_cli/commands.py mythic_vibe_cli/repl.py mythic_vibe_cli/runtime/slash_commands.py tests/test_workspace_manager.py tests/test_workspace_cli.py tests/test_repl.py tests/test_cli_kernel.py`
- Broad regression subset: `python -m pytest tests/test_repl.py tests/test_cli.py tests/test_cli_kernel.py tests/test_slash_commands.py tests/test_slash_parity.py tests/test_slash_inspect.py tests/test_docs_site.py tests/test_memory_cli.py tests/test_memory_spine.py tests/test_knowledge_reader.py tests/test_knowledge_cli.py tests/test_workspace_manager.py tests/test_workspace_cli.py tests/test_ai_route_cli.py tests/test_ai_models_cli.py`

## Next Step

Commit and push Phase 7, then begin Phase 8 patch proposal-system work.
