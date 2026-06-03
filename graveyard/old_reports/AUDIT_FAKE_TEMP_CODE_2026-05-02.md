# Mythic Vibe CLI — Fake/Temp Code Audit
Date: 2026-05-02
HEAD: e0953b6
Branch: development
Auditor: Sólrún Hvítmynd
Environment: Python 3.10, Windows 11, textual 8.2.4 installed

---

## Verdict

The project is **substantially real** — no wholesale stubs, no hollow phase modules, and no
fabricated test counts. The mega-day (PH-09 through PH-18) produced genuine implementations
for every phase. However, **four honest incompletions are structurally present** and several
are either not acknowledged in the closeout prose or are acknowledged only in footnotes while
the phase headline says "closed". The most important single finding is the chat-bridge
long-poll loop: it does not exist in the production code, the `mythic-vibe surface chat`
command returns a scaffolding notice and exits — that is the *entirety* of the feature as
shipped. The memory record says "long-poll deferred"; the closeout prose says "scaffolding
entry … deferred to a future deployment-style PR"; those are honest labels — but the phase is
still marked fully closed. Additionally, the coverage number in every closeout from PH-10
onward reads "76% (held)"; the live measurement is **82%**, meaning the closeout docs carry
a stale metric. The `ai models` command is a documented partial: Ollama listing works;
all other providers return a hard-coded "not implemented" note. The `scaffold` command
supports only `adr`; all other artefact types return an error that says they are not yet
implemented. Both partials are acknowledged in their respective phase closeouts.

---

## Severity Summary

| Severity | Count | One-line description |
|---|---|---|
| High | 1 | chat-bridge poll loop entirely absent; `surface chat` is a scaffolding exit, not a working surface |
| Medium | 4 | coverage metric stale in all closeouts (76% vs 82%); `ai models` partial for non-Ollama providers; `scaffold` supports only `adr`; plugin TUI dispatch "not yet implemented" in picker |
| Low | 4 | cicd TODO markers are intentional user-facing templates; sandbox "not yet wired" note in PH-10 closeout is stale; single POSIX-only test skip (legitimate); `_matrix_request`/`_telegram_request` untested by test suite |

---

## Findings (grouped by category)

---

### Category: Deferred feature sold as done (most critical)

**[High]** `mythic_vibe_cli/surfaces/chat_bridge.py` — `commands.py:3024–3060`

The `cmd_surface_chat` handler, the one and only entry point for
`mythic-vibe surface chat --backend matrix|telegram`, does the following:

```python
payload = {
    "scaffolded": True,
    "note": (
        "This is the slice 17.4 scaffolding entry. The chat "
        "bridge's poll loop expects credentials supplied by "
        "your own deployment script…"
    ),
}
write_line(f"Chat bridge ({backend}) - scaffolding entry")
write_line(payload["note"])
return SUCCESS
```

There is no poll loop anywhere in `chat_bridge.py` (confirmed: `grep` for
`poll_loop`, `run_loop`, `sync_loop`, `matrix_sync`, `getUpdates` all return
zero results). The module supplies `parse_command`, `handle_message`, and the
urllib HTTP client primitives. A caller *could* write a loop around those
primitives, but no such loop is shipped in the CLI.

The `PHASE17_FINALE_CLOSEOUT.md:91–93` says:
> CLI: `mythic-vibe surface chat --backend matrix|telegram` is the **scaffolding entry**.
> The long-poll loop is deferred to a future deployment-style PR.

And at line 135:
> The long-poll loop is deferred — it's a deployment concern, not a contract concern.

These are honest disclosures — but they sit inside a phase marked "fully closed" with
a checkmark on "17.4 Chat bridge scaffolding ✓". The checkmark says "chat bridge" without
saying "parse + dispatch primitives only". A user running `mythic-vibe surface chat
--backend matrix` gets a note and an exit, not a running bridge. The claim of
completeness is overstated relative to what operators can actually run.

Evidence: `commands.py:3024–3060`, `surfaces/chat_bridge.py` (full file search for loop),
`PHASE17_FINALE_CLOSEOUT.md:91–93, 135`.

---

### Category: User-visible "not implemented" messages in production paths

**[Medium]** `mythic_vibe_cli/commands.py:5253–5257` — `ai models` for non-Ollama providers

```python
"models": [],
"note": (
    f"Model listing is not implemented for {provider_name!r} yet — "
    "use the provider's documented model id with `ai run --provider`."
),
```

