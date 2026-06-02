# Mythic Vibe CLI — Audit Remediation Closeout

**Date:** 2026-05-02
**Branch:** `development`
**Pre-remediation HEAD:** `e0953b6`
**Post-remediation HEAD:** `4af3dca`
**Plan:** `TASK_AUDIT_REMEDIATION_PLAN.md`
**Authors:** Volmarr Wyrd & Runa Gridweaver Freyjasdottir

---

## Executive verdict

**All 8 outstanding audit findings — 2 High, 4 Medium, 2 Low — are
closed.** The remediation cycle ran to completion in a single working
day (2026-05-02), shipped through 7 phases (A → G) with strict
operational discipline (one logical concern per phase, additive-only
fixes, ruff + mypy + pytest gating every commit, closeout addenda for
every claim), and added **+175 net tests** (1700 → 1875) without
moving coverage off its post-mega-day floor of **82%**.

The "fully featured" directive Volmarr gave for Phases D and E was
honoured: Phase D shipped both static catalog AND live remote listing
for all four remote AI providers (Anthropic / OpenAI / Gemini /
OpenRouter) plus ADR-0010 documenting the policy. Phase E shipped a
production-grade running chat bridge for Matrix + Telegram with master
gate, allowlist refusal, echo prevention, exponential backoff,
SIGINT/SIGTERM clean shutdown, and a deployment guide covering
systemd / NSSM / launchd.

The "additive only — never subtractive" rule (durable; recorded in
`feedback_additive_only.md`) was honoured throughout: every legacy /
broken / deferred path was preserved as a fallback behind the new
primary path. Closeout documents gained dated `Update Notice`
addenda; original prose stayed intact.

---

## Driver audits

| Audit | File | Severity counts (original) |
|---|---|---|
| First pass — fake/temp/stub sweep | `AUDIT_FAKE_TEMP_CODE_2026-05-02.md` | 1 High, 4 Medium, 4 Low |
| Second pass — pseudo-code focus | `AUDIT_PSEUDOCODE_DEEP_2026-05-02.md` | 1 High, 1 Medium, 3 Low |

After de-duplication (chat_bridge HTTP coverage appeared in both at
different angles): **8 distinct findings** entered the remediation
plan.

---

## Per-finding closure ledger

Every finding records: severity at audit time → closing phase →
commit hash → primary new code path → preserved legacy fallback path
→ closeout addendum.

### #1 — Chatterbox `speak()` mapping broken (High)

- **Phase:** A.1
- **Commit:** `6f60e57` — *fix(voice): Phase A.1 — Chatterbox modern-API adapter (additive)*
- **New primary path:**
  - `mythic_vibe_cli/voice/tts.py` — `_resolve_modern_tts_cls()`
    walks `_MODERN_CLASS_CANDIDATES` (`chatterbox.tts.ChatterboxTTS`,
    `chatterbox.ChatterboxTTS`, `chatterbox.mtl_tts.ChatterboxMultilingualTTS`,
    `chatterbox.ChatterboxMultilingualTTS`), then `_say_via_modern()`
    runs the `from_pretrained → generate → torchaudio.save` pipeline.
- **Preserved legacy fallback:**
  - The pre-2026-05-02 `getattr(self._module, "speak", None)` block
    is preserved verbatim in `ChatterboxEngine.say()` after the
    modern-path probe. Fires only when no modern class is reachable.
- **Closeout addendum:** `PHASE7_FINALE_CLOSEOUT.md` § *Update Notice — 2026-05-02 (additive, Phase A.1 of audit remediation)*

### #2 — chat_bridge poll loop missing (High)

