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

### Phase D — `ai models` per-provider expansion (fully featured)
**Goal:** make `ai models --provider <name>` return a rich, real listing for every supported provider, with both static (offline) and remote (live HTTP) paths.

**Locked scope (Volmarr 2026-05-02):** **do BOTH fully** — static catalog AND remote listing for every provider. Static is the default (offline-friendly, no API key needed); `--remote` triggers a real HTTP listing.

**D.1 — Provider catalog scaffolding** (Finding #5, Medium)
- New module: `mythic_vibe_cli/ai/providers/model_catalog.py` (or extend `base.py`).
- Frozen dataclass `ModelInfo`:
  ```
  id: str                 # canonical provider model id
  family: str             # "claude" | "gpt" | "gemini" | "openrouter"
  display_name: str
  context_window: int     # tokens; 0 if unknown
  max_output_tokens: int  # 0 if not declared
  capabilities: tuple[str, ...]   # ("vision", "audio", "tools", "thinking", ...)
  source: str             # "static" | "remote"
  last_updated: str       # ISO date (static records only)
  ```
- Helper: `to_dict()` for JSON serialisation.

**D.2 — Anthropic** (static + remote)
- Static catalog includes: `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001` (capabilities tuned per current cutoff).
- Remote: `GET https://api.anthropic.com/v1/models` with `x-api-key` + `anthropic-version` headers. Falls back to static + warning when `ANTHROPIC_API_KEY` missing.

**D.3 — OpenAI** (static + remote)
- Static catalog of current GA models.
- Remote: `GET https://api.openai.com/v1/models` with `Authorization: Bearer $OPENAI_API_KEY`.

**D.4 — Gemini** (static + remote)
- Static catalog.
- Remote: `GET https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY`.

**D.5 — OpenRouter** (static + remote)
- Static catalog (curated subset of popular routes).
- Remote: `GET https://openrouter.ai/api/v1/models` (unauthenticated for listing).

**D.6 — Dispatcher refresh + ADR-0010**
- `commands.py:cmd_ai_models` honours `--remote`, calls each provider's `list_models(remote=...)`, falls back to static + emits a warning record if remote fails.
- JSON payload gains `"source": "static" | "remote"`, `"implemented": true`, `"warnings": [...]`.
- ADR-0010 documents the static-default-with-remote-opt-in policy.

**Phase D commit shape:** five commits (D.1 scaffolding + D.2..D.5 per provider) + D.6 dispatcher + ADR-0010 + closeout addendum to `PHASE6_FINALE_CLOSEOUT.md`.

**Phase D done-when:** `mythic-vibe ai models --provider <name>` returns a non-empty `models` list for **all** 5 providers (Ollama already worked + 4 new). `--remote` actually fetches live listings where the provider supports it. Tests with `unittest.mock.patch("urllib.request.urlopen")` cover the remote path; static-catalog tests assert non-empty + correct ID format. Coverage on `ai/providers/*.py` rises proportionally.

---

### Phase E — Chat bridge poll loop (fully featured, the big one)
**Goal:** ship a production-grade runnable Matrix + Telegram chat bridge so PH-17 slice 17.4's checkmark is no longer caveated.

**Locked scope (Volmarr 2026-05-02):** **do all parts fully featured.** Both backends, env-var + config-file credentials, master gate, allowlist enforcement, clean shutdown, reconnect-with-backoff, structured logging, deployment docs.

**E.0 — Config + master gate** (precedes the loops)
- `MYTHIC_CHAT_BRIDGE_ENABLED=1` master env gate (default off — durable rule). `--run` refuses without it.
- `MatrixConfig` and `TelegramConfig` (already exist per audit) gain:
  - `from_env(cls)` classmethod reading the canonical env vars
  - `from_file(cls, path: Path)` classmethod reading JSON (alt: TOML if simpler)
  - `from_sources(cls, *, config_path: Path | None)` that does the merge (env wins for unset file fields and vice versa — file overrides env when both present, since file is more specific)
  - `validate()` method that raises a typed `ChatBridgeConfigError` on missing required fields, and **refuses if no allowlist is set** (operator must explicitly opt into broadcast via `ALLOWED_*=*`).

**E.1 — Matrix `/sync` long-poll loop**
- File: new `surfaces/chat_bridge_loop.py`. Existing `chat_bridge.py` untouched.
- `run_matrix_loop(config: MatrixConfig, *, stop_event: threading.Event | None = None, timeout_ms: int = 30000)`:
  - Initial `GET /sync?timeout=<ms>` to grab `next_batch` token.
  - Loop: `GET /sync?since=<token>&timeout=<ms>`, dispatch new room messages through `parse_command` + `handle_message`, reply via `matrix_send_message` only to allowlisted rooms.
  - **Echo prevention:** skip messages whose sender == bot's own user_id (avoids reply loops).
  - **Reconnect with backoff:** transient HTTP errors (5xx, network reset) → exponential backoff capped at 60s; 4xx → log + abort.
  - Honours `stop_event` between sync calls for clean shutdown.

**E.2 — Telegram `getUpdates` long-poll loop**
- Same shape as E.1: `run_telegram_loop(config, *, stop_event, timeout_s=30)`.
- `GET /bot<token>/getUpdates?offset=<id>&timeout=<s>`, dispatch + reply via `telegram_send_message`.
- Allowlist enforcement on **both** chat_id and user_id (a chat could have multiple users).
- Same echo prevention + reconnect backoff.

**E.3 — `--run` wired into `cmd_surface_chat`**
- File: `commands.py:3024-3060`. Keep the entire existing scaffolding-and-exit body. ADD a `--run` branch BEFORE the existing exit that invokes the appropriate loop function. Old behaviour preserved when `--run` is absent.
- New flags: `--config <path>` (file override), `--timeout <seconds>` (long-poll timeout for the chosen backend).
- SIGINT / SIGTERM → set the `stop_event` so the loop exits cleanly between sync calls.

**E.4 — Tests**
- `tests/test_chat_bridge_loop_matrix.py` — `unittest.mock.patch("urllib.request.urlopen")` feeds canned `/sync` payloads. Verify: command dispatch, allowlist filtering (allowed room replies, denied room ignored), echo prevention (own messages skipped), backoff on 5xx, clean stop on `stop_event.set()`, validate refuses without allowlist.
- `tests/test_chat_bridge_loop_telegram.py` — same shape against `getUpdates` payloads.
- `tests/test_chat_bridge_config.py` — `from_env`, `from_file`, `from_sources` merge, `validate()` raising on missing fields, `validate()` refusing without allowlist (and accepting explicit `*` opt-in).
- Existing 4 untested HTTP client functions (`matrix_send_message`, `telegram_send_message`, `_matrix_request`, `_telegram_request`) gain coverage as a side-effect.

**E.5 — Deployment docs**
- New `docs/CHAT_BRIDGE_DEPLOYMENT.md` with:
  - Required env vars / config file shape
  - Allowlist policy + the explicit-broadcast caveat
  - systemd unit example (Linux)
  - Windows service example (NSSM)
  - macOS launchd plist example
  - TLS / reverse-proxy notes (Matrix homeserver typically on HTTPS)
  - Rate-limit guidance (Telegram 30 msg/s, Matrix per-room limits)

**Phase E commit shape:** five commits (E.0 config, E.1 Matrix loop, E.2 Telegram loop, E.3 wire-up, E.4 tests, E.5 docs — six logical commits actually; one per concern). Per Volmarr's durable rule.

**Phase E done-when:** operator can run `mythic-vibe surface chat --backend matrix --run` (or `--backend telegram --run`) with creds in env + allowlist set, and the bridge actually polls + replies + reconnects + shuts down cleanly. PH-17 closeout gets a follow-up additive note: "**E.0–E.5 closed 2026-XX-XX** — long-poll loop now shipped; the 2026-05-02 caveat block above is now historical."

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

## Phase closeouts (additive — appended as each phase ships)

### Phase A — closed 2026-05-02
- **A.1** Chatterbox TTS adapter — commit `6f60e57`. Adds modern-API
  detection (`ChatterboxTTS` / `ChatterboxMultilingualTTS` via
  `from_pretrained` → `generate` → `torchaudio.save`) before the
  legacy `speak()` probe (preserved as fallback). 23 new tests, all
  failure branches covered. PHASE7_FINALE_CLOSEOUT.md gained an
  additive 2026-05-02 update notice.
- **A.2** policy_gate iterable exhaustion — commit `8578698`. Adds
  `constraints = list(constraints)` at the top of `evaluate()`;
  list-comp + `any()` check now operate on the same materialised
  list. 3 new regression tests (one verified to fail against
  un-fixed code). PHASE14_FINALE_CLOSEOUT.md gained an additive
  2026-05-02 update notice.

**Cumulative test delta:** 1700 → 1726 (+26 from Phase A).
**Coverage:** still ≥ 82% (no regression). Lint + mypy clean.

### Phase B — closed 2026-05-02
- **B.1** `_matches_command` reactivation — commit `1c482be`. The
  function body is preserved verbatim. New helpers
  `_extract_command_tags` + `_constraint_applies_to_command` realise
  the docstring's promised `[command:<name>]` tag scoping. `evaluate()`
  now filters constraints through the new helper. Untagged
  constraints continue to apply broadly (pre-Phase-B default
  preserved); tagged constraints scope correctly. 6 new tests cover
  case-insensitivity, multi-tag OR semantics, mixed tagged+untagged
  filtering, and advisory-note suppression. PHASE14_FINALE_CLOSEOUT.md
  gained an additive update notice.

**Cumulative test delta after Phase B:** 1700 → 1732 (+32). Coverage
still ≥ 82%. Lint + mypy clean.

### Phase C — closed 2026-05-02
- **C.1** TUI plugin slash dispatch — commit `39e0497`. Adds an
  in-process `run_slash` protocol to the plugin layer:
  `SlashRunResult` dataclass, `PluginHookDispatcher.dispatch_slash`,
  `SlashCommandInfo.runnable: bool = False` (additive opt-in),
  `PickerEntry.dispatch_mode` property, and a new
  `PluginSlashRunScreen` that drives dispatch + renders results.
  Plugin failures (raise / wrong return type / no handler) all
  surface as clean error messages. Legacy "(plugin dispatch not
  yet implemented)" message preserved as final fallback for plugins
  that opted into neither argv nor runnable. PHASE10_FINALE_CLOSEOUT.md
  gained an additive update notice.

