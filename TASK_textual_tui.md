# TASK — V2 Phase 3 Slice 2: Textual TUI `mythic-vibe tui`

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor:** `18d09e6` — minimal shell REPL.

---

## Why this slice

The shell REPL is interactive but text-only. V2 Phase 3 calls for "a professional terminal interface" — Textual delivers that with rich rendering, keybindings, panels, and auto-refresh. This slice adds a minimal Textual TUI that shows project state with auto-refresh.

## Cross-platform / open-source compliance

- **Textual** — MIT-licensed, pure Python, supports Windows / macOS / Linux. Verified against the durable cross-platform requirement Volmarr stated 2026-04-29.
- No platform-conditional code paths. No native dependencies. No proprietary services.
- Optional dependency under `[tui]` extra so users who don't want it don't pay for it.

## Goal

Land:

1. `mythic_vibe_cli/tui/__init__.py` — package marker
2. `mythic_vibe_cli/tui/app.py` — Textual `App` subclass + Screen + `build_status_data(root)` pure helper
3. `cmd_tui(args)` in `commands.py` — late-imports the TUI module so missing-`textual` doesn't break the rest of the CLI
4. `tui` sub-parser in `app.py`
5. `pyproject.toml` — `[tui]` extra adds `textual>=0.80`; dev group includes textual
6. Tests:
   - `build_status_data(root)` is pure and tested without Textual
   - Skip-if-missing test that confirms Textual is importable
   - `App.run_test()` headless test that confirms the screen renders and the quit binding works
7. `docs/runtime.md` mention; `docs/COMMAND_CONTRACTS.md` and `docs/api.md` cross-link
8. CHANGELOG + DEVLOG

## TUI shape (first slice scope)

**Single screen, four panels:**

```
┌── Mythic Vibe TUI ─────────────────────────────────────────┐
│                                                            │
│  ╔══ Status ════════════╗ ╔══ Verification ═════════════╗  │
│  ║ Path:        ...     ║ ║ Last result:   pass         ║  │
│  ║ Phase:       intent  ║ ║ Last ID:       vfy-...      ║  │
│  ║ Active task: TASK-A  ║ ║ Level:         unit         ║  │
│  ╚══════════════════════╝ ╚═════════════════════════════╝  │
│                                                            │
│  ╔══ Latest Handoff ════╗ ╔══ Plugins ══════════════════╗  │
│  ║ ID:          hd-...  ║ ║ 2 enabled, 1 disabled       ║  │
│  ║ Created:     ...     ║ ║                             ║  │
│  ║ Next step:   ...     ║ ║                             ║  │
│  ╚══════════════════════╝ ╚═════════════════════════════╝  │
│                                                            │
│  Last refresh: 2026-04-29 12:00:00 UTC                     │
│  q quit · r refresh · ? help                               │
└────────────────────────────────────────────────────────────┘
```

**Auto-refresh:** every 2 seconds, re-reads project state and updates the panels.

**Keybindings:**
- `q` / `ctrl+c` → quit
- `r` → manual refresh
- `?` → show short help (just a dialog of the keys for now)

## Out of scope

- Multi-screen navigation
- Editing actions (read-only TUI in this slice)
- Real-time log streaming from running commands
- Progress bars for long tasks (deferred — V2 roadmap mentions this for a later slice)
- Rich animation / transitions
- Theme customization
- Mouse interaction

## Files to Touch

| File | Change |
|---|---|
| `pyproject.toml` | Add `[tui]` extra; add to dev |
| `mythic_vibe_cli/tui/__init__.py` | NEW |
| `mythic_vibe_cli/tui/app.py` | NEW |
| `mythic_vibe_cli/commands.py` | `cmd_tui` + dispatch |
| `mythic_vibe_cli/app.py` | `tui` sub-parser |
| `tests/test_cli_kernel.py` | Update command-registry expected set; add `tui --help` smoke; add missing-textual fallback test |
| `tests/test_tui.py` | NEW — `build_status_data` tests + Textual headless test |
| `docs/runtime.md` | (no change — TUI is not a runtime primitive) |
| `docs/COMMAND_CONTRACTS.md` | Add `tui` contract |
| `docs/api.md` | Add `tui` cross-link |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Update pyproject.toml ([tui] extra + dev)
- [ ] Implement `tui/__init__.py` and `tui/app.py`
- [ ] Add `cmd_tui` + dispatch
- [ ] Add `tui` sub-parser
- [ ] Update command-registry test expected set
- [ ] Pure-data tests (no textual needed)
- [ ] Headless Textual `run_test` test
- [ ] Missing-textual fallback test (mock the import)
- [ ] `pytest -q` green
- [ ] `ruff` + `mypy` green
- [ ] Doc updates
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. **Cross-platform compliance is non-negotiable** — no `os.name == "nt"` branches in TUI code; let Textual handle terminal differences.
3. Use `from textual.app import App, ComposeResult` etc — late-import inside `cmd_tui` so the rest of the CLI doesn't break when Textual isn't installed.
4. The `build_status_data(root)` function should be pure (no Textual imports) and tested directly.
5. Use `await app.run_test()` for headless tests (Textual's built-in async test driver).