Any call to `mythic-vibe ai models --provider anthropic` (or openai, gemini, openrouter)
returns an empty model list with a hard-coded "not implemented" notice. Ollama is the only
working path.

Mitigation: `PHASE6_FINALE_CLOSEOUT.md:67–69` explicitly documents this:
> "Other providers: returns 'not implemented for this provider' note for parity."

So the closeout is honest. The production code is the intended behavior, not an oversight.
It still means "ai models" is a partial feature for 4 of 5 providers.

**[Medium]** `mythic_vibe_cli/commands.py:1851–1856` — `scaffold` supports only `adr`

```python
if artefact != "adr":
    write_error(
        f"Scaffold artefact {artefact!r} not yet implemented. "
        "Available now: adr. Future types (task/interface/invariant/risk) land in PH-10 slice 10.4."
    )
    return USER_INPUT_ERROR
```

The `PHASE10_FINALE_CLOSEOUT.md:77–80` documents slice 10.4 as the "Plugin Authoring Guide"
— not the artefact scaffold types. Slice 10.4 never landed the task/interface/invariant/risk
scaffold types; they were pushed forward with a forward reference to PH-10, but PH-10's
closeout records slice 10.4 as completed documentation, not scaffold implementation.
The error message in production code refers to "PH-10 slice 10.4" for types that are
still missing in PH-18 HEAD.

Evidence: `commands.py:1851–1856`, `PHASE10_FINALE_CLOSEOUT.md:77`.

**[Medium]** `mythic_vibe_cli/tui/picker.py:165–168` — plugin dispatch "not yet implemented"

```python
run_hint = (
    "[dim](plugin dispatch not yet implemented; "
    "press Esc to return.)[/dim]"
)
```

This string is user-visible in the TUI slash picker when a non-builtin slash command is
selected. The `test_plugin_slash_dispatch.py:228` asserts this string is present —
the test effectively documents and accepts the gap. The TUI presents external plugin
commands but cannot execute them through the picker; operators must fall back to the REPL.
PH-10's closeout does not explicitly claim the picker dispatches plugins.

Evidence: `tui/picker.py:165–168`, `tests/test_plugin_slash_dispatch.py:228`.

---

### Category: Stale metric in closeout documentation

**[Medium]** `PHASE10_FINALE_CLOSEOUT.md` through `PHASE17_FINALE_CLOSEOUT.md` — coverage figure

Every closeout from PH-10 through PH-18 (all mega-day phases) states:
> **Coverage:** 76% (held).

Live measurement:
```
TOTAL  14230  2143  4040  637  82%
```
Command: `python -m pytest tests/ --cov=mythic_vibe_cli --cov-report=term-missing --tb=no -q`
(run 2026-05-02, 1694 passed, 1 skipped)

The actual coverage is **82%**, not 76%. The discrepancy is 6 percentage points. The figure
was not updated as phases landed. This is a documentation accuracy defect, not a code
defect, but it does mean every status report quoting "76%" understates the actual position.

Evidence: all PHASE*_FINALE_CLOSEOUT.md files (PH-10 through PH-17), live test run above.

---

### Category: TODO markers in production code

**[Low]** `mythic_vibe_cli/cicd/ci_scaffold.py:231–234` and `cicd/docker_scaffold.py:79, 98, 113, 142, 143`

These `TODO` strings are **intentional user-facing scaffold content** — they appear inside
multi-line template strings that the CLI writes into the user's project (`ci scaffold`,
`docker scaffold`). They are instructions to the operator, not developer notes to self.
The context makes this unambiguous: the strings appear in `_render_unknown()` and in
named Dockerfile template constants. Not a stub-code smell.

Evidence: `ci_scaffold.py:231–234`, `docker_scaffold.py:79,98,113,142,143`.

**[Low]** `mythic_vibe_cli/cicd/release.py:138–140`

```python
body_bullets = body_bullets or "- TODO: list user-visible changes."
summary.strip() if summary.strip() else "TODO: one-sentence summary."
```

Same pattern: fallback text written into a rendered release-notes template when the
user omits content. User-visible instructional defaults, not dead developer notes.

---

### Category: `pass`-body / `...`-body functions

**[Low/Design]** `mythic_vibe_cli/plugins/extension_points.py:65,80,94,110,126,142`