**Cumulative test delta after Phase C:** 1700 → 1751 (+51). Coverage
still ≥ 82%. Lint + mypy clean.

### Phase D — closed 2026-05-02
- **D.1 + D.2 + D.3 + D.4 + D.5 + D.6** `ai models` per-provider —
  commit `a7367c2`. New `ai/providers/model_catalog.py` with
  `ModelInfo` / `ModelListing` / `ProviderListingError` + static
  catalogs for Anthropic (3) / OpenAI (4) / Gemini (4) / OpenRouter
  (5) + per-provider remote fetchers + top-level `list_models`
  dispatcher. Each of the 4 provider classes gained a `list_models`
  method delegating to the catalog. `cmd_ai_models` re-routed
  through the new protocol; legacy "not implemented" branch
  preserved as defensive fallback. New `--remote` argparse flag.
  ADR-0010 documents the static-first-with-remote-opt-in policy.
  PHASE6_FINALE_CLOSEOUT.md gained an additive update notice.

**Cumulative test delta after Phase D:** 1700 → 1783 (+83). Coverage
still ≥ 82%. Lint + mypy clean.

---

## Progress tracker (live — update after each phase commit)

```
Phase A — Surgical real-bug fixes  [CLOSED 2026-05-02]
  [x] A.1  Chatterbox TTS adapter                       (voice/tts.py, voice tests)
  [x] A.2  policy_gate iterable exhaustion              (policy_gate.py, new test)

Phase B — Dead-code reactivation  [CLOSED 2026-05-02]
  [x] B.1  _matches_command wired into evaluate()       (policy_gate.py)

Phase C — TUI plugin slash dispatch  [CLOSED 2026-05-02]
  [x] C.1  picker → dispatcher wiring                   (tui/picker.py + tests)

Phase D — ai models per-provider expansion (static + remote)  [CLOSED 2026-05-02]
  [x] D.1  ModelInfo dataclass + catalog scaffolding    (ai/providers/model_catalog.py)
  [x] D.2  Anthropic static + remote list_models        (ai/providers/anthropic.py)
  [x] D.3  OpenAI static + remote list_models           (ai/providers/openai.py)
  [x] D.4  Gemini static + remote list_models           (ai/providers/gemini.py)
  [x] D.5  OpenRouter static + remote list_models       (ai/providers/openrouter.py)
  [x] D.6  Dispatcher refresh + ADR-0010                (commands.py, docs/ADRS/)

Phase E — Chat bridge poll loop (fully featured, all parts)
  [ ] E.0  Config + master gate + allowlist refusal     (surfaces/chat_bridge.py — additive)
  [ ] E.1  Matrix /sync loop + echo prevention + backoff (surfaces/chat_bridge_loop.py)
  [ ] E.2  Telegram getUpdates loop + allowlist on chat+user (surfaces/chat_bridge_loop.py)
  [ ] E.3  --run flag + --config + signal handling      (commands.py)
  [ ] E.4  Tests for loops + config + HTTP coverage     (tests/test_chat_bridge_*.py)
  [ ] E.5  CHAT_BRIDGE_DEPLOYMENT.md (systemd/NSSM/launchd) (docs/)

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
  - **RESOLVED 2026-05-02:** read the vendored package; modern API is `from chatterbox.tts import ChatterboxTTS` → `cls.from_pretrained(device=...)` → `model.generate(text)` → `torchaudio.save(path, wav, model.sr)`. Adapter shipped in commit `6f60e57`.
- **Phase D:** Volmarr — preference on remote-listing default? My recommendation: static catalog by default (no API call required), `--remote` opt-in. Anthropic specifically: stick to static-only since the `/v1/models` endpoint isn't widely documented.
  - **RESOLVED 2026-05-02 (Volmarr's call):** **do BOTH fully — static catalog AND remote listing for every provider.** Static is the default (offline-friendly); `--remote` triggers a real HTTP listing where the provider supports it. Anthropic gets remote too (their `/v1/models` does exist, just less documented historically). Each provider returns metadata-rich `ModelInfo` records (id, family, context_window, capability flags). JSON output gains `"source": "static" | "remote"` and `"implemented": true` for programmatic detection.
- **Phase E:** Matrix and Telegram bridges both need credentials at runtime. Where do we read them from? Recommend `MYTHIC_CHAT_MATRIX_TOKEN` / `MYTHIC_CHAT_TELEGRAM_TOKEN` env vars (durable cross-platform pattern), with optional `--config <path>` override for ops who prefer a file.
  - **RESOLVED 2026-05-02 (Volmarr's call):** **do all parts fully featured.** Both Matrix and Telegram backends. Hybrid credentials: env-vars-first with `--config <path>` override. Master gate `MYTHIC_CHAT_BRIDGE_ENABLED=1` (default off — durable rule). Refuse to `--run` without explicit allowlist (rooms for Matrix; chat IDs + user IDs for Telegram); operator must opt into broadcast with `ALLOWED_*=*` (not recommended). Both `MatrixConfig` and `TelegramConfig` gain `from_env()` and `from_file()` classmethods. Loop functions accept `stop_event: threading.Event | None` for clean shutdown. Reconnect-with-backoff on transient HTTP failures. Logging via the existing structured event-log layer. Deployment guide at `docs/CHAT_BRIDGE_DEPLOYMENT.md` with systemd unit example.
- **Phase F.2:** the probe-loop entry-point names look guessed. Need to verify the actual Yggdrasil and MindSpark APIs. If those packages aren't external (they may live in Volmarr's other repos — `WYRD-Protocol` for Yggdrasil maybe?), we should pin the import to a specific known-good entry point.

---

## Next step (the very next action when work resumes)

1. Volmarr reviews this plan; confirms phase order and the open questions above.
2. Commit + push this TASK file and the existing scaffold/closeout/memory work to `development`.
3. Begin **Phase A.1 — Chatterbox TTS adapter** (smallest real-bug fix; closes the most embarrassing finding).

---

## Status

`STATUS: PLAN WRITTEN — AWAITING VOLMARR'S GO-AHEAD AND PHASE A KICKOFF`

