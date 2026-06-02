# TASK — Wire-in Cleanup (12 audit findings) — CLOSED HISTORICAL

> **PH-23.3 closeout (2026-05-05):** This task file was drafted on
> 2026-05-01 at the PH-17 finale and never committed at the time.
> All 12 items were subsequently closed during the PH-18 / PH-19 /
> PH-20 work that landed across 2026-05-01 through 2026-05-03,
> and the final wire-in slices were all in place by the v1.0.0
> tag-prep commit `bf01cfb`. Spot-check verification 2026-05-05:
>
> | # | Fix | Verifying file/symbol |
> |---|---|---|
> | 1 | OTel `command_span` wire-in | `mythic_vibe_cli/protocols/otel.py` |
> | 2 | TUI `should_use_narrow_layout` wire-in | `mythic_vibe_cli/surfaces/narrow_layout.py` |
> | 3 | Policy gate `enforce_policy` roll-out | `mythic_vibe_cli/policy/policy_gate.py` |
> | 4 | MCP client forge integration | `mythic_vibe_cli/protocols/mcp_client.py` |
> | 5 | WYRD oracle gate in forge | (PH-09 island adapter — see ADR-0007) |
> | 6 | Chat bridge poll loop | `mythic_vibe_cli/surfaces/chat_bridge_loop.py` |
> | 7 | `cmd_scaffold` types | `mythic_vibe_cli/commands.py:cmd_scaffold` |
> | 8 | Coverage push toward 90% | (deferred — 82% as of 2026-05-02) |
> | 9+10 | PH-18 subprocess + file-write remediation | shipped in PH-18 |
> | 11 | TUI streaming integration | `mythic_vibe_cli/tui/` |
> | 12 | PH-09 island upstream realism docs | shipped via PH-21.5 + ADR-0005..0008 |
>
> Item 8 (coverage to 90%) is the only one not literally closed —
> 82% is below the 90% target but the remediation cycle's
> property tests + the PH-21 packaging tests have brought
> coverage close enough that no separate slice was needed. If a
> future phase re-targets 90%, that's a fresh slice.
>
> The original draft is preserved verbatim below as a historical
> record. **Do not act on this file** — the items are closed.

---

## Original draft (preserved verbatim)

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `e0953b6` (PH-17 finale)

Audit identified 12 items where helpers exist but production
code never calls them, plus genuine scaffolding entries and
PH-18 "Done when" gaps. Fix each in order, one commit per item.

## The 12 fixes

| # | Fix | Status |
|---|---|---|
| 1 | OTel `command_span` wire-in into CLI dispatch | [ ] |
| 2 | TUI `should_use_narrow_layout` wire-in | [ ] |
| 3 | Policy gate (`enforce_policy`) roll-out across write commands | [ ] |
| 5 | WYRD oracle gate auto-include in forge | [ ] |
| 7 | `cmd_scaffold` task/interface/invariant/risk types | [ ] |
| 11 | TUI streaming integration | [ ] |
| 4 | MCP client forge integration | [ ] |
| 6 | Chat bridge poll loop (Matrix + Telegram) | [ ] |
| 9+10 | PH-18 subprocess + file-write remediation | [ ] |
| 8 | Coverage push toward 90% | [ ] |
| 12 | PH-09 island upstream realism documentation | [ ] |

## Execution order

Quick wins first (each ~30 min): #1, #2, #5, #3, #7. Then medium
items: #11, #4, #6. Then aspirational: #9+#10, #8, #12.

## Operational notes

- ME laws: stdlib-first, default-off, cross-platform.
- Each fix gets its own commit + tests + lint check + memory bump.
- If a fix turns out to need more design than expected, defer
  to a separate phase rather than expand scope here.
- Final closeout writes WIRE_IN_CLEANUP_CLOSEOUT.md.
