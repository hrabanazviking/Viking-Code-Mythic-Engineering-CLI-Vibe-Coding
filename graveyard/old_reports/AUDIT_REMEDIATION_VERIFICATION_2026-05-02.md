# Mythic Vibe CLI — Phase G Audit Re-run / Remediation Verification

**Date:** 2026-05-02  
**HEAD verified:** `4af3dca8081599634efd5d34a4ed45f22b4e8439`  
**Branch:** `development`  
**Auditor:** Sólrún Hvítmynd (Phase G re-run)  
**Environment:** Windows 11 22621, Python (project venv), PowerShell  
**Commands run:**
```
git log --oneline -15
git rev-parse HEAD
pytest tests/ --cov=mythic_vibe_cli --cov-report=term-missing -q --tb=no
python -m ruff check mythic_vibe_cli/ tests/
python -m mypy mythic_vibe_cli/ --ignore-missing-imports
```

---

## Verdict

The 2026-05-02 remediation cycle is **structurally clean**. All 8 findings from the prior
two audits (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md` and `AUDIT_PSEUDOCODE_DEEP_2026-05-02.md`)
are verified closed in HEAD `4af3dca`. Every legacy fallback path cited in the operating
constraint is present and intact. No new stubs, pseudo-code, TODOs, or regressions were
introduced by the remediation work. Quality gates pass unconditionally: 1875 tests pass,
82% coverage, ruff clean, mypy clean across 138 source files.

---

## Each-finding verification (1..8)

### Finding #1 — High | ChatterboxEngine.say() mapping

| Field | Detail |
|---|---|
| Closing commit | `6f60e57` |
| New code path | `mythic_vibe_cli/voice/tts.py:205-220` — `_resolve_modern_tts_cls()` walks `_MODERN_CLASS_CANDIDATES` tuple for `ChatterboxTTS`/`ChatterboxMultilingualTTS` via `from_pretrained`; `tts.py:265-405` — `_say_via_modern()` drives `from_pretrained` → `generate` → `torchaudio.save` pipeline |
| Legacy fallback | `tts.py:380-405` — `getattr(self._module, "speak", None)` probe block retained verbatim; fires only when `_resolve_modern_tts_cls()` returns `None` |
| Closeout addendum | `PHASE7_FINALE_CLOSEOUT.md` — "Update Notice — 2026-05-02 (additive, Phase A.1 of audit remediation)" present at line 206 |
| **Status** | **PASS** |

### Finding #2 — High | chat_bridge poll loop missing

| Field | Detail |
|---|---|
| Closing commit | `c44231b` |
| New code path | `mythic_vibe_cli/surfaces/chat_bridge_loop.py:179-270` — `run_matrix_loop()` (allowlist, echo prevention, exponential backoff, `stop_event`); `chat_bridge_loop.py:351-441` — `run_telegram_loop()` (same contract, `getUpdates`); `commands.py:3314` — `if bool(_flag(args, "run")): return _cmd_surface_chat_run(args, backend)` branch before legacy exit |
| Legacy fallback | `commands.py:3317-3338` — original scaffolding-and-exit body remains; only reached when `--run` is absent |
| Closeout addendum | `PHASE17_FINALE_CLOSEOUT.md` — "Update Notice — 2026-05-02 Phase E (additive, audit remediation **closed**)" present at line 159 |
| **Status** | **PASS** |

### Finding #3 — Medium | policy_gate iterable exhaustion

| Field | Detail |
|---|---|
| Closing commit | `8578698` |
| New code path | `mythic_vibe_cli/policy/policy_gate.py:151` — `constraints = list(constraints)` at top of `evaluate()` body, with dated audit-remediation comment; both the list-comp and `any(scoped_constraints)` at line 171 operate on the materialised list |
| Legacy fallback | N/A (one-line materialisation; no prior logic removed) |
| Closeout addendum | `PHASE14_FINALE_CLOSEOUT.md` — "Update Notice — 2026-05-02 Phase A.2 (additive, audit remediation)" present at line 160 |
| **Status** | **PASS** |

### Finding #4 — Medium | TUI plugin slash dispatch

| Field | Detail |
|---|---|
| Closing commit | `39e0497` |
| New code path | `mythic_vibe_cli/tui/picker.py:258-383` — `PluginSlashRunScreen` class (in-process plugin dispatch); `picker.py:86-99` — `PickerEntry.dispatch_mode` property returns `"run_slash"` when `self.runnable` is True; `picker.py:223-227` — `action_run_command` routes to `PluginSlashRunScreen` when `mode == "run_slash"` |
| Legacy fallback | `picker.py:199-205` — `"(plugin dispatch not yet implemented; press Esc to return.)"` string remains as the final `else` branch in `_format_body()` for plugins that opted into neither argv nor `runnable=True` |
| Closeout addendum | `PHASE10_FINALE_CLOSEOUT.md` — "Update Notice — 2026-05-02 Phase C (additive, audit remediation)" present at line 169 |
| **Status** | **PASS** |

### Finding #5 — Medium | ai models non-Ollama canned

| Field | Detail |
|---|---|
| Closing commit | `a7367c2` |
| New code path | `mythic_vibe_cli/ai/providers/model_catalog.py` — `ModelInfo`, `ModelListing`, `ProviderListingError`, static catalogs for Anthropic/OpenAI/Gemini/OpenRouter, per-provider remote fetchers, `list_models()` dispatcher; `commands.py:5643-5701` — `list_models_method = getattr(provider, "list_models", None)` call ahead of legacy fallback |
| Legacy fallback | `commands.py:5704-5730` — legacy "not implemented" canned payload block preserved; only reached if a provider lacks a `list_models` method (no current provider does, per plan note) |
| Closeout addendum | `PHASE6_FINALE_CLOSEOUT.md` — "Update Notice — 2026-05-02 Phase D (additive, audit remediation)" present at line 212 |
| **Status** | **PASS** |

### Finding #6 — Low | `_matches_command` dead code

| Field | Detail |
|---|---|
| Closing commit | `1c482be` |
| New code path | `mythic_vibe_cli/policy/policy_gate.py:89-103` — `_extract_command_tags()` parses `[command:<name>]` markers; `policy_gate.py:106-125` — `_constraint_applies_to_command()` uses extracted tags for scoping; `evaluate()` at line 162-164 filters constraints through the new helper |
| Legacy fallback | `policy_gate.py:66-86` — `_matches_command()` body preserved verbatim; docstring at line 79-84 explicitly records the additive preservation rationale |
| Closeout addendum | `PHASE14_FINALE_CLOSEOUT.md` — "Update Notice — 2026-05-02 Phase B (additive, audit remediation)" present at line 196 |
| **Status** | **PASS** |

### Finding #7 — Low | chat_bridge HTTP coverage

| Field | Detail |
|---|---|
| Closing commit | `c44231b` (Phase E.4, absorbed F.1) |
| New code path | `tests/test_chat_bridge_http_client.py` — 275 lines; `MatrixRequestTests` (3 tests: GET query string, PUT JSON body, empty response), `MatrixSendMessageTests` (3 tests: default room_id, room_id override, missing room_id raises), `TelegramRequestTests` (2 tests: POST body, empty body), `TelegramSendMessageTests` (3 tests: default chat_id, chat_id override, missing chat_id raises). 11 tests total covering the 4 previously-untested functions |
| Legacy fallback | N/A (test file is additive; no prior test was removed) |
| Closeout addendum | `PHASE17_FINALE_CLOSEOUT.md` — Phase E closeout addendum at line 159 explicitly records "E.4 Tests (3 new files, 80 net new tests)" including `test_chat_bridge_http_client.py` |
| **Status** | **PASS** |

### Finding #8 — Low | yggdrasil/mindspark getattr probes

| Field | Detail |
|---|---|
| Closing commit | `902ac80` |
| New code path (yggdrasil) | `mythic_vibe_cli/ai/providers/yggdrasil.py:71-79` — `_try_import_wyrdforge()` for canonical WYRD package; `yggdrasil.py:102` — `__post_init__` tries wyrdforge first, falls to yggdrasil; `yggdrasil.py:209-260` — `_invoke_yggdrasil()` returns `(str, str)` tuple with `entry_point_label`; metadata carries which entry point fired (`yggdrasil.py:204`) |
| New code path (mindspark) | `mythic_vibe_cli/ai/providers/mindspark.py:224-255` — `_resolve_thoughtforge_core_class()` locates `ThoughtForgeCore` via `cognition` sub-package; `mindspark.py:161-221` — `_invoke_thoughtforge()` tries documented primary path first, then legacy probe loop as fallback; returns `(str, str)` tuple |
| Legacy fallback | `yggdrasil.py:240-259` — original `("route", "router.route", "ask")` candidate loop preserved as fallback; `mindspark.py:202-216` — original `("plan", "cognition.plan", "cognition.scaffold.plan", "cognition.router.route", "ask")` probe loop preserved |
| Closeout addendum | `PHASE9_FINALE_CLOSEOUT.md` — "Update Notice — 2026-05-02 Phase F.2 (additive, audit remediation)" present at line 155 |
| **Status** | **PASS** |

---

## New-findings sweep

Scope: all 5 files authored or materially changed by the remediation cycle
(`voice/tts.py`, `surfaces/chat_bridge_loop.py`, `policy/policy_gate.py`,
`tui/picker.py`, `ai/providers/model_catalog.py`, `ai/providers/yggdrasil.py`,
`ai/providers/mindspark.py`, `tests/test_chat_bridge_http_client.py`).

Patterns searched: `TODO`, `FIXME`, `HACK`, `XXX`, `not yet implemented`,
`pseudo.?code`, `placeholder`, `raise NotImplementedError`, bare `pass`.

**Result: no new findings.** All occurrences were:
- Contextual documentation strings (e.g. `yggdrasil.py:146` — "placeholder +
  an error string" in prose description, not code path).
- The two legacy "not yet implemented" strings correctly preserved as
  intentional fallbacks: `picker.py:203` and `commands.py:5717`.
- The `tts.py:181` reference to "The pseudo-code audit … finding #1" in a
  comment — historical traceability, not a stub.
- The cicd scaffold `TODO` strings excluded per plan's acknowledged-and-leave
  list.

No severity-classified new findings. Sweep is clean.

---

## Quality gates

| Gate | Command | Result |
|---|---|---|
| **pytest** | `pytest tests/ --cov=mythic_vibe_cli --cov-report=term-missing -q --tb=no` | **1875 passed, 1 skipped, 54 subtests passed** in 116.33s |
| **Coverage** | Same run, `TOTAL` line | **82%** (15,189 statements, 2,292 missed) |
| **ruff** | `python -m ruff check mythic_vibe_cli/ tests/` | **All checks passed** (0 issues) |
| **mypy** | `python -m mypy mythic_vibe_cli/ --ignore-missing-imports` | **Success: no issues found in 138 source files** |

Plan claimed: 1875 tests, ≥82% coverage. Actual: 1875 passed, 82%. **Exact match.**

---

## Closeout discipline check

Each phase's addendum was verified present in the correct closeout file:

| Phase | Finding(s) | Addendum file | Verified |
|---|---|---|---|
| A.1 | #1 | `PHASE7_FINALE_CLOSEOUT.md` line 206 | Yes |
| A.2 | #3 | `PHASE14_FINALE_CLOSEOUT.md` line 160 | Yes |
| B | #6 | `PHASE14_FINALE_CLOSEOUT.md` line 196 | Yes |
| C | #4 | `PHASE10_FINALE_CLOSEOUT.md` line 169 | Yes |
| D | #5 | `PHASE6_FINALE_CLOSEOUT.md` line 212 | Yes |
| E | #2, #7 | `PHASE17_FINALE_CLOSEOUT.md` line 159 | Yes |
| F.2 | #8 | `PHASE9_FINALE_CLOSEOUT.md` line 155 | Yes |

All 7 addendums present. Discipline: intact.

---

## Recommendations

None. The cycle is complete and clean.

One minor observation for future reference (severity: **nit**, no action required):
`mindspark.py:_resolve_thoughtforge_core_class` is not listed in `__all__`
(`mindspark.py:258-263`), whereas `yggdrasil.py:_try_import_wyrdforge` is exported
(`yggdrasil.py:267-270`). The asymmetry is harmless — `_resolve_thoughtforge_core_class`
is called internally only; however, making it testable directly (as the yggdrasil
counterparts are) would be marginally cleaner. This is an observation, not a finding.

---

*Sólrún Hvítmynd — Phase G verification complete.*