- **Phase:** E (E.0 + E.1 + E.2 + E.3 + E.4 + E.5 — six logical sub-phases, one cohesive commit)
- **Commit:** `c44231b` — *feat(chat-bridge): Phase E — running Matrix + Telegram bridge (additive)*
- **New primary path:**
  - `mythic_vibe_cli/surfaces/chat_bridge_loop.py` (new) —
    `run_matrix_loop()` (`/sync` long-poll), `run_telegram_loop()`
    (`getUpdates`), `_Backoff`, `_is_transient_http_error`,
    `_matrix_extract_messages`, `_telegram_extract_messages`.
  - `mythic_vibe_cli/surfaces/chat_bridge.py` — `MatrixConfig` /
    `TelegramConfig` gained `from_env`, `from_file`, `from_sources`,
    `validate`, allowlist accessors. `matrix_send_message` /
    `telegram_send_message` gained `room_id` / `chat_id` keyword
    overrides additively.
  - `mythic_vibe_cli/commands.py` — `_cmd_surface_chat_run()`
    dispatched ahead of legacy scaffolding-and-exit body when the
    new `--run` flag is set.
- **Preserved legacy fallback:**
  - The original 17.4 scaffolding-and-exit body of `cmd_surface_chat`
    runs unchanged when `--run` is absent. Existing callers that
    constructed `MatrixConfig` / `TelegramConfig` with three / two
    positional args continue to work (the new fields all have safe
    defaults).
- **Closeout addendum:** `PHASE17_FINALE_CLOSEOUT.md` § *Update Notice — 2026-05-02 Phase E (additive, audit remediation **closed**)* — explicitly marks the prior caveat block as historical.
- **Side effect:** also closed finding #7 (chat_bridge HTTP coverage) via E.4's `tests/test_chat_bridge_http_client.py`.

### #3 — policy_gate iterable exhaustion (Medium)

- **Phase:** A.2
- **Commit:** `8578698` — *fix(policy): Phase A.2 — materialise iterable in evaluate() (additive)*
- **New primary path:**
  - `mythic_vibe_cli/policy/policy_gate.py:evaluate()` — single
    additive line `constraints = list(constraints)` at the top of
    the body so the list-comp at line ~85 and the `any()` check
    that follows it both see the same materialised list.
- **Preserved legacy fallback:** N/A — this was a pure bug fix on a
  single line; no fallback path exists or is needed. Original
  function logic is unchanged below the new line.
- **Verified:** `git stash`-and-test demonstrated the new regression
  test fails against the un-fixed code with the exact predicted
  symptom (`notes=[]`).
- **Closeout addendum:** `PHASE14_FINALE_CLOSEOUT.md` § *Update Notice — 2026-05-02 Phase A.2 (additive, audit remediation)*

### #4 — TUI plugin slash dispatch dead-end (Medium)

- **Phase:** C
- **Commit:** `39e0497` — *feat(tui): Phase C — in-process plugin slash dispatch (additive)*
- **New primary path:**
  - `mythic_vibe_cli/plugins/api.py` — `SlashRunResult` dataclass
    (`handled / output / exit_code / error`).
  - `mythic_vibe_cli/plugins/dispatcher.py` —
    `PluginHookDispatcher.dispatch_slash(name, args)` walks loaded
    plugins, invokes `run_slash(name, args)` via `safe_call`,
    returns first `handled=True` result.
  - `mythic_vibe_cli/runtime/slash_commands.py` —
    `SlashCommandInfo.runnable: bool = False` (additive opt-in).
  - `mythic_vibe_cli/tui/picker.py` —
    `PickerEntry.dispatch_mode` ∈ {`builtin`, `argv`, `run_slash`,
    `none`}. New `PluginSlashRunScreen` drives the in-process
    dispatch and renders the result.
- **Preserved legacy fallback:**
  - The "(plugin dispatch not yet implemented; press Esc to return.)"
    string in `tui/picker.py:CommandPreviewScreen._format_body` fires
    only for entries with `dispatch_mode == "none"` (no argv AND no
    `runnable=True` opt-in) — backward compatible.
- **Lock-in:** when a plugin opts into BOTH argv and runnable, the
  argv subprocess path wins (older contract). Test
  `test_dispatch_mode_argv_takes_priority_over_run_slash` locks this.
