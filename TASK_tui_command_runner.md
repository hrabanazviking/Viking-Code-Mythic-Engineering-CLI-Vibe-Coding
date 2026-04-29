# TASK — TUI Slice 3: Command Runner with Live Elapsed Time

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `3af5eed` — slash-commands picker screen.

---

## Why this slice

The picker shows commands but cannot run them. This slice gives the TUI a `RunningCommandScreen` that actually dispatches a selected command in a subprocess, displays elapsed time live, and shows the final exit code with a tail of output when the process completes.

This is the third of three TUI slices Volmarr requested. It closes the trio: status panel + recent events feed → picker → runner.

## Goal

Land:

1. `mythic_vibe_cli/tui/runner.py` — `RunningCommandScreen` that:
   - Spawns the command via `subprocess.Popen` with `stdout=PIPE / stderr=PIPE`
   - Refreshes elapsed time on a Textual interval (every 0.2s)
   - Polls process completion at the same interval
   - Displays the final exit code + a tail of stdout/stderr when the process exits
2. `RunningCommandScreen` is reachable from `CommandPreviewScreen` via an `Enter` / `r` ("Run") binding when the entry is a *builtin* slash command
3. Plugin-contributed commands display "(plugin dispatch not yet implemented)" instead — that contract belongs to a future slice
4. Tests: pure-data tests on the command-builder helper, headless TUI tests on the runner screen lifecycle
5. Cross-platform: subprocess via stdlib only; no signal handling that's Unix-specific; no `os.name` branches

## Interaction model

```
CommandPreviewScreen (entry is builtin)
  ↓  press "r" or "Enter"
RunningCommandScreen [shows: command, elapsed, output tail; updates every 0.2s]
  ↓  process exits
RunningCommandScreen [shows: exit code, full output tail, "Esc to return"]
  ↓  Esc
CommandPreviewScreen (or pop further back)
```

For non-builtin entries (plugin/extension/skill/prompt), the preview screen shows a notice that this slice doesn't dispatch them yet.

## Out of scope

- Plugin-contributed slash command dispatch (deferred — design needs a plugin-side `run_slash_command(name, args)` hook)
- Killing a running command from the TUI (a kill key would be useful but adds scope; defer)
- Streaming stdout/stderr line-by-line as the command runs (this slice polls; streaming via `asyncio.create_subprocess_exec` is a follow-on)
- Argument prompting (this slice runs commands with no arguments — picker entries don't carry argument schemas yet)

## Cross-platform compliance

- `subprocess.Popen` works uniformly on Windows / macOS / Linux
- We use `proc.poll()` + `proc.communicate(timeout=0.001)` polling (no Unix-only signal handlers)
- Textual handles all terminal-specific rendering
- No platform branches in runner code

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/tui/runner.py` | NEW — `RunningCommandScreen`, `command_for_builtin(name)` |
| `mythic_vibe_cli/tui/__init__.py` | Re-export via lazy `__getattr__` |
| `mythic_vibe_cli/tui/picker.py` | `CommandPreviewScreen` gains `r`/Enter binding to push runner for builtins; non-builtin shows notice |
| `tests/test_tui.py` | New tests: command_for_builtin shape, runner screen lifecycle (run a fast command, see exit code) |
| `docs/runtime.md` / `docs/COMMAND_CONTRACTS.md` | Note the new screen |
| `CHANGELOG.md` + `DEVLOG.md` |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Implement `RunningCommandScreen` + `command_for_builtin`
- [ ] Wire preview → runner via `r`/Enter binding
- [ ] Plugin-entry "not yet" notice on preview
- [ ] Tests
- [ ] Gates green
- [ ] Docs + CHANGELOG + DEVLOG
- [ ] Memory + push

## Resume Instructions

1. Read this file for full task scope.
2. Use `sys.executable -m mythic_vibe_cli <name>` as the command form so the runner re-enters the same Python interpreter the TUI is running in (avoids PATH/venv issues across platforms).
3. The runner's elapsed-time tick uses `set_interval(0.2)` — same Textual primitive as the status auto-refresh.
4. To headless-test the lifecycle, pick a builtin that exits fast (e.g., `status`) and assert that exit code 0 appears in the rendered output after `pilot.pause(...)`.
