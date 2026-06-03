---
title: "PH-15 Sub-slice — Provider-call Auto-recording (close-out)"
phase: PH-15
subslice: 15.1.1
created: 2026-04-29
created_by: Runa Gridweaver Freyjasdottir
branch: development
head_at_open: 8853249
head_at_close: 8b923fc
test_baseline_open: 874 + 14 subtests
test_baseline_close: 886 + 14 subtests
ruff_status: clean
mypy_status: clean
status: complete
---

# PH-15 sub-slice — Provider-call auto-recording (close-out)

The PH-15 finale (commit `8853249`) shipped the conversation log
data layer (slice 15.1) but explicitly deferred wiring `record_turn`
into the AI provider commands. This sub-slice closes that gap.

## What landed

### CLI surface

| Subcommand | New flag | Behaviour |
|---|---|---|
| `ai run` | `--conversation-id CV-XXXXXX` | optional id; auto-generated if absent |
| `ai run` | `--no-record` | opt out of conversation logging |
| `ai ingest-response` | `--conversation-id CV-XXXXXX` | same as above |
| `ai ingest-response` | `--no-record` | same as above |

### `cmd_ai_run` recording rules

| Condition | Records? |
|---|---|
| `--no-record` set | No |
| `--dry-run` set | No |
| Provider response `dry_run=True` (e.g. shipped CopyPasteProvider / LocalProvider) | No |
| Real provider response | Yes — user turn + assistant turn |

The shipped CopyPaste / Local providers always self-report
`dry_run=True` because they wrap prompts for manual paste and don't
actually call an AI. The recording correctly skips for these — no
real conversation has happened. Real recording fires only when an
API-backed provider (Anthropic / OpenAI / Gemini / OpenRouter)
returns `dry_run=False`, or when a test mocks the response.

### `cmd_ai_ingest_response` recording rules

`ingest-response` is the manual paste-back flow — the operator
pasted the packet into a chat UI by hand, then runs `mythic-vibe ai
ingest-response --response "..."` to record what came back. The
matching user turn lives outside Mythic, so the sub-slice records
only the assistant side under the resolved conversation_id.

### JSON output additions

```jsonc
// ai run
{ ..., "conversation_id": "CV-ABCDEF", "recorded": true }

// ai ingest-response (under .payload)
{ "..., "conversation_id": "CV-ABCDEF", "recorded": true, ... }
```

### Robustness

Any `record_turn` failure (disk full, permission denied, etc.)
quarantines to `recorded=False` — the CLI never crashes on a log-
write error. The original `ai run` / `ai ingest-response`
behaviour is byte-identical when `--no-record` is set, so callers
that want the exact pre-sub-slice flow can opt out.

## Numbers

| Metric | Open | Close |
|---|---|---|
| Test count | 874 | **886** (+12) |
| Source files | 86 | 86 |
| Slash builtins | 57 | 57 |
| Argparse handlers | 55 | 55 |
| Ruff / mypy | clean | clean |

## Tests added (12)

`tests/test_ai_conversation_recording.py`:

- `AiRecordingArgparseTests` (3): both subcommands accept the new
  flags with sensible defaults.
- `AiRunRecordingTests` (5):
  - Real call (CopyPasteProvider.run mocked to dry_run=False)
    records two turns under supplied id.
  - Auto-generated id when none supplied.
  - `--no-record` skips even on a real call.
  - `--dry-run` skips even with explicit id.
  - Unmocked provider (`dry_run=True`) skips correctly.
- `AiIngestRecordingTests` (3): single assistant turn; auto-id;
  `--no-record` skip.
- `MultiTurnRecordingTests` (1): two `ai run` calls under the same
  id produce four turns (two user + two assistant) so the same
  conversation can grow across invocations.

The mocking pattern (patch `CopyPasteProvider.run` with a
non-dry-run `ProviderResponse`) is the canonical way to exercise
the recording path without an API key.

## Master-roadmap PH-15 gate

The Phase 15 finale flagged this as the only PH-15 gate that was
**partial**:

> Persist provider conversations: ✅ data layer ready
> (`record_turn`); provider-call hooks deferred

After this sub-slice, the gate is fully met. Operators who run
real-API providers automatically build a structured conversation
log they can later show / list / compact / rehydrate via
`mythic-vibe memory ...`.

## What this sub-slice deliberately did not do

- **Did not change provider behaviour.** Providers still emit
  `ProviderResponse(dry_run=True/False)` exactly as before; the
  recording layer reads that flag and decides whether to log.
- **Did not auto-flag a conversation as "ongoing".** Each
  invocation of `ai run` is independent unless the operator
  passes the same `--conversation-id`. A future "current
  conversation" slot (similar to current handoff) is its own
  slice.
- **Did not record `ai test`.** That subcommand is the estimation
  / dry-run path — same reasoning as why we skip when
  response.dry_run=True. If a future test variant becomes a real
  call, recording can be added under the same flags.
- **Did not migrate metadata-only ingestion to a single turn.**
  We record only the assistant side because that's what
  `ingest-response` carries. The matching user turn (the operator's
  manual paste) belongs to whatever flow recorded the packet — if
  any.
- **Did not add a TUI surface.** `mythic-vibe memory list` /
  `show` cover the surface CLI-side; a future slice can mirror it
  in the TUI.

## How to verify

```bash
$ mythic-vibe memory list
Memory: no conversations recorded yet.

# Real-API run (Anthropic / OpenAI etc) records automatically:
$ mythic-vibe ai run --provider anthropic --packet pkt.txt
  ... { "conversation_id": "CV-XXXXXX", "recorded": true, ... }

$ mythic-vibe memory list
Memory: 1 conversation(s).
  CV-XXXXXX  turns=2  updated=...  provider=anthropic

# Reuse the id to grow the same conversation:
$ mythic-vibe ai run --provider anthropic --packet next.txt \
                    --conversation-id CV-XXXXXX
  ... { "recorded": true, ... }

$ mythic-vibe memory show --id CV-XXXXXX
# Full transcript including all four turns.

# Skip recording when needed:
$ mythic-vibe ai run --provider anthropic --packet pkt.txt --no-record
  ... { "conversation_id": "", "recorded": false, ... }
```
