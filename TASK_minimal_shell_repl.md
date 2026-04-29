# TASK — V2 Phase 3 Slice 1: Minimal `mythic-vibe shell` REPL

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `f282714` — slash-commands hook + slash list consumer.

---

## Why this slice

V2 Phase 3 (TUI) is a multi-slice arc. Before committing to a TUI library, ship a minimal interactive surface that uses the primitives we already have (slash-commands catalog, output_guard, timings) and establishes the REPL contract a future Textual TUI will wrap or replace.

The slash-commands catalog and `slash list` machinery shipped yesterday are the natural foundation. This slice gives them their first interactive consumer.

## Goal

Land:

1. `mythic_vibe_cli/repl.py` — the REPL loop
2. `cmd_shell(args)` in `mythic_vibe_cli/commands.py` + dispatch wiring
3. `shell` sub-parser in `mythic_vibe_cli/app.py`
4. Tests: EOF exit, `/quit` exit, `/help`, empty line re-prompt, unknown command graceful error, real command dispatch round-trip
5. Update `docs/plugins.md` + `docs/runtime.md` cross-links pointing at the new shell as the slash-catalog consumer
6. CHANGELOG + DEVLOG

## Loop contract

```text
mythic-vibe shell starts.
Prints a banner (one line).
Repeats:
  1. Print prompt: "mythic-vibe> "
  2. Read one line from stdin via input()
  3. Strip whitespace.
     - Empty line → re-prompt (continue)
     - EOF (Ctrl+D) → exit with SUCCESS
     - "/quit" or "/exit" → exit with SUCCESS
     - "/help" → print BUILTIN_SLASH_COMMANDS catalog inline
     - Anything else (with or without leading "/") → strip leading "/", split via shlex, call app.main(parts), print exit code if non-zero
  4. KeyboardInterrupt (Ctrl+C) caught → print a brief message, re-prompt
  5. Any other exception caught → print "Command failed: <error>", re-prompt (don't crash the REPL)
```

## Out of scope

- readline/history (defer; if added later, becomes a follow-on slice)
- Tab-completion
- Multi-line input
- Textual dependency or any TUI rendering library
- Plugin slash command dispatch beyond just listing them via /help (full slash dispatch by plugin-contributed name = follow-on slice)
- Async / streaming output

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/repl.py` | NEW — the REPL loop (`run_shell()`) |
| `mythic_vibe_cli/commands.py` | Add `cmd_shell` and register handler |
| `mythic_vibe_cli/app.py` | Add `shell` sub-parser |
| `tests/test_cli_kernel.py` | Update command-registry expected set; add 6 shell integration tests |
| `tests/test_repl.py` | NEW — unit tests on the REPL loop in isolation |
| `docs/plugins.md` | Cross-link the shell as the slash catalog's interactive consumer |
| `docs/runtime.md` | Update §6 to mention shell as a consumer |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Implement `repl.py:run_shell(stdin, stdout, stderr)` (parameterized for tests)
- [ ] Add `cmd_shell` + dispatch
- [ ] Add `shell` sub-parser
- [ ] Update command-registry test expected set
- [ ] Unit tests (test_repl.py): EOF exits, /quit, /help, empty line, unknown command, real command dispatch
- [ ] Integration test (test_cli_kernel.py): `app.main(["shell"])` with piped stdin works end-to-end
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Doc cross-links updated
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. The REPL function should accept stdin/stdout/stderr file objects as parameters so tests can inject `io.StringIO` without monkey-patching `sys.stdin`.
3. Use `shlex.split()` for the command line, not `.split()` — handles quoted arguments correctly.
4. `app.main()` returns an int exit code. The REPL prints it on non-zero so the user sees command failures, but doesn't crash on them.
5. Recursive `mythic-vibe shell` inside the shell would be silly; it's allowed but not blocked. Consider gating later.
6. The slash dispatcher is `app.main` re-entrance — slash commands map directly to existing CLI sub-commands. Plugin-contributed slash commands are listed by `/help` but not dispatched in this slice (their dispatch needs design work — defer).
