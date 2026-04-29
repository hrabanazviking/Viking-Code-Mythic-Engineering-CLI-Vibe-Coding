# TASK — Wire `before_verify` / `after_verify` Emitters

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `078226a` — packet hook emitters.

---

## Why this slice

Three hook pairs remain unwired: verify, reflect, and the reflect lifecycle. This slice handles the verify pair. Same dispatcher template as `cmd_scan` and `cmd_packet_create`. Single command site, no dry-run path, so emission timing is straightforward.

## Goal

Wrap `cmd_verify` with a `PluginHookDispatcher` block. Emit `before_verify` at the top with the selected check flags, emit `after_verify` after the verification artifact has been written. Payload uses small stable keys; large lists (warnings, errors, command outputs) stay out of the payload — plugins that need them can read the artifact at `artifact_path`.

## Payload contract

```text
before_verify:
  {
    "path": "<absolute project root>",
    "selected": {"commands": bool, "changed_files": bool, "docs": bool, "invariants": bool},
  }

after_verify:
  {
    "path": "<absolute project root>",
    "result": "pass" | "fail" | "blocked",
    "level": "none" | "smoke" | "unit" | "integration",
    "verification_id": "<vfy-...>",
    "artifact_path": "<absolute path to the verification artifact>",
    "errors_count": int,
    "warnings_count": int,
    "blocked_count": int,
  }
```

## Out of scope

- `before_reflect`/`after_reflect` (separate slice)
- Refactoring verify internals
- Adding payload fields beyond the scalar summary

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/commands.py` | Wrap `cmd_verify` with dispatcher, emit before/after |
| `tests/test_cli_kernel.py` | Add 2-3 integration tests |
| `docs/COMMAND_CONTRACTS.md` | Add verify entry to plugin-dispatch section |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Wrap `cmd_verify` with dispatcher block
- [ ] Integration tests (≥2 cases — passing path + failing path)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Docs updated
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. `cmd_verify` has no dry-run flag — always emits when the command runs.
3. Fire `before_verify` BEFORE any check work begins.
4. Fire `after_verify` AFTER `write_verification_artifact` returns, BEFORE the JSON/text output.
5. Keep payloads small; no nested arrays of warnings/errors.
