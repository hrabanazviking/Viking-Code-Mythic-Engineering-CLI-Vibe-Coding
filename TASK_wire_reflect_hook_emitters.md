# TASK — Wire `before_reflect` / `after_reflect` Emitters (Closeout)

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `85ccc1b` — verify hook emitters.

---

## Why this slice

Two declared hooks remain — `before_reflect` and `after_reflect`. Wiring them into `cmd_reflect` closes out the full set of eight `PLUGIN_HOOKS`. Once this slice lands, every name declared in `mythic_vibe_cli/plugins/api.py:PLUGIN_HOOKS` has a real emitter. The plugin layer becomes fully load-bearing — every life-cycle moment in the CLI announces itself to subscribed plugins.

## Goal

Bracket `cmd_reflect`'s real-work path with `PluginHookDispatcher`. Emit `before_reflect` with the user's intent, `after_reflect` with the resulting handoff record's IDs and paths. Dry-run path skips emission, matching the pattern across the other dispatcher sites.

## Payload contract

```text
before_reflect:
  {
    "path": "<absolute project root>",
    "summary": "<args.summary or args.objective or None>",
    "next_step": "<args.next_step or None>",
    "note": "<args.note or None>",
  }

after_reflect:
  before_reflect payload + {
    "handoff_id": "<handoff record id>",
    "json_path": "<absolute json path>",
    "markdown_path": "<absolute markdown path>",
    "next_recommended_action": "<first next-steps entry, or sentinel>",
  }
```

## Out of scope

- Refactoring `cmd_reflect`'s handoff internals
- Adding hook emission to dry-run paths
- Altering `cmd_resume` or other handoff commands

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/commands.py` | Wrap `cmd_reflect` real-work path with dispatcher |
| `tests/test_cli_kernel.py` | Add 2 integration tests (real path emits, dry-run does not) |
| `docs/COMMAND_CONTRACTS.md` | Add reflect entry; promote summary line to "all eight hooks now emit" |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry — closeout entry for the dispatcher emitter set |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Wrap `cmd_reflect` real-work path with dispatcher
- [ ] Integration tests (≥2 cases — real path emits both; dry-run emits nothing)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Docs updated; promote summary line
- [ ] CHANGELOG entry
- [ ] DEVLOG entry — closeout
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Use `with PluginHookDispatcher(root) as dispatcher:` because the real-work path has only one return point — context manager is clean here.
3. After this lands, the plugin emitter set is closed. Memory and DEVLOG should record the milestone.
