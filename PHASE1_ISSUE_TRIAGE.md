---
title: "Phase 1 — GitHub Issue Triage (Slice 1.2)"
phase: PH-01
slice: 1.2
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_triage: 00daa67
issues_repo: hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
open_count: 21
closed_count: 0
discipline: read-only — no GitHub interaction performed; Volmarr owns all close/comment actions
status: complete
---

# Phase 1 GitHub Issue Triage (Slice 1.2)

## Purpose

Match every open issue on the GitHub repo against the unified
`MYTHIC_VIBE_CLI_MASTER_ROADMAP.md` to:

1. Assign each issue a phase/slice destination so it ceases to be
   stranded backlog.
2. Identify duplicates (multiple issues describing one body of work).
3. Identify already-shipped fragments worth flagging for partial close.
4. Produce a disposition recommendation for each issue (keep-open /
   merge-into-other / convert-to-slice / close-as-shipped).

This slice **does not perform any GitHub interaction**. No comments
are posted, no issues are closed, no labels are changed. Volmarr
performs all GitHub actions personally — the durable working
preference is that the assistant proposes; the human commits.

## Inputs

- `gh issue list --state open --limit 200` → 21 issues, numbered #27
  through #47, all opened 2026-04-25 by `hrabanazviking`.
- 7 GitHub label groups (Phase 1–7 in the *issue-tracker* numbering,
  which predates the master-roadmap Phase 1–20 numbering).
- Cross-references against `MYTHIC_VIBE_CLI_MASTER_ROADMAP.md`,
  `PHASE1_RUNTIME_AUDIT.md`, and `CHANGELOG.md`.

## Important nomenclature note

The GitHub issue labels say "Phase 1: The Core Brain", "Phase 5: The
Shield Wall", etc. These are **not** the same as the master-roadmap
phases (PH-01 Foundation Audit … PH-20 v1.0.0 Launch). To avoid
collision, this document uses:

- `GHL-N` for the GitHub label group (the older issue-tracker phase
  numbering).
- `PH-NN` for the master-roadmap phase.

| GHL | Label name | Open issues |
|---|---|---|
| GHL-1 | Phase 1: The Core Brain | #27, #28, #29 |
| GHL-2 | Phase 2: The Guard & Governance | #30, #31, #32 |
| GHL-3 | Phase 3: The Expansion Tools | #33, #34, #35 |
| GHL-4 | Phase 4: Testing & Quality Assurance | #36, #37, #38 |
| GHL-5 | Phase 5: Security & Governance (The Shield Wall) | #39, #40, #41 |
| GHL-6 | Phase 6: CI/CD & Deployment | #42, #43, #44 |
| GHL-7 | Phase 7: Collaboration & Multi-Agent Logic | #45, #46, #47 |

## Disposition codes

| Code | Meaning |
|---|---|
| **CONVERT** | Issue should remain open; convert it into one or more master-roadmap slices |
| **MERGE-INTO** | Issue duplicates another open issue; recommend closing this one with a "tracked in #N" comment |
| **PARTIAL-SHIPPED** | Some of the issue body is already implemented; recommend updating the issue to reflect what remains |
| **KEEP-OPEN** | Issue is valid as-is and tracked by a master-roadmap phase; no immediate action |
| **CLOSE-AS-SHIPPED** | Issue is fully addressed by code already on the development branch |

---

## Triage table