- **Closeout addendum:** `PHASE10_FINALE_CLOSEOUT.md` § *Update Notice — 2026-05-02 Phase C (additive, audit remediation)*

### #5 — `ai models` non-Ollama canned (Medium)

- **Phase:** D (D.1 through D.6 — one cohesive commit)
- **Commit:** `a7367c2` — *feat(ai): Phase D — ai models per-provider, fully featured (additive)*
- **New primary path:**
  - `mythic_vibe_cli/ai/providers/model_catalog.py` (new) —
    `ModelInfo`, `ModelListing`, `ProviderListingError`; static
    catalogs for Anthropic (3 models), OpenAI (4), Gemini (4),
    OpenRouter (5); per-provider `fetch_*_models_remote()` HTTP
    helpers; top-level `list_models(family, *, remote=False, api_key=None)`
    dispatcher with `static-fallback` source semantics on remote
    failure.
  - Each of `ai/providers/{anthropic,openai,gemini,openrouter}.py`
    gained a `list_models(remote=False) -> ModelListing` method
    delegating to the catalog.
  - `commands.py:cmd_ai_models` — non-Ollama branch routes through
    `provider.list_models(remote=...)`; JSON gains
    `implemented: true`, `source: "static" | "remote" | "static-fallback"`,
    `warnings: [...]`.
  - `app.py` — new `--remote` argparse flag.
- **Preserved legacy fallback:**
  - The pre-D canned `"models": [], "note": "...not implemented..."`
    payload is preserved as a defensive fallback for any future
    provider that lacks `list_models` (unreachable today; kept per
    additive-only rule).
- **ADR:** `docs/ADRS/ADR-0010-ai-model-listing-policy.md` —
  static-first-with-remote-opt-in policy + per-provider endpoint
  table.
- **Closeout addendum:** `PHASE6_FINALE_CLOSEOUT.md` § *Update Notice — 2026-05-02 Phase D (additive, audit remediation)*

### #6 — `_matches_command` dead code (Low)

- **Phase:** B
- **Commit:** `1c482be` — *feat(policy): Phase B — wire [command:<name>] tag scoping (additive)*
- **New primary path:**
  - `mythic_vibe_cli/policy/policy_gate.py` — new
    `_COMMAND_TAG_PATTERN`, `_extract_command_tags(constraint)`,
    `_constraint_applies_to_command(constraint, command)`. The
    `evaluate()` function now filters constraints through the
    new helper before computing violations.
- **Preserved legacy:**
  - `_matches_command(constraint, command)` body is unchanged
    (the legacy substring-match utility). Its docstring gained an
    additive 2026-05-02 note explaining the new path.
- **Behaviour:** untagged constraints continue to apply broadly
  (pre-Phase-B default preserved). Tagged constraints (text
  containing `[command:<name>]`) scope correctly.
- **Closeout addendum:** `PHASE14_FINALE_CLOSEOUT.md` § *Update Notice — 2026-05-02 Phase B (additive, audit remediation)*

### #7 — chat_bridge HTTP client untested (Low)

- **Phase:** F.1 (absorbed naturally into Phase E.4)
- **Commit:** `c44231b` (the same commit that closed #2; see E.4's
  test layer)
- **Coverage delivered:**
  - `tests/test_chat_bridge_http_client.py` (new, 11 tests) —
    exercises `_matrix_request`, `matrix_send_message`,
    `_telegram_request`, `telegram_send_message` via mocked
    `urllib.request.urlopen`. Asserts URL shape, headers, body,
    method. Also covers the new `room_id` / `chat_id` keyword
    overrides.
- **Closeout addendum:** captured in PHASE17 Phase E note
  (cross-references the HTTP-client test file).

### #8 — yggdrasil/mindspark `getattr` probes brittle (Low)

