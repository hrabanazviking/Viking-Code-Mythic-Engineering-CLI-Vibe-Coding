# TASK — Pi (pi-mono coding-agent) Plundering Guide

**Opened:** 2026-04-29
**Owner:** Runa
**TODO source:** Item #14 in `TODO.md` — *"Create a plundering document for https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent based on the other plunder documents."*
**Successor:** Item #15 — actually plunder Pi using the guide produced here.

---

## Goal

Land a single new file `Pi_Coding_Agent_Plundering_Guide.md` in the repo root, modeled on the existing siblings:

- `Aider_Plundering_Guide.md`
- `OpenAI_Codex_CLI_Plundering_Guide.md`
- `Gemini_CLI_Plundering_Guide.md`
- `Goose_Plundering_Guide.md`
- `Mistral_Vibe_Plundering_Guide.md`
- `Qwen_Code_Plundering_Guide.md`
- `Lawful_Code-Raiding_Guide_Reusing_Apache-2.0_Code_from_Kimi_CLI.md` (meta-guide)

Naming: `Pi_Coding_Agent_Plundering_Guide.md` (the package being plundered is `pi-mono/packages/coding-agent`, not the whole monorepo).

## Required Sections

Match the canonical Aider-guide structure:

1. **Purpose** — what Pi/coding-agent is, why we'd plunder it
2. **Core Legal Position** — confirm license, state our stance
3. **Required Source Links** — anchored upstream URLs as footnotes
4. **Core License Duties** — keep license, preserve notices, add third-party notices
5. **Branding Warning** — what we cannot call our derivative
6. **Repo Structure Worth Studying** — the file tree of `packages/coding-agent`
7. **Highest-Value Plunder Targets** — per-folder breakdown of what to study
8. **Do / Do Not** — concrete dos and don'ts
9. **Suggested Mythic Mapping** — Pi subsystem → Mythic Vibe CLI target path
10. **Final Checklist Before Publishing** — the additive ship gate
11. **Clean Rule** — three-line poetic summary in the house style
12. **Footnotes** — numbered upstream links

## Research Required (web)

- pi-mono README at `https://github.com/badlogic/pi-mono`
- coding-agent package README/source at `https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent`
- LICENSE at the repo root (confirm permissive — likely MIT/Apache-2.0; license drives the entire stance section)
- File tree of `packages/coding-agent/` for the structural inventory

## Out of Scope

- Actually plundering Pi code (that is item #15, a separate slice)
- Editing other plunder guides
- Adding pi-mono to the root README until the actual plundering happens
- Modifying `NOTICE` / `THIRD_PARTY_NOTICES.md` until item #15 lands

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed to development
- [x] License confirmed (MIT, Copyright (c) 2025 Mario Zechner)
- [x] Repo structure surveyed via `gh api` (root + src + core + tools + modes + utils + test + docs)
- [x] Coding-agent package surveyed (README + LICENSE + ~30 src files + ~90 test files mapped)
- [x] Guide draft landed at `Pi_Coding_Agent_Plundering_Guide.md` (759 lines, 13 sections + footnotes)
- [x] Memory snapshot updated
- [x] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Use WebFetch (now in the global allow list) to pull the four targets in *Research Required*.
3. Write the guide using the Aider guide as the structural template.
4. Confirm the license stance section reflects the *actual* upstream license, not assumption.
5. Land + push. No code changes; this is documentation only.