---

### Status (additive update 2026-05-02)

`STATUS: PHASE A CLOSED — ready for Phase B (`_matches_command` reactivation).`

Live HEAD: `8578698` (after Phase A.2). Tests: 1726 passed, 1 skipped,
lint + mypy clean, working tree clean and pushed to `development`.

### Status (additive update 2026-05-02 — Phase B)

`STATUS: PHASE B CLOSED — ready for Phase C (TUI plugin slash dispatch).`

Live HEAD: `1c482be` (after Phase B). Tests: 1732 passed, 1 skipped,
lint + mypy clean, working tree clean and pushed to `development`.

**Closed so far:** 3 of 8 outstanding findings (audit findings #1, #3,
#6). 5 remain: chat-bridge poll loop, ai models non-Ollama, TUI plugin
dispatch, chat_bridge HTTP coverage, yggdrasil/mindspark probes.

### Status (additive update 2026-05-02 — Phase C)

`STATUS: PHASE C CLOSED — ready for Phase D (ai models per-provider, fully featured).`

Live HEAD: `39e0497` (after Phase C). Tests: 1751 passed, 1 skipped,
lint + mypy clean, working tree clean and pushed to `development`.

**Closed so far:** 4 of 8 outstanding findings (audit findings #1, #3,
#4, #6). 4 remain: chat-bridge poll loop (E), ai models non-Ollama (D),
chat_bridge HTTP coverage (F.1), yggdrasil/mindspark probes (F.2).

### Status (additive update 2026-05-02 — Phase D)

`STATUS: PHASE D CLOSED — ready for Phase E (chat-bridge poll loop, the big one).`

Live HEAD: `a7367c2` (after Phase D). Tests: 1783 passed, 1 skipped,
lint + mypy clean, working tree clean and pushed to `development`.

**Closed so far:** 5 of 8 outstanding findings (audit findings #1, #3,
#4, #5, #6). 3 remain: chat-bridge poll loop (E — biggest item, the
sole remaining High-severity finding), chat_bridge HTTP coverage (F.1
— absorbed into E.4's tests as a natural side-effect),
yggdrasil/mindspark probes (F.2).
