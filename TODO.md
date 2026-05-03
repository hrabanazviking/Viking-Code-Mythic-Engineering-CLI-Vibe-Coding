# TODO

**Last reviewed:** 2026-05-03 (v1.0.0 launch)

> **v1.0.0 status header.** Most items in the historical backlog below were
> closed during the PH-01 → PH-20 cycle that culminated in the v1.0.0
> launch. This file is kept as a continuity record, not a live planning
> doc. The current planning surfaces are:
>
> - **`TASK_PH19_DISTRIBUTION.md`** — live PH-19 + PH-20 + PH-21 + PH-22 plan tracker (still updated additively).
> - **`docs/RELEASE_CHECKLIST.md`** — pre-tag manual gates.
> - **`docs/governance/quarterly_review.md`** — quarterly architecture review cadence.
> - **`MYTHIC_VIBE_CLI_MASTER_ROADMAP.md`** — single-source-of-truth roadmap.

## v1.0.0 — what closed

The historical bullets below all map to phases that landed in v1.0.0:

| Historical bullet | Status |
|---|---|
| Robustness rounds 1-4 (multiple bullets below) | ✓ Closed via PH-15 + PH-18 (robustness sweeps) + PH-19.0 (10-fix bug sweep) |
| Pi plundering | ✓ Closed via PH-09-era plunder + 7 plundered runtime primitives (see `THIRD_PARTY_NOTICES.md`) |
| V2 Roadmap Phase 3 (TUI) | ✓ Closed via PH-04 (TUI build-out) + PH-20.I (opt-in heatmap + plugin risk panels) |
| V2 Roadmap Phase 4 | ✓ Closed |
| "Massive number of slash commands" | ✓ ~60 slash entries in `BUILTIN_SLASH_COMMANDS` (see `mythic_vibe_cli/runtime/slash_commands.py`) |
| Vibe_Coding_CLI_Tools aggregate-feature plan | ✓ Folded into the master roadmap; PH-20 polished v1.0 features |
| Bug / missing-feature / orphan-code audit + remediation | ✓ Closed via 2026-05-02 audit cycle (see `AUDIT_*_2026-05-02.md` + `AUDIT_REMEDIATION_CLOSEOUT_2026-05-02.md`) |
| All-code-robust additive remediation rounds | ✓ Closed via PH-19.0 + PH-19.4 (property tests) + PH-20 (polish) |

## v1.x post-launch backlog

Forward-looking items now sit in `TASK_PH19_DISTRIBUTION.md` under the PH-21 + PH-22 sections. Highlights:

- **PH-21** (v1.x distribution expansion) — OCI / PyInstaller / Nuitka / macOS notarization / Sigstore / AUR / winget / Termux.
- **PH-22** (v2.0 strategic stretch) — Rust/Go launcher shim / native Android wrapper / WASI runtime.

These are deliberately out of v1.0 scope and are flagged as multi-week+ items in the plan tracker.

## Operational queue

Items that re-enter the active queue post-launch follow the [`docs/governance/quarterly_review.md`](docs/governance/quarterly_review.md) cadence — the next scheduled architecture review is the right moment to re-evaluate whether anything below should be promoted back to active scope.

---

## Historical backlog (preserved for continuity, 2026-05-03)

The original entries below are kept verbatim. They predate the v1.0.0 launch and are now superseded by the status table above. Do not edit these in place; if any item needs reactivation, capture it as a fresh entry under "Operational queue" or in `TASK_PH19_DISTRIBUTION.md`.

- After all of the current roadmap steps(both present and upcoming) are completed 100% and the current list if steps are done, the  start on Mythic_Vibe_CLI_ The_2026_Expansion_Roadmap.md
- Work on all steps in MYTHIC_VIBE_CLI_EXPANSION_ROADMAP_V2.md
- Work on all repo issues.
- Create a massive amount of / commands, including all the ones that other cli vibe coding apps have.
- Read and study Vibe_Coding_CLI_Tools_-_Aggregate_Feature_and_Interface_Report.md and come up with a massive multistep MD file plased plan to implement, in a very robust amd advanced way, every single feature that Vibe_Coding_CLI_Tools_-_Aggregate_Feature_and_Interface_Report.md  lists.
- Start the plan to implement every feature from Vibe_Coding_CLI_Tools_-_Aggregate_Feature_and_Interface_Report.md
- Check all code for bugs, incomplete code, missing features, not integrated code, orphaned code, imcomplete features, issues, inefficiencies, etc, and make a MD multiple step plan to fix all and improve all, only using additive methods. After consulting with Volmarr the human, begin the first step of the plan.
- Consult all plundering documents, and begin lawful code plundering, while keeping mindful of the plundering documents instructions, and any information at the repos of each plundered project. Be sure to keep it legal, ethical, and in alignment with opensource standards for plundering.
- Make all code robust, error correcting, bug resistant, self healing, platform agnostic, file location agnostic, use api for internal communication, modular.
- Do a second round of make all code robust, error correcting, bug resistant, self healing, platform agnostic, file location agnostic, use api for internal communication, modular.
- Do a third round of make all code robust, error correcting, bug resistant, self healing, platform agnostic, file location agnostic, use api for internal communication, modular.
- Do a fourth round of make all code robust, error correcting, bug resistant, self healing, platform agnostic, file location agnostic, use api for internal communication, modular.
- Check all code for bugs, incomplete code, missing features, not integrated code, orphaned code, imcomplete features, issues, inefficiencies, etc, and make a MD multiple step plan to fix all and improve all, only using additive methods. After consulting with Volmarr the human, begin the first step of the plan.
- Create a plundering document for https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent based on the other plunder documents. Be sure it explains how to do lawful plundering that keeps the plundering legal, ethical, and in alignment with opensource standards for plundering.
- Consult the Pi ( https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent ) plundering documents, and begin lawful code plundering of Pi, while keeping mindful of the plundering documents instructions, and any information at the repos of each plundered project. Be sure to keep it legal, ethical, and in alignment with opensource standards for plundering.
- Do V2 Roadmap Phase 3+ (TUI)
- Do V2 Roadmap Phase 4