| # | Title | GHL | Master-roadmap home | Disposition | Notes |
|---|---|---|---|---|---|
| 27 | Implement Intent Interpretation Logic | 1 | PH-03 (forge agent) + PH-05 (graph retrieval) | CONVERT | The current `intent capture` flow only records text. Real interpretation belongs to the Architect agent (PH-03 slice 3.1) backed by knowledge-graph retrieval (PH-05 slice 5.3). |
| 28 | Repository-Wide Semantic Search | 1 | PH-05 slice 5.5 (`graph query`) | CONVERT | Direct mapping. The slash command `/search` is reserved for this in PH-02. |
| 29 | Context Anchoring (CLAUDE.md / AGENTS.md) | 1 | PH-10 slice 10.4 (artefact templates) + PH-15 (memory) | PARTIAL-SHIPPED | `init` already writes `MYTHIC_ENGINEERING.md` + `docs/INDEX.md`. The remaining work is generating CLAUDE.md / AGENTS.md / .cursorrules variants — added as new templates in PH-10. |
| 30 | Automated Policy Generation | 2 | PH-14 slice 14.1 (constraint store) | CONVERT | Becomes the policy engine work. Note duplicate body with #40. |
| 31 | Conventional Commit Enforcement | 2 | PH-12 slice 12.1 (CI scaffold) | CONVERT | Adds a `commitlint`-equivalent gate to the generated GitHub Actions workflow. |
| 32 | Vulnerability Auto-Fix Pipeline | 2 | PH-11 slice 11.3 (secret scanner) + PH-13 slice 13.3 (heal v2) | CONVERT | "Scan" is PH-11; "auto-fix" is PH-13. Note duplicate body with #39. |
| 33 | One-Click Cloud Deployment | 3 | PH-12 slice 12.2 (docker) + 12.3 (release) | MERGE-INTO #43 | Same scope as #43; recommend closing #33 in favour of #43 (which also says "Infrastructure as Code"). |
| 34 | Multi-Platform Interface (Web/Mobile/Telegram) | 3 | PH-17 (Multi-Surface Access) | CONVERT | Becomes PH-17 wholesale. Note overlap with #47 (mobile/telegram subset). |
| 35 | MCP Server Integration | 3 | PH-16 slice 16.1 (MCP server adapter) | MERGE-INTO #45 | Identical scope to #45; recommend closing the older one (#35) in favour of #45. Master roadmap PH-16 covers both server and client adapters. |
| 36 | Browser-Based UI Testing Suite | 4 | PH-12 slice 12.1 (CI) | CONVERT | Generated CI workflow gets an optional Playwright matrix when the project's tech stack is web-shaped. Not in the core CLI. |
| 37 | Automated Test-on-Generation Loop | 4 | PH-03 slice 3.6 (verifier integration) + PH-13 (self-heal) | CONVERT | The Auditor agent in the forge cycle already plays this role; the loop closes when the Verifier blocks on a failing test (PH-03 slice 3.6). |
| 38 | AI-Powered Code Review Bot | 4 | PH-03 (forge audit role) + PH-12 (CI) | CONVERT | Two halves: in-CLI review via the Auditor agent (PH-03), and PR-side via the GitHub Actions workflow (PH-12). |
| 39 | Repository Vulnerability & Secret Scanner | 5 | PH-11 slice 11.3 (secret scanner) + 11.5 (dangerous patterns) | MERGE-INTO #32 | Same scope as #32 (or vice versa). Recommend keeping #32 because it adds the "auto-fix" half. |
| 40 | Automated Policy & Rule Enforcement | 5 | PH-14 slice 14.2 (pre-command policy check) | MERGE-INTO #30 | Generation (#30) and enforcement (#40) split is real but tightly coupled in PH-14. Recommend keeping #30 (broader title) and closing #40 with a "tracked in #30" comment. |
| 41 | Zero-Knowledge Secret Management | 5 | PH-11 slice 11.2 (redaction engine) | CONVERT | Default-deny patterns + redaction in `provider_calls.jsonl` already exist; "zero-knowledge encryption" extends that to local-key encryption of `.env` access. |
| 42 | Automated Docker Containerization | 6 | PH-12 slice 12.2 (`mythic-vibe docker scaffold`) | CONVERT | Direct mapping. |
| 43 | One-Click Infrastructure-as-Code | 6 | PH-12 slice 12.2 + 12.3 | KEEP-OPEN | Keep open as the umbrella issue; close #33 into it. |
| 44 | Automated Changelog & Release Notes | 6 | PH-12 slice 12.3 (`mythic-vibe release`) | PARTIAL-SHIPPED | `scripts/check_changelog.py` and `CHANGELOG.md` already exist. The remaining work is automated entry generation from Conventional Commits. |
| 45 | Model Context Protocol (MCP) Integration | 7 | PH-16 slice 16.1 + 16.2 | KEEP-OPEN | Master umbrella for MCP work. Close #35 into it. |
| 46 | Multi-Agent "Squad" Configuration | 7 | PH-03 (forge) + PH-10 slice 10.3 (plugin extension points) | CONVERT | "Squad" is a plugin-defined preset over the six Mythic roles (`SquadPlugin` extension point in PH-10). |
| 47 | Mobile/Telegram Command Interface | 7 | PH-17 slice 17.2 (mobile) + 17.4 (chat bridge) | MERGE-INTO #34 | #34 is broader (Web + Mobile + Telegram). Recommend keeping #34 and closing #47 with a "tracked in #34" comment. |

## Duplicate clusters

Five duplicate clusters identified. Recommended consolidation:

| Cluster | Members | Keep | Close into |
|---|---|---|---|
| Cloud deployment / IaC | #33, #43 | #43 | #33 → #43 |
| MCP integration | #35, #45 | #45 | #35 → #45 |
| Multi-platform / mobile | #34, #47 | #34 | #47 → #34 |
| Vulnerability scan/fix | #32, #39 | #32 | #39 → #32 |
| Policy gen/enforce | #30, #40 | #30 | #40 → #30 |

If Volmarr accepts these consolidations, **5 of the 21 issues** can
be closed as duplicates, leaving 16 active.

## Already-shipped fragments worth flagging

| Issue | Already shipped | Implication |
|---|---|---|
| #29 Context Anchoring | `init` writes `MYTHIC_ENGINEERING.md`, `docs/INDEX.md`, and the docs scaffold | The remaining work is multi-tool variants (CLAUDE.md / AGENTS.md / `.cursorrules`). Recommend updating the issue body to reflect this. |
| #44 Changelog automation | `CHANGELOG.md` is in active use; `scripts/check_changelog.py` enforces the unreleased-section discipline in CI | Remaining work is auto-generation from commit history. Recommend updating the issue body. |
| #41 Secret management | `mythic/ai/provider_calls.jsonl` redaction is live; `--dry-run-first` provider behaviour is enforced | "Zero-knowledge encryption" of `.env` is the remaining new work. Recommend updating the issue body. |

## Phase 1-aligned issues (none)

None of the 21 open issues map to Phase 1 (Foundation Audit & Quality
Sweep). The audit findings in `PHASE1_RUNTIME_AUDIT.md` are a separate
quality-internal track. This is fine — the audit is internal hygiene,
the issues are user-visible features.

## Recommended slice 1.3 / 1.4 actions for Volmarr

When Volmarr is ready to act on this triage:

1. **(Optional) Close the 5 duplicates** with the comments suggested
   above. Net result: 16 active issues.
2. **(Optional) Update the bodies of #29, #41, #44** to mark
   already-shipped fragments and reduce scope to the remaining work.
3. **(No action required)** — the master roadmap already addresses
   all 21 issues across phases PH-03, PH-05, PH-10, PH-11, PH-12,
   PH-13, PH-14, PH-15, PH-16, PH-17. Issues do not need to be
   converted to roadmap entries; the roadmap is the plan, the issues
   are the public tracker.

## Open-issue → master-roadmap-phase distribution

| Master phase | Issues landed |
|---|---|
| PH-03 Multi-Agent Forge | #27, #37, #38, #46 |
| PH-05 Knowledge Graph | #27, #28 |
| PH-10 Plugin Ecosystem | #29, #46 |
| PH-11 Security/Sandbox | #32, #39, #41 |
| PH-12 CI/CD & Deployment | #31, #33, #36, #38, #42, #43, #44 |
| PH-13 Drift / Self-Healing | #32 |
| PH-14 Policy Engine | #30, #40 |
| PH-15 Conversation Memory | #29 |
| PH-16 MCP / ACP / OTEL | #35, #45 |
| PH-17 Multi-Surface Access | #34, #47 |

Phases PH-02 (Slash Commands), PH-04 (TUI v2), PH-06 (Local LLM),
PH-07 (Voice), PH-08 (Provider Routing), PH-09 (Islands), PH-18
(Robustness), PH-19 (Distribution), PH-20 (Launch) have no
issue-tracker entries today — they are roadmap-original work.

## What this slice did not do

- Did not post any comments on GitHub.
- Did not close, label, or otherwise modify any issue.
- Did not assign issues to milestones (Volmarr's call).
- Did not draft commit-style or PR-style fix proposals — those land
  in the slices that pick the issues up (PH-03 forge, PH-11 security,
  PH-12 CI/CD, PH-14 policy, PH-16 MCP, PH-17 multi-surface).

## Slice 1.2 close-out

Slice 1.2 is complete. Findings:

- 21 open issues, 0 closed, all from Volmarr 2026-04-25.
- 5 duplicate clusters identified.
- 3 issues with already-shipped fragments (#29, #41, #44).
- All 21 issues route cleanly to master-roadmap phases (PH-03 through
  PH-17). No issue is orphaned.
- Recommended Volmarr-actions are explicitly optional; the master
  roadmap fully owns the implementation regardless of issue-tracker
  state.

Slice 1.3 (quick-fix sweep) follows. It is the first slice in this
roadmap that lands a code change, scoped to the seven info-severity
additive findings from `PHASE1_RUNTIME_AUDIT.md`: F-006, F-007,
F-010, F-014, F-017, F-018, F-019.
