# TASK — Audit Remediation Plan (Mythic Vibe CLI)

**Opened:** 2026-05-02
**Branch:** `development`
**HEAD at plan write:** `e0953b6` (pre-remediation)
**Driver audits:**
- `AUDIT_FAKE_TEMP_CODE_2026-05-02.md` — first-pass fake/temp/stub sweep
- `AUDIT_PSEUDOCODE_DEEP_2026-05-02.md` — second-pass pseudo-code sweep

**In-flight (already shipped before plan write):**
- ✅ Closeout docs PH-10..PH-18 patched additively with 2026-05-02 update notices
- ✅ `project_mythic_engineering_cli_status.md` + `MEMORY.md` updated
- ✅ Scaffold `task` / `interface` / `invariant` / `risk` artefact types landed (commands.py + app.py + tests; +6 tests; lint+mypy clean)

---

## Operating rules — durable for the entire task

1. **Additive only — never subtractive.** Per `feedback_additive_only.md`: add wrappers, replacement paths, dated update notices. Do not delete or overwrite. Old/broken paths remain behind new ones until Volmarr explicitly says to clean up.
2. **Operational cadence:** TASK file → commit + push → implement → ruff/mypy/pytest green → phase closeout memo → memory update → push. One phase = one merge-worthy unit.
3. **Tests gate every commit:** `ruff check`, `mypy mythic_vibe_cli/`, `pytest tests/` all green before push. Coverage may not regress below 82%.
4. **Stdlib-first.** No new runtime deps unless unavoidable. Optional deps remain optional under existing extras.
5. **Cross-platform + open-source only** (durable rule).
6. **One real-bug fix per commit.** Mixed commits are forbidden — bug fix + cleanup + feature in one commit are three commits.
7. **No phase claims completion until its closeout memo is written and the test count + coverage in MEMORY.md are refreshed.**

---

## Outstanding inventory (post-2026-05-02-am work)

| # | Sev | Module | Finding | Source |
|---|---|---|---|---|
| 1 | **High** | `voice/tts.py:181` | `ChatterboxEngine.say()` probes `getattr(module, "speak", None)`; chatterbox package exports `ChatterboxTTS`/`ChatterboxVC`/`ChatterboxMultilingualTTS`, no module-level `speak`. Has **never worked.** | Pseudo-code audit |
| 2 | **High** | `surfaces/chat_bridge.py` + `commands.py:3024-3060` | No poll loop — `mythic-vibe surface chat --backend matrix\|telegram` is scaffolding-and-exit. | First audit |
| 3 | **Medium** | `policy/policy_gate.py:85-90` | `evaluate()` exhausts `Iterable[Constraint]` in list-comp at L85, calls `any(constraints)` at L90 on now-empty iterator. Generator inputs silently suppress advisory note. | Pseudo-code audit |
| 4 | **Medium** | `tui/picker.py:165-168` | Plugin slash dispatch shows "(plugin dispatch not yet implemented; press Esc to return.)". Plugin commands run via REPL only. | First audit |
| 5 | **Medium** | `commands.py:5253-5257` + `ai/providers/{anthropic,openai,gemini,openrouter}.py` | `ai models` for non-Ollama providers returns hardcoded `models: []` + "not implemented" note. | First audit |
| 6 | **Low** | `policy/policy_gate.py:57-67` | `_matches_command()` defined with command-scoping docstring, **zero call sites** anywhere. Dead code. | Pseudo-code audit |
| 7 | **Low** | `surfaces/chat_bridge.py` (`matrix_send_message`, `telegram_send_message`, `_matrix_request`, `_telegram_request`) | Four exported HTTP-client functions have zero test coverage. | First audit |
| 8 | **Low** | `ai/providers/yggdrasil.py:169-185` + `mindspark.py:154-179` | Speculative `getattr` probe loops for entry points that may not exist in the external packages. Currently surface `AttributeError` to `metadata["error"]` (better than silent), but brittle. | Pseudo-code audit |

