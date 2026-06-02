---
title: "PH-15 Sub-slice — Provider-call auto-recording wire-up"
phase: PH-15
subslice: 15.1.1
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 8853249
status: in_progress
---

# PH-15 follow-up — auto-record provider calls

The PH-15 finale (commit `8853249`) shipped the conversation log
data layer (slice 15.1) but deferred wiring `record_turn` into the
AI provider commands. This sub-slice closes that gap.

## Plan

1. Extend argparse for `ai run` and `ai ingest-response`:
   - `--conversation-id` (optional) — operator-supplied
     `CV-XXXXXX`. When absent, a fresh id is generated.
   - `--no-record` — opt out of conversation logging entirely.

2. `cmd_ai_run`:
   - When `--no-record` is set OR `--dry-run` is set, skip
     recording (dry-runs aren't real conversations).
   - Otherwise: record the packet text as a `user` turn and the
     provider's response content as an `assistant` turn.
   - Surface the resolved `conversation_id` in the JSON payload so
     the operator knows where the log landed.

3. `cmd_ai_ingest_response`:
   - When `--no-record` is set, skip recording.
   - Otherwise: record the response text as an `assistant` turn
     under the supplied / generated id.
   - Surface `conversation_id` in JSON output.

4. Tests:
   - `cmd_ai_run` happy path with `copy-paste` provider records two
     turns; supplied id reused; absent id auto-generated.
   - `--dry-run` skips recording.
   - `--no-record` skips recording even on real calls.
   - `cmd_ai_ingest_response` records single assistant turn.
   - Argparse accepts the new flags.

## Definition of done

- Tests green; existing 874 stay green.
- Ruff + mypy clean.
- Single-commit close-out under `PH15_PROVIDER_RECORDING_CLOSEOUT.md`.
- Tracker + memory updated.
- Pushed.