- **Phase:** F.2
- **Commit:** `902ac80` — *fix(islands): Phase F.2 — Yggdrasil + MindSpark documented entry points (additive)*
- **New primary path (MindSpark):**
  - `ai/providers/mindspark.py` —
    `_resolve_thoughtforge_core_class(module)` finds
    `thoughtforge.cognition.ThoughtForgeCore` (verified canonical
    against `MindSpark_ThoughtForge` HEAD on 2026-05-02). Direct
    sub-package import fallback is **gated on
    `module.__name__ == "thoughtforge"`** so test fakes cannot
    accidentally pull in the real package. `_invoke_thoughtforge`
    now returns `(text, label)`.
- **New primary path (Yggdrasil):**
  - `ai/providers/yggdrasil.py` — new `_try_import_wyrdforge()`
    companion. `__post_init__` tries `wyrdforge` (the canonical
    published WYRD package, verified against `WYRD-Protocol`'s
    pyproject.toml) first, then `yggdrasil` (legacy alias).
    `_invoke_yggdrasil` now returns `(text, label)`.
- **Preserved legacy fallbacks:**
  - Both adapters keep their original speculative probe candidate
    lists (`route` / `router.route` / `ask` for yggdrasil; `plan` /
    `cognition.plan` / `cognition.scaffold.plan` /
    `cognition.router.route` / `ask` for mindspark) as documented
    fallbacks below the primary path. Operators wrapping wyrdforge's
    class-based Oracle / TurnLoop in a top-level `route()` shim get
    caught by the first candidate.
- **Operator audit:** both providers' `response.metadata` now
  records `"entry_point": "<module>.<attr_path>"` so deployments can
  see which path fired.
- **Closeout addendum:** `PHASE9_FINALE_CLOSEOUT.md` § *Update Notice — 2026-05-02 Phase F.2 (additive, audit remediation)*

---

## In-flight non-finding work shipped during the cycle

The cycle also closed two pre-existing forward references that
weren't audit findings per se but were called out in the plan:

- **Scaffold task / interface / invariant / risk artefact types** —
  shipped at `5b89812`, *feat(scaffold)*. Originally forward-
  referenced from `cmd_scaffold`'s rejection branch as "land in
  PH-10 slice 10.4" (a phase that closed without delivering them).
  6 new tests (`ScaffoldExtendedTypesTests`).

- **Stale 76% coverage figure** in PH-10..PH-18 closeouts —
  shipped at `5c883c9`, *docs*. Live coverage was always 82% post-
  mega-day; the closeouts had carried a stale carry-over. Each
  closeout gained an additive update notice with the corrected
  figure; original prose untouched.

- **PH-10 stale "sandbox not yet wired" prose** — closeout was
  factually wrong in HEAD (sandbox IS wired at
  `plugins/dispatcher.py:31, 200`). Good-news additive correction
  added.

---

## Final metrics

| Metric | Pre-remediation | Post-remediation | Δ |
|---|---|---|---|
| Tests passed | 1700 | **1875** | **+175** |
| Tests skipped | 1 | 1 | 0 |
| Coverage (branch+line) | 82% | **82%** | held |
| Lint (ruff) | clean | **clean** | — |
| Type (mypy) | clean | **clean** | — |
| ADRs | 9 (ADR-0001..0009) | **10** (added ADR-0010) | +1 |
| Source files | 135 | **138** (+chat_bridge_loop.py, +model_catalog.py, +chat_bridge tests) | +3 prod, +5 test files |
| Documentation files | (mega-day baseline) | +`CHAT_BRIDGE_DEPLOYMENT.md` | +1 |

Coverage measurement command:
```
pytest tests/ --cov=mythic_vibe_cli --cov-report=term-missing -q
```
Result on `4af3dca` (2026-05-02): `15189 statements, 2292 missed,
4380 branches, 692 partial, 82% TOTAL`. 1875 passed, 1 skipped, 54
subtests passed.

---

## Phase-by-phase commit ledger

In commit order (oldest → newest), all on `development`:

```
5c883c9  docs: additive 2026-05-02 update notices on PH-10..PH-18 closeouts
5b89812  feat(scaffold): add task/interface/invariant/risk artefact types (additive)
76d3130  docs: add 2026-05-02 audit reports (fake/temp + pseudo-code)
3186b94  task: open audit remediation plan (7 phases A..G)
6f60e57  fix(voice): Phase A.1 — Chatterbox modern-API adapter (additive)
8578698  fix(policy): Phase A.2 — materialise iterable in evaluate() (additive)
e74c3b5  task: mark Phase A closed in remediation plan (additive)
1c482be  feat(policy): Phase B — wire [command:<name>] tag scoping (additive)
59777f4  task: mark Phase B closed in remediation plan (additive)
d0e4aff  task: lock Phase D + E scope (fully featured) per Volmarr's call
39e0497  feat(tui): Phase C — in-process plugin slash dispatch (additive)
9ab157f  task: mark Phase C closed in remediation plan (additive)
a7367c2  feat(ai): Phase D — ai models per-provider, fully featured (additive)
99487f9  task: mark Phase D closed in remediation plan (additive)
c44231b  feat(chat-bridge): Phase E — running Matrix + Telegram bridge (additive)
c8faf11  task: mark Phase E closed in remediation plan (additive)
902ac80  fix(islands): Phase F.2 — Yggdrasil + MindSpark documented entry points (additive)
4af3dca  task+docs: mark Phase F.2 closed, add PH-09 closeout addendum (additive)
[Phase G]  task+docs: write AUDIT_REMEDIATION_CLOSEOUT_2026-05-02 (this memo)
```

(Two unrelated Codex research-plan merges — `7940957` cross-platform
plan and `718ccaf` improvement plan — landed mid-session at the
remote and were rebased over cleanly. They are not part of this
remediation cycle.)

---

## Closeout discipline summary

Every phase that touched closed-phase territory dropped an additive
`Update Notice` block at the end of the corresponding closeout.
Original prose was preserved character-for-character per the
additive-only rule; corrections layered as dated addenda.

| Phase | Closeout file | Addendum date |
|---|---|---|
| Pre-cycle docs sweep | PH-10..PH-18 closeouts | 2026-05-02 |
| Phase A.1 | PHASE7_FINALE_CLOSEOUT.md | 2026-05-02 |
| Phase A.2 + Phase B | PHASE14_FINALE_CLOSEOUT.md | 2026-05-02 |
| Phase C | PHASE10_FINALE_CLOSEOUT.md | 2026-05-02 |
| Phase D | PHASE6_FINALE_CLOSEOUT.md | 2026-05-02 |
| Phase E | PHASE17_FINALE_CLOSEOUT.md (caveat marked **historical**) | 2026-05-02 |
| Phase F.2 | PHASE9_FINALE_CLOSEOUT.md | 2026-05-02 |

---

## What's next

This remediation cycle is **complete**. Mythic Vibe CLI continues at
**18 of 20 master-roadmap phases closed (90%)**. Remaining roadmap
work, unrelated to this cycle:

- **PH-19** — Distribution (pip / brew / scoop / aur / winget)
- **PH-20** — v1.0.0 — Sovereign OS Launch

The Codex research plans that landed mid-session (`7940957`,
`718ccaf`) are independent strategic-planning artefacts and do not
affect the master roadmap structure.

---

## Operational rule reaffirmed

The session validated the durable rule recorded in
`feedback_additive_only.md` (2026-05-02):

> **Additive-only fixes — never subtractive.** When fixing code,
> docs, or status files, add corrections / wrappers / addenda;
> never delete or overwrite the original. Preserves history and
> avoids losing context.

Every preserved fallback, every dated update notice, every old
function whose body remained untouched after a new primary path
was added — these are the rule's footprints in this codebase.

---

`STATUS: AUDIT REMEDIATION CYCLE — CLOSED 2026-05-02.`

— *Volmarr Wyrd & Runa Gridweaver Freyjasdottir, 2026-05-02*