**Acknowledged-and-leave (not in this plan):**
- CI/CD scaffold `TODO` strings (`cicd/ci_scaffold.py`, `cicd/docker_scaffold.py`, `cicd/release.py`) — confirmed by both audits as **intentional user-facing template content**, not developer stubs. **Do not change.**
- `Protocol` classes with `...` bodies in `plugins/extension_points.py`, `ai/providers/base.py`, `voice/tts.py`, `voice/transcribe.py`, `forge.py` — idiomatic Python Protocol declarations. Not stubs.
- `pass` inside defensive `except` blocks in `protocols/`, `acp_bridge.py`, `otel.py`, `plugins/dispatcher.py`, `plugins/sandbox.py`, `runtime/event_log.py`, `policy/policy_gate.py:154` — verified clean-shutdown guards on best-effort operations. Not silent swallows.

---

## Phased plan

Each phase is independently shippable, ordered by **(real-bug-first, smallest first, fewest dependencies first)**. Phases A–C are fast (a few hours each); D and E are larger.

### Phase A — Surgical real-bug fixes
**Goal:** close the two confirmed functional bugs with the smallest possible additive patch.

**A.1 — Chatterbox TTS adapter** (Finding #1, High)
- File: `mythic_vibe_cli/voice/tts.py`
- Approach: keep the existing `getattr(module, "speak", None)` probe **and the entire `ChatterboxEngine.say()` body** intact. ADD a new probe path that detects the real exports (`ChatterboxTTS`/`ChatterboxMultilingualTTS`) and binds an adapter shim that calls the modern API. Existing failure path remains as the fallback if neither old nor new shape is present.
- Tests: add `tests/test_voice_chatterbox_adapter.py` — mocks the chatterbox module with each export shape; asserts the adapter chooses the right path for each shape. Existing tests must stay green.
- Done-when: `mythic-vibe voice say "hello" --engine chatterbox --force` against a real install completes with `spoken=True`. Coverage on `voice/tts.py` rises.

**A.2 — policy_gate iterable exhaustion** (Finding #3, Medium)
- File: `mythic_vibe_cli/policy/policy_gate.py:85-90`
- Approach: ADD a single `constraints = list(constraints)` at the top of `evaluate()` (before the first iteration). The list-comp at L85 and the `any()` at L90 then operate on the same materialised list. Old logic is preserved character-for-character below the new line.
- Tests: add `tests/test_policy_gate_generator_inputs.py` — passes a generator into `evaluate()` and asserts the advisory note appears in the result (currently fails — proves the bug — and passes after the fix).
- Done-when: new test passes; existing `test_policy_*.py` tests stay green.

**Phase A commit shape:** two commits, one per finding. Each gets its own closeout note appended to `PHASE14_FINALE_CLOSEOUT.md` (policy gate lives in PH-14) and `PHASE7_FINALE_CLOSEOUT.md` (TTS lives in PH-07) **additively**.

**Phase A done-when:** both bugs have failing-then-passing tests; closeouts updated; status memory updated; pushed to `development`.

---

### Phase B — `_matches_command` reactivation
**Goal:** wire the dead-code function into `evaluate()` so command-scoped policy enforcement works as the docstring claims.

**B.1 — Wire `_matches_command()` into `evaluate()`** (Finding #6, Low)
- File: `mythic_vibe_cli/policy/policy_gate.py:57-67` + `evaluate()` body
- Approach: keep `_matches_command` as-is (zero edits to its body). ADD a call site inside `evaluate()` so each constraint is filtered through `_matches_command(constraint, command_name)` before being applied. Existing behaviour for constraints without a command-scope field is unchanged (function returns True for unscoped constraints).
- Tests: add tests in `tests/test_policy_gate_command_scoping.py` covering: unscoped-constraint always matches; scoped-constraint matches only the named command; case-insensitivity if the existing helper supports it.
- Done-when: command-scoped constraints in `mythic/constraints.md` actually scope to the named command.

**Phase B commit shape:** one commit + closeout addendum to `PHASE14_FINALE_CLOSEOUT.md` (additive).

---

### Phase C — TUI plugin slash dispatch
**Goal:** wire the TUI slash picker through to the plugin dispatcher so plugin-contributed slash commands actually run from the TUI (not just the REPL).

**C.1 — Picker → dispatcher wiring** (Finding #4, Medium)
- Files: `mythic_vibe_cli/tui/picker.py:165-168` + relevant plugin dispatcher entry point + new `tui/runner.py` integration
- Approach: keep the existing `"(plugin dispatch not yet implemented; press Esc to return.)"` branch as a final fallback. ADD a primary dispatch path BEFORE that branch — if the selected entry has a `plugin_id` / `dispatch_target`, route through `plugins.dispatcher.dispatch_slash(name, args)` and surface result in the TUI's running-command screen. The fallback fires only if dispatch returns "not handled" (defensive belt-and-suspenders).
- Tests: extend `tests/test_plugin_slash_dispatch.py` — currently asserts the "not yet implemented" string is shown. ADD new headless TUI integration test that selects a fake plugin slash command from the picker and asserts it invokes the dispatcher.
- Done-when: plugin slash commands run from the TUI picker; the "not yet implemented" string remains as a final fallback that the integration test no longer hits for the happy path.

**Phase C commit shape:** one commit + closeout addendum to `PHASE10_FINALE_CLOSEOUT.md` (plugin work owns this) **additively**.

---

### Phase D — `ai models` per-provider expansion
**Goal:** make `ai models --provider anthropic|openai|gemini|openrouter` return a real listing where the provider supports it, instead of the canned "not implemented" payload.

**D.1 — Provider catalog approach** (Finding #5, Medium)
- Files: `mythic_vibe_cli/commands.py:5253-5257` (the dispatch) + each provider in `ai/providers/{anthropic,openai,gemini,openrouter}.py`
- Approach: keep the existing `"models": [], "note": "not implemented…"` branch as the catch-all for providers that don't implement listing. ADD a per-provider `list_models()` method on each provider class. Implementations:
  - **Anthropic:** static catalog (latest Claude IDs hardcoded with last-updated date); ADR-0010 to record why we ship a static catalog vs hitting `/v1/models` (Anthropic's models endpoint is stable enough that a static catalog avoids requiring an API key just to list).
  - **OpenAI:** static catalog with optional `--remote` flag that does a real `/v1/models` GET if `OPENAI_API_KEY` is set.
  - **Gemini / OpenRouter:** static catalog; remote optional same shape as OpenAI.
- ADD `Models implemented: true` flag to JSON payload so consumers can detect real vs canned.
- Tests: per-provider tests with `unittest.mock.patch("urllib.request.urlopen")` for the remote-listing path; static catalog tests that just assert non-empty + ID format.
- Done-when: `mythic-vibe ai models --provider <name>` returns a non-empty list for all 5 providers.

**Phase D commit shape:** five small commits (one per provider, then the dispatcher refresh) + ADR-0010 + closeout addendum to `PHASE6_FINALE_CLOSEOUT.md` additively.

---

### Phase E — Chat bridge poll loop (the big one)
**Goal:** ship a runnable Matrix + Telegram chat bridge so PH-17 slice 17.4's checkmark is no longer caveated.

**E.1 — Matrix `/sync` long-poll loop**
- File: ADD a new `surfaces/chat_bridge_loop.py` module. Keep `chat_bridge.py` (parse_command, handle_message, urllib HTTP primitives, `cmd_surface_chat` exit) untouched.
- Approach: implement `run_matrix_loop(config: MatrixConfig, *, stop_event: threading.Event | None = None)` that calls `/sync` with a long-poll timeout, dispatches each message through `parse_command` + `handle_message`, replies via `matrix_send_message`. Honours `stop_event` for clean shutdown.
- Add a new CLI subcommand: `mythic-vibe surface chat --backend matrix --run` (the `--run` flag is the additive switch — without it, the existing scaffolding-and-exit behaviour is preserved).

**E.2 — Telegram `getUpdates` long-poll loop**
- Same shape as E.1: `run_telegram_loop(config: TelegramConfig, *, stop_event=None)` in the same new module.

**E.3 — Wire `--run` into `cmd_surface_chat`**
- File: `mythic_vibe_cli/commands.py:3024-3060`
- Approach: keep the entire existing scaffolding-and-exit body. ADD a `--run` branch BEFORE the existing exit that invokes the appropriate loop function. Old behaviour (no `--run` flag) is unchanged.

**E.4 — Tests + docs**
- Tests: `unittest.mock.patch("urllib.request.urlopen")` to feed canned `/sync` and `getUpdates` responses; assert the loop dispatches expected commands and exits cleanly on `stop_event`.
- Docs: ADD a "Running the bridge" section to `docs/SSH_DEPLOYMENT.md` (or a new `docs/CHAT_BRIDGE_DEPLOYMENT.md`) with credential setup, systemd unit example, and security caveats.

**Phase E commit shape:** four commits (E.1, E.2, E.3, E.4 — docs+tests). Per Volmarr's durable rule, each commit closes one slice, no batching.

**Phase E done-when:** an operator can run `mythic-vibe surface chat --backend matrix --run` (or `--backend telegram --run`) with credentials in env and the bridge actually polls + replies. PH-17 closeout gets a follow-up additive note: "**E.1–E.4 closed 2026-XX-XX** — long-poll loop now shipped; the 2026-05-02 caveat block above is now historical."

---

### Phase F — Test coverage + brittle-probe hardening
**Goal:** close the two Low findings: untested chat-bridge HTTP and brittle `getattr` probes in island adapters.

**F.1 — chat_bridge HTTP client tests** (Finding #7, Low)
- File: ADD `tests/test_chat_bridge_http_client.py`
- Approach: `unittest.mock.patch("urllib.request.urlopen")` for `_matrix_request` + `_telegram_request`; build `Request` objects, assert URL/method/body/headers; for `matrix_send_message` + `telegram_send_message` assert payload shape and method (POST). One mock-driven test per function (4 tests).
- Done-when: coverage on `chat_bridge.py` HTTP paths reaches >= 90%.

**F.2 — Yggdrasil + MindSpark probe hardening** (Finding #8, Low)
- Files: `mythic_vibe_cli/ai/providers/yggdrasil.py:169-185` + `mindspark.py:154-179`
- Approach: keep the existing `getattr` probe loop as a fallback (per additive rule). ADD a primary dispatch that targets the **documented entry points** of each external package (research them first; record findings in this TASK file before coding). If the documented entry point exists, use it directly; if not, fall through to the probe loop with a warning logged.
- Open question (record in this file before coding): **what are the actual documented entry points for the Yggdrasil and MindSpark packages?** The probe-loop names (`route`, `router.route`, `ask`, `plan`, `cognition.plan`) suggest guessing. We need to inspect the real packages or read their README before writing the primary dispatch.
- Tests: mock the external module to provide each documented entry point; assert primary dispatch is preferred. Mock to provide ONLY the legacy probe-target; assert fallback warning is logged + probe path runs.
- Done-when: probe path becomes a fallback, not the primary; warning logs surface so operators know they're on the brittle path.

**Phase F commit shape:** two commits.

---

### Phase G — Audit re-run + final closeout
**Goal:** verify the codebase is clean and refresh all metrics.

**G.1 — Re-run both audits**
- Re-dispatch the auditor agent against HEAD post-Phase-F. Expected verdict: clean or near-clean.
- If new findings surface, file them as a follow-up phase (don't extend this TASK).

**G.2 — Refresh coverage + metrics**
- Run `pytest --cov=mythic_vibe_cli --cov-report=term-missing -q`.
- Update MEMORY.md + `project_mythic_engineering_cli_status.md` with the post-remediation test count, coverage %, and "Audit Remediation Closed" status line.

**G.3 — Write the remediation closeout**
- New file: `AUDIT_REMEDIATION_CLOSEOUT_2026-XX-XX.md` in repo root.
- Tabulates each finding from both audits + which commit closed it + which closeout addendum carries the historical record.
- Mark this TASK file `STATUS: COMPLETE` and append a final-state summary.

---

## Progress tracker (live — update after each phase commit)

```
Phase A — Surgical real-bug fixes
  [ ] A.1  Chatterbox TTS adapter                       (voice/tts.py, voice tests)
  [ ] A.2  policy_gate iterable exhaustion              (policy_gate.py, new test)

Phase B — Dead-code reactivation
  [ ] B.1  _matches_command wired into evaluate()       (policy_gate.py)

Phase C — TUI plugin slash dispatch
  [ ] C.1  picker → dispatcher wiring                   (tui/picker.py + tests)

Phase D — ai models per-provider expansion
  [ ] D.1  Anthropic list_models                        (ai/providers/anthropic.py)
  [ ] D.2  OpenAI list_models (+ optional --remote)     (ai/providers/openai.py)
  [ ] D.3  Gemini list_models                           (ai/providers/gemini.py)
  [ ] D.4  OpenRouter list_models                       (ai/providers/openrouter.py)
  [ ] D.5  Dispatcher refresh + ADR-0010                (commands.py, docs/ADRS/)

Phase E — Chat bridge poll loop
  [ ] E.1  Matrix /sync loop                            (surfaces/chat_bridge_loop.py)
  [ ] E.2  Telegram getUpdates loop                     (surfaces/chat_bridge_loop.py)
  [ ] E.3  --run flag wired into cmd_surface_chat       (commands.py)
  [ ] E.4  Tests + deployment docs                      (tests/, docs/)

Phase F — Coverage + probe hardening
  [ ] F.1  chat_bridge HTTP client tests                (tests/test_chat_bridge_http_client.py)
  [ ] F.2  Yggdrasil + MindSpark documented entry points (ai/providers/{yggdrasil,mindspark}.py)

Phase G — Audit re-run + closeout
  [ ] G.1  Re-dispatch first + second audit             (auditor agent)
  [ ] G.2  Refresh coverage + metrics                   (MEMORY.md, status memory)
  [ ] G.3  Write AUDIT_REMEDIATION_CLOSEOUT_...md       (repo root)
```

---

## Risks / open questions to resolve before coding each phase

- **Phase A.1 (Chatterbox):** what is the chatterbox package's modern API exactly? Need to read `chatterbox/src/chatterbox/__init__.py` for the install we have, OR pin to a known version. If the API takes a model checkpoint argument we need to expose, document it as a CLI flag.
- **Phase D:** Volmarr — preference on remote-listing default? My recommendation: static catalog by default (no API call required), `--remote` opt-in. Anthropic specifically: stick to static-only since the `/v1/models` endpoint isn't widely documented.
- **Phase E:** Matrix and Telegram bridges both need credentials at runtime. Where do we read them from? Recommend `MYTHIC_CHAT_MATRIX_TOKEN` / `MYTHIC_CHAT_TELEGRAM_TOKEN` env vars (durable cross-platform pattern), with optional `--config <path>` override for ops who prefer a file.
- **Phase F.2:** the probe-loop entry-point names look guessed. Need to verify the actual Yggdrasil and MindSpark APIs. If those packages aren't external (they may live in Volmarr's other repos — `WYRD-Protocol` for Yggdrasil maybe?), we should pin the import to a specific known-good entry point.

---

## Next step (the very next action when work resumes)

1. Volmarr reviews this plan; confirms phase order and the open questions above.
2. Commit + push this TASK file and the existing scaffold/closeout/memory work to `development`.
3. Begin **Phase A.1 — Chatterbox TTS adapter** (smallest real-bug fix; closes the most embarrassing finding).

---

## Status

`STATUS: PLAN WRITTEN — AWAITING VOLMARR'S GO-AHEAD AND PHASE A KICKOFF`
