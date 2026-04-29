# TASK — Workflow Identifiers on Plans and Packets

**Opened:** 2026-04-29
**Owner:** Runa (Forge Worker role)
**Stage:** 16 (V2 Roadmap Phase 2 — The 6-Agent Engine)
**Continuity from:** 2026-04-29 DEVLOG entry "Stage 16 Workflow Packet Listing"

---

## Continuity Quote

From the prior session's DEVLOG:

> *"The next slice can attach workflow identifiers to plan and packet metadata, so packet readiness can be traced by workflow ID instead of exact task text."*

This task delivers that slice.

---

## Why

`_workflow_packet_status()` currently matches plan steps to stored packets by exact text on `(role, phase, task, audience, output_format)`. That match is brittle:

- If a user edits the human-readable task text on a saved plan, packet readiness silently breaks
- Two unrelated plans with identical task text could cross-match
- Re-running a task months later finds stale packets

A `workflow_id` stamped on the plan and every packet generated from it gives a stable identity. Text matching stays as a legacy/fallback path.

## Strictly Additive Constraint

Per Mythic Engineering law: no subtraction. New fields are optional. Legacy plans/packets without IDs continue to load and match by text. The CLI surface adds zero breaking changes.

## Scope

### In scope

- New optional `workflow_id` and `workflow_step_id` on plans, packet requests, packet records, packet `.meta.json` payloads
- Deterministic-but-unique workflow_id generation (`WF-<UTCcompact>-<sha8(task+created_at)>`)
- Update `_workflow_packet_status` to prefer ID-based matching, fall back to text-based matching when either side lacks an ID
- Surface workflow_id in `workflow plan` / `workflow packets` / `workflow run` JSON and human output
- Tests for: id generation determinism (within a single build), id round-trip via `from_dict`, packet stamping on `--packets`, ID-based readiness match, legacy-fallback text match
- DEVLOG, CHANGELOG, COMMAND_CONTRACTS, api.md updates

### Out of scope

- Renaming or migrating existing packet metadata files
- Cross-machine workflow synchronization
- Workflow id assignment for non-workflow packets (`packet create` outside `workflow plan --packets`)
- Stage 15 method excerpt selector (separate task)
- V2 Phase 3+ (TUI / Ollama / WYRD)

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/workflow_engine.py` | Add `workflow_id` to `WorkflowPlan`; add `workflow_id`/`step_id` to `WorkflowStep.packet_request()`; serialize/deserialize via `to_dict`/`from_dict`; deterministic id generation in `build_plan` |
| `mythic_vibe_cli/codex_bridge.py` | Add `workflow_id`/`workflow_step_id` to `CodexPacketRequest` and `PacketRecord`; persist in `.meta.json` when set; load back in `list_packets`/`load_packet_record` |
| `mythic_vibe_cli/commands.py` | `_workflow_packet_status` ID-first match with text fallback; surface `workflow_id` in `cmd_workflow_plan`, `cmd_workflow_packets`, `cmd_workflow_run` JSON+human output |
| `tests/test_workflow_engine.py` | Plan id generation + round-trip + packet_request propagation |
| `tests/test_cli_kernel.py` | `workflow plan --packets` stamps id; `workflow packets` matches by id; legacy fallback still works |
| `docs/COMMAND_CONTRACTS.md` | Note the workflow_id field on plan/packet outputs |
| `docs/api.md` | Same |
| `CHANGELOG.md` | Add Unreleased entries |
| `DEVLOG.md` | New 2026-04-29 entry with Continuity thread |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed to development
- [x] Code change: `workflow_engine.py`
- [x] Code change: `codex_bridge.py`
- [x] Code change: `commands.py`
- [x] Tests added (4 engine + 3 CLI-kernel)
- [x] `pytest` green — `93 passed, 14 subtests passed`
- [x] `ruff check mythic_vibe_cli tests` green
- [x] `mypy mythic_vibe_cli` green — 51 source files
- [x] Smoke: `workflow plan --packets --json` -> `workflow_id: WF-20260429074552-75add827` stamped on packet
- [x] Smoke: `workflow packets --json` -> `match_strategy: "id"` on saved plan
- [x] Smoke: stripped IDs -> `match_strategy: "text"` legacy fallback intact
- [x] Docs (COMMAND_CONTRACTS, api.md) updated
- [x] CHANGELOG Unreleased entries added
- [x] DEVLOG entry written
- [ ] Memory `project_mythic_engineering_cli_status.md` updated with new HEAD
- [ ] Final commit + push

## Resume Instructions for Fresh Session

1. Read this file for full task context.
2. Check off boxes above to see remaining work.
3. The active runtime is at `mythic_vibe_cli/`; tests at `tests/`.
4. Run the test suite first to confirm baseline (`pytest -q`).
5. ID format reference: `WF-<UTC compact>-<sha8 of task+created_at>`. Always optional. Legacy plans without one fall back to existing text-based matching.
6. Verification commands: `pytest -q`, `ruff check mythic_vibe_cli tests`, `mypy mythic_vibe_cli`.
7. Final step: write a DEVLOG entry with a Continuity thread for the next slice.

## Continuity Thread (For Next Slice)

After this lands, the natural next slice is:

> *"Workflow-scoped packet listing — a `packet list --workflow <id>` filter so users can show only the packets belonging to one workflow run."*

That uses the IDs added here without expanding the runner surface.