All six Protocol classes use `...` (Ellipsis) as method bodies. This is the correct Python
idiom for abstract Protocol method stubs — `...` is the conventional body for Protocol
method declarations. They are not intended to execute; they define a structural interface
for type-checker and `isinstance` use. No issue here.

**[Low]** `mythic_vibe_cli/ai/providers/base.py:49,52,55,107` — same pattern, abstract Protocol.

**[Low]** `mythic_vibe_cli/forge.py:79` — `_SupportsRun.run` with `...`. Marked `pragma: no cover`. Same rationale.

**[Low]** `mythic_vibe_cli/voice/tts.py:115` and `voice/transcribe.py:123,316` — `...` bodies in optional-dependency abstract classes.

**[Low]** `pass` inside exception handlers in `protocols/mcp_server.py:295`, `mcp_client.py:190,194,201`, `acp_bridge.py:225`, `otel.py:144`, `plugins/dispatcher.py:93,224`, `plugins/sandbox.py:261`, `runtime/event_log.py:170`, `policy/policy_gate.py:154`:

All examined in context — every `pass` is inside a defensive `except (OSError|ValueError|...): pass` block on a best-effort operation (stream flush, close, lock release, span recording). None is a silent swallow of a logic exception; all are intentional clean-shutdown guards. No issue.

---

### Category: Untested production code paths

**[Low]** `mythic_vibe_cli/surfaces/chat_bridge.py` — `matrix_send_message`, `telegram_send_message`, `_matrix_request`, `_telegram_request`

These four functions are exported in `__all__` and implement the HTTP client layer. Zero
tests exercise them — the chat bridge test file (`test_surface_chat_bridge.py`) imports
only `parse_command`, `handle_message`, `COMMAND_PREFIX`, `ParsedCommand`, `ChatResponse`.
The HTTP client code is untested. This is low-severity because the functions are simple
urllib wrappers and will only run when operators supply real credentials, but it means
100% of the network-facing code in the module has no test coverage.

Evidence: `tests/test_surface_chat_bridge.py` (no import of `matrix_send_message`,
`telegram_send_message`, `MatrixConfig`, `TelegramConfig`), `chat_bridge.py:297–307`
(`__all__` listing).

---

### Category: Stale PH-10 closeout claim (sandbox wiring)

**[Low]** `PHASE10_FINALE_CLOSEOUT.md:53–59` states:

> Not yet wired into `PluginHookDispatcher` — that integration fits naturally with PH-11…

But in HEAD (e0953b6), `plugins/dispatcher.py:31` imports `safe_call` and uses it at
line 200 inside `_fire`. The sandbox IS wired. The PH-10 closeout note is stale. The PH-11
work landed the wiring and did not update the PH-10 closeout retrospectively. Minor.

Evidence: `plugins/dispatcher.py:31`, `plugins/dispatcher.py:200`, `PHASE10_FINALE_CLOSEOUT.md:53`.

---

### Category: `time.sleep` usage

`mythic_vibe_cli/persistence/json_store.py:37` — `time.sleep(0.05)` inside a busy-wait
file-lock loop (`FileLock.__enter__`). This is a legitimate cross-platform locking
implementation with a deadline check. Not a race-condition Band-Aid. No issue.

---

### Category: Disabled tests

1 test skipped: `tests/test_plugin_sandbox.py:199–208` — `test_posix_returns_rlimit_data`,
skipped on Windows with `self.skipTest("POSIX-specific assertion")`. Legitimate platform guard.
The companion `test_advisory_only_on_windows` (line 192) runs on this host and passes.

No `pytest.mark.skip`, `pytest.mark.xfail`, or `assert True` no-op tests found.
All textual-dependent tests use `@unittest.skipIf(textual_unavailable, ...)` — textual 8.2.4
is installed and all these tests execute (0 textual skips in the run).

---

## Cross-check: Closeout docs vs code

