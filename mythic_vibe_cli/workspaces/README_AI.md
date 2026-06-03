# Workspace Package Notes

This package owns the Reforge Phase 7 local Git/GitHub workspace layer.

## Purpose

- Resolve the default Mythic workspace root.
- Record known local repositories in a workspace registry.
- Propose clone, branch, tracking, and PR-draft actions.
- Execute Git mutations only through explicit command flags.

## Rules

- Natural-language shell prompts must use proposal helpers only.
- `clone` and `branch` mutations stay gated behind `--yes`.
- PR draft file writes stay gated behind `--write`.
- Workspace state belongs under the configured workspace root, defaulting to `~/.mythic-vibe/workspaces/`.
- Keep this package independent from provider routing, memory persistence, and private-knowledge readers.