| Closeout claim | Code reality | Assessment |
|---|---|---|
| PH-17: "17.4 Chat bridge scaffolding ✓" | `surface chat` returns a note and exits; no poll loop exists anywhere | **Misrepresented** — checkmark on "chat bridge" implies a running bridge; what shipped is parse+dispatch primitives + HTTP wrappers, no runnable loop. The footnote is honest; the checkmark is not. |
| PH-17: "Web terminal end-to-end (token-gated /api/run)" | Full `ThreadingHTTPServer` + xterm.js HTML + token comparison via `secrets.compare_digest` — all present and functional | Verified |
| PH-17: "SSH doctor 4 checks" | 4 checks in `run_ssh_doctor()`, all real implementations | Verified |
| PH-18: "All 4 canonical simulate scenarios PASS" | `mythic_vibe_cli/robustness/simulate.py` — 4 named scenarios in `CANONICAL_SCENARIOS`; tests pass | Verified |
| PH-18: "No subprocess call bypasses runtime.exec — Not yet" | `cicd/release.py:172`, `cicd/rollback.py:74`, `tui/runner.py:137`, `protocols/mcp_client.py:51` all use subprocess directly | Consistent — closeout accurately marks this as unremediated |
| PH-16: "MCP server implements initialize, tools/list, tools/call, ping" | All four methods present in `mcp_server.py` | Verified |
| PH-16: "ACP cancel is best-effort" | `acp_bridge.py:168–177` sets `cancel_event` but the synchronous handler does not observe it mid-run | Consistent with closeout disclosure |
| PH-14: "Policy gate wired into cmd_oath only" | `commands.py:2776` — only `cmd_oath` calls `enforce_policy` | Verified consistent with closeout |
| PH-10: "Sandbox not yet wired into dispatcher" | **Stale** — `dispatcher.py:31,200` imports and uses `safe_call` | Closeout is stale; reality is better than claimed |
| All PH-10..18 closeouts: "Coverage 76% (held)" | Live: **82%** | Metric is stale in all 9 closeout documents |

---

## Tests

- **Test run:** 1694 passed, 1 skipped, 14 subtests passed in ~80s
- **Coverage:** 82% (branch+line, `mythic_vibe_cli` source only)
  - The claimed 76% in all recent closeout docs is stale by 6 points
- **Skipped tests:** 1 (`test_plugin_sandbox.py:199` — POSIX rlimit, legitimate Windows platform guard)
- **Empty/no-op tests:** 0 found
- **`assert True` / `pass`-only tests:** 0 found
- **`pytest.mark.skip`/`xfail`:** 0 found
- **`@unittest.skipIf(textual_unavailable)`:** 21 tests; textual 8.2.4 is installed so all execute (not skipped in this run)
- **`@unittest.skipUnless(GIT_AVAILABLE)`:** 1 test (git availability check, legitimate)
- **Untested production code:** `chat_bridge.py` HTTP client functions (`matrix_send_message`, `telegram_send_message`, `_matrix_request`, `_telegram_request`) have zero test coverage

---

## Recommendations (prioritized)

1. **[High — PH-17 chat bridge]** Either ship a minimal `run_loop(config: MatrixConfig | TelegramConfig)` function in `chat_bridge.py` and wire it to `cmd_surface_chat`, or change the phase-17 checkmark from "Chat bridge ✓" to "Chat bridge primitives ✓ / poll loop deferred". The current state creates a gap between documentation claim and what an operator can actually run. If the loop is genuinely out of scope, the memory record and closeout prose already say so — the roadmap checkmark should too.

2. **[Medium — coverage metric]** Update the coverage figure in memory and any living status docs from 76% to 82%. All phase closeouts are historical artifacts; the number to fix is in `project_mythic_engineering_cli_status.md` if it echoes 76%.

3. **[Medium — scaffold artefact types]** Decide: either land the task/interface/invariant/risk scaffold types (the error message says they belong to "PH-10 slice 10.4" which has long since closed), or update the error message to say they are not yet on the roadmap. The forward reference in the error message points to a phase that is closed without having delivered those types.

4. **[Medium — ai models non-Ollama]** The "not implemented" note for non-Ollama providers is acceptable as documented, but consider adding `"implemented": false` to the JSON payload so consumers can detect the gap programmatically rather than parsing a human-readable note string.

5. **[Low — TUI plugin dispatch]** The picker shows plugin-contributed slash commands but cannot execute them (prints "not yet implemented"). Document this gap explicitly in PH-10's authoring guide so plugin authors know their commands only work through the REPL, not the TUI picker.

6. **[Low — chat bridge HTTP coverage]** Add at least 2 tests for `matrix_send_message` and `telegram_send_message` using `unittest.mock.patch("urllib.request.urlopen")`. The functions are real code that touches the network; they deserve at least one mock-gated test each.

7. **[Low — PH-10 closeout stale note]** The "sandbox not yet wired into dispatcher" note in PH-10 closeout is factually wrong in HEAD. No action required on old closeout files, but the living status doc should not repeat it.
