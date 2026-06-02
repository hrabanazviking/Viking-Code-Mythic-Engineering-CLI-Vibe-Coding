# Mythic Vibe CLI — Pseudo-Code Deep Audit (Second Pass)
Date: 2026-05-02
HEAD: e0953b6
Branch: development
Auditor: Sólrún Hvítmynd (second pass)
Environment: Python 3.10, Windows 11, project root C:/Users/volma/runa/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
First-pass report: AUDIT_FAKE_TEMP_CODE_2026-05-02.md

Commands run during this audit:
- Full file reads: all modules in `mythic_vibe_cli/ai/providers/`, `surfaces/`, `forge_verifier.py`, `policy/`, `security/`, `robustness/`, `drift.py`, `voice/`, `protocols/`, `context/`, `plugins/`, `ux.py`, `ai/router.py`, `ai/cost_guard.py`
- `python -c "..." ` — generator exhaustion verification (policy_gate.evaluate)
- `python -c "..." ` — chatterbox API surface check (chatterbox.__init__ + tts.py)
- `python -c "..." ` — _matches_command dead-code confirmation (ast.walk)
- `python -c "..." ` — zsh_completion parsing verification
- `python -c "..." ` — evaluate_for_root list-vs-generator type check

---

## Verdict

The project is **substantially clean** at the pseudo-code level. The four AI cloud providers (Anthropic, OpenAI, Gemini, OpenRouter) make real urllib network calls; `forge_verifier.py`'s three gate runners consult real state; `drift.py`'s detectors walk real filesystem and AST trees; `simulate.py`'s four scenarios inject real failure conditions against live CLI handlers; `policy/constraint_store.py` genuinely reads `mythic/oaths.md`, `mythic/constraints.md`, and `docs/ADRS/*.md`; `security/secret_scanner.py` uses real regex patterns against real file content. The robustness audit modules (`boundary_audit.py`, `path_audit.py`, `api_audit.py`) walk real ASTs. The knowledge graph, cost guard, and routing table all perform real computation.

**Three genuine pseudo-code findings are present** that the first pass missed. The most significant is a real functional bug: `ChatterboxEngine.say()` looks for a module-level `chatterbox.speak()` function that does not exist in the actual chatterbox package — the backend silently reports `spoken=False` every time with a misleading error string, meaning the Chatterbox TTS feature has never worked. The second finding is a latent generator-exhaustion bug in `policy_gate.evaluate()` that silently suppresses advisory notes when callers pass a generator. The third is a dead private function (`_matches_command`) that is defined, documented, but never called — the policy gate's command-scoping design is absent despite the function existing to support it.

---

## Severity Summary

| Severity | Count | Description |
|---|---|---|
| High | 1 | ChatterboxEngine.say() looks for a non-existent API entry point; backend is always non-functional when the real package is installed |
| Medium | 1 | policy_gate.evaluate() exhausts its Iterable input before calling any(constraints); advisory notes are silently dropped when callers pass generators |
| Low | 2 | _matches_command is a dead private function (defined, never called); Yggdrasil/MindSpark island adapters use the same speculative getattr-probe pattern as Chatterbox but are properly labeled as provisional |

**Total second-pass findings: 4** (first audit found 9 items; this pass adds 4 new ones not found by the first pass)

---

## Findings (grouped by category from the menu)

---

### Category: Optional-dep backend that always fails silently (Category 4 + Category 12)

**[High]** `mythic_vibe_cli/voice/tts.py:171–202` — `ChatterboxEngine.say()`

**Claim:** `ChatterboxEngine` is a working TTS backend that emits audio via the open-source chatterbox package. The `TTSResult.spoken` field is documented as `True` only when audio is actually emitted.

**Reality:** The method looks for `chatterbox.speak` — a bare module-level function:

```python
speak = getattr(self._module, "speak", None)
if callable(speak):
    speak(request.text, voice=...)
    return TTSResult(text=..., engine=self.name, spoken=True, ...)
return TTSResult(
    text=request.text,
    engine=self.name,
    spoken=False,
    error="chatterbox.speak not callable in installed version",
)
```

The actual chatterbox package (`chatterbox/src/chatterbox/__init__.py`, confirmed by reading its source) exports `ChatterboxTTS`, `ChatterboxVC`, and `ChatterboxMultilingualTTS` — zero module-level `speak()` function. The package's real API surface (`tts.py` functions: `ChatterboxTTS.generate()`, `ChatterboxTTS.from_pretrained()`) has no callable named `speak`.

**Verified by:**
```
python -c "
import pathlib, ast
content = pathlib.Path('chatterbox/src/chatterbox/__init__.py').read_text(encoding='utf-8', errors='replace')
# Exports: ChatterboxTTS, ChatterboxVC, ChatterboxMultilingualTTS
# No speak function.
tts_content = pathlib.Path('chatterbox/src/chatterbox/tts.py').read_text(encoding='utf-8', errors='replace')
tree = ast.parse(tts_content)
funcs = [n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
# funcs = ['punc_norm', 'to', 'save', 'load', '__init__', 'from_local', 'from_pretrained',
#           'prepare_conditionals', 'generate']   — no 'speak'
"
```

**Consequence:** When `MYTHIC_VOICE_TTS_ENABLED=1` AND `MYTHIC_ISLAND_CHATTERBOX_ENABLED=1` AND the chatterbox package is installed, every call to `voice say --engine chatterbox` returns `spoken=False` with `error="chatterbox.speak not callable in installed version"`. The feature appears shipped ("Chatterbox engine — try-imports at construction time"); it has never been able to produce audio. The `__post_init__` guard (`import chatterbox`) passes because the package is importable; only `say()` fails.

**Callers:** `voice/tts.py:209` (`make_tts_engine("chatterbox")` → `ChatterboxEngine()`), `commands.py` `cmd_voice_say` path.

**Recommendation:** Replace `getattr(self._module, "speak", None)` with the actual API: instantiate `chatterbox.ChatterboxTTS` via `from_pretrained()` and call `.generate(text, audio_prompt_path=None)`. Alternatively, document that ChatterboxEngine is a mapping stub pending API research, and display a clear operator message rather than the misleading error string.

---

### Category: Phantom function / dead code that implies a feature (Category 7 + Category 10)

**[Medium]** `mythic_vibe_cli/policy/policy_gate.py:57–67` — `_matches_command()` defined, never called

**Claim (docstring):** "a constraint applies to a command when the command name appears in the constraint text… Tag a constraint with ``[command:<name>]`` to scope it to a specific command."

**Reality:** The function exists at line 57 but is called zero times in the entire codebase:

```python
def _matches_command(constraint: Constraint, command: str) -> bool:
    """Heuristic match: a constraint applies to a command when
    the command name appears in the constraint text…"""
    return command.lower() in constraint.text.lower()
```

The `evaluate()` function at line 85 extracts violations with:
```python
violations = [
    c for c in constraints if c.severity == SEVERITY_BLOCKING
]
```
It never calls `_matches_command`. Every blocking constraint is a violation regardless of which command is running. The function implies per-command scoping is active; it is not.

**Verified by:**
```python
import ast, pathlib
src = pathlib.Path('mythic_vibe_cli/policy/policy_gate.py').read_text()
tree = ast.parse(src)
calls = [n.lineno for n in ast.walk(tree)
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
         and n.func.id == '_matches_command']
# calls = []  — zero calls
```

**Consequence:** Per-command policy scoping is implied by the code's structure but not wired. Any blocking constraint blocks ALL write commands, not just the one it was written for. This is documented in `evaluate()`'s docstring ("Today's matching rule is broad") — so it's not hidden — but the existence of `_matches_command` makes it look like the feature is implemented.

**Recommendation:** Either wire `_matches_command` into `evaluate()`'s violation filter, or remove the function and update the docstring to remove the forward reference to `[command:<name>]` tagging.

---

### Category: Iterator exhaustion producing silent wrong result (Category 6 / latent bug)

**[Medium]** `mythic_vibe_cli/policy/policy_gate.py:85–90` — `evaluate()` exhausts `Iterable[Constraint]` before calling `any()`

**Claim:** The function's type hint is `constraints: Iterable[Constraint]`, which promises generator support. The note logic at line 90 says: if there are no blocking violations but there ARE constraints of other kinds, append an advisory note.

**Reality:**

```python
violations = [
    c for c in constraints if c.severity == SEVERITY_BLOCKING   # ← exhausts the iterator
]
requires_override = bool(violations)
notes: list[str] = []
if not violations and any(constraints):     # ← constraints is now empty if it was a generator
    notes.append(...)
```

When `constraints` is a generator or any single-pass iterable, the list comprehension at line 85 fully consumes it. The `any(constraints)` call at line 90 iterates an exhausted generator and always returns `False`, silently dropping the advisory note.

**Verified by:**
```
python -c "
from mythic_vibe_cli.policy.constraint_store import Constraint, SEVERITY_WARN
from mythic_vibe_cli.policy.policy_gate import evaluate

def gen_constraints():
    yield Constraint(id='r1', kind='rule', text='be nice', severity=SEVERITY_WARN)
    yield Constraint(id='r2', kind='rule', text='be brave', severity='advisory')

decision = evaluate(gen_constraints(), action='write', command='oath')
print('Generator input: notes =', decision.notes)
# Output: Generator input: notes = []  ← advisory note silently dropped

# With a list (the actual call-site form):
decision2 = evaluate(list(gen_constraints()), action='write', command='oath')
print('List input: notes =', decision2.notes)
# Output: List input: notes = ['action=... no blocking violations ...']
"
```

**Current callers:** All production callers go through `evaluate_for_root()` which passes `result.constraints` — a `list`, not a generator. The bug does not affect production code today. But the public API (`evaluate` is in `__all__`) promises `Iterable` support, making this a latent contract violation. Direct callers or future refactors passing generators will hit it silently.

**Recommendation:** Materialise the input at the top of `evaluate()`:
```python
constraint_list = list(constraints)
violations = [c for c in constraint_list if c.severity == SEVERITY_BLOCKING]
...
if not violations and constraint_list:
```

---

### Category: Speculative getattr-probe adapters (Category 4 + Category 12 — lower severity)

**[Low]** `mythic_vibe_cli/ai/providers/yggdrasil.py:169–185` and `ai/providers/mindspark.py:154–179` — `_invoke_yggdrasil()` / `_invoke_thoughtforge()` probe for speculative function names

Both island adapters use a `getattr`-probe loop to find the external package's entry point:

```python
for attr_path in ("route", "router.route", "ask"):
    target = module
    for piece in attr_path.split("."):
        target = getattr(target, piece, None)
        if target is None:
            break
    if callable(target):
        return str(target(prompt))
raise AttributeError("package does not expose a known entry point ...")
```

This is the same structural pattern as `ChatterboxEngine.say()`. Unlike Chatterbox, neither `yggdrasil` nor `thoughtforge` is vendored in the repo, so the actual API cannot be verified in this audit. Both adapters raise `AttributeError` (not silently succeed) when no probe hits — that error is caught and written to `metadata["error"]` by the caller, so the failure is surfaced rather than swallowed. Severity is low because the feature flag gates and unconfigured-path handling are honest.

**Distinction from ChatterboxEngine:** ChatterboxEngine returns `spoken=False, error="not callable"` and looks like a normal degraded result. The island adapters return a structured error payload. The Chatterbox case is higher severity because it actively misleads callers about what happened.

**Recommendation:** When the actual `yggdrasil` and `thoughtforge` packages are stable, replace the probe loops with direct imports of the known entry points and add tests that mock those specific call signatures.

---

## Cross-references with first audit

**Items the first audit caught (not re-raised here):**
- High: chat-bridge poll loop entirely absent (`surface chat` exits with a scaffolding notice)
- Medium: coverage metric stale (76% in closeouts vs 82% live)
- Medium: `ai models` returns "not implemented" for non-Ollama providers
- Medium: `scaffold` supports only `adr`
- Medium: plugin TUI dispatch "not yet implemented" in picker
- Low: cicd TODO markers are user-facing scaffold templates
- Low: sandbox wiring note in PH-10 closeout is stale
- Low: single POSIX-only test skip
- Low: `_matrix_request` / `_telegram_request` untested by test suite

**Items the first audit MISSED that this pass found:**
1. **[High]** `voice/tts.py:181` — `ChatterboxEngine.say()` probes for `chatterbox.speak` which does not exist; backend always returns `spoken=False` when the real package is installed.
2. **[Medium]** `policy/policy_gate.py:85–90` — generator exhaustion: `any(constraints)` always returns `False` after the list comprehension at line 85 has consumed the iterator. Advisory notes are silently dropped for generator inputs.
3. **[Low]** `policy/policy_gate.py:57–67` — `_matches_command()` is defined, exported by docstring implication, but never called; per-command policy scoping is absent despite the function existing.
4. **[Low]** `ai/providers/yggdrasil.py:169–185`, `ai/providers/mindspark.py:154–179` — speculative `getattr`-probe loops for unknown external package APIs; same structural risk as ChatterboxEngine but lower severity due to honest error surfacing.

**Items both passes confirm clean:**
- `ai/providers/anthropic.py`, `openai.py`, `gemini.py`, `openrouter.py` — all four make real urllib network calls with correct API payloads. The `run()` methods are genuine implementations.
- `forge_verifier.py` gates — `gate_diff_reviewed`, `gate_no_invariant_violation`, `gate_test_evidence_recorded` — all consult real state (git diff, invariant checker, latest verification file). None returns a canned pass.
- `policy/constraint_store.py` — genuinely reads and parses `mythic/oaths.md`, `mythic/constraints.md`, and `docs/ADRS/*.md` with correct section extraction.
- `policy/policy_gate.py:enforce_policy()` — genuinely blocks when blocking constraints exist and no override is supplied.
- `robustness/simulate.py` — four scenarios inject real failure conditions (malformed JSON, missing artefact, unconfigured provider, blocking constraint) and exercise live CLI handlers.
- `drift.py` — three detectors walk real filesystem and AST trees; `detect_orphaned_modules` is a real graph query gated on file existence.
- `security/secret_scanner.py` — applies real regex patterns to real file content; tests verify actual secret strings are caught.
- `security/redaction.py` — real recursive redaction with the same pattern set.
- `plugins/sandbox.py` — `safe_call()` is a real thread-based sandbox with genuine timeout enforcement. `probe_resource_caps()` correctly documents its advisory-only status on Windows.
- `protocols/mcp_client.py` — real JSON-RPC over subprocess pipes with real id-matching and error handling.
- `protocols/acp_bridge.py` — real stdio JSON-RPC server with genuine cancellation event set (best-effort, as disclosed).
- `protocols/otel.py` — honest try-import with a zero-cost no-op path when SDK is absent.
- `context/graph.py` — real SQLite CRUD operations; `GraphStore` is a genuine implementation.
- `context/retriever.py:rank_entities()` — real tag-overlap + neighbour-expansion scoring with deterministic sort; not a canned return.
- `ai/router.py:route()` — real predicate walk over ordered routing rules with hardware-floor checks.
- `ai/cost_guard.py:compute_today_spend_usd()` — real ledger-file parse summing today's UTC entries.
- `voice/transcribe.py:WhisperTranscriber` — real `whisper.load_model().transcribe()` invocation; the stub is correctly labeled.
- `drift.py:detect_orphaned_modules()` — real graph query, not a hardcoded empty list; correctly no-ops when graph file is absent.

---

## Recommendations (prioritized)

1. **[High — ChatterboxEngine]** Replace `getattr(self._module, "speak", None)` with the actual chatterbox API. The library's entry point is `ChatterboxTTS.from_pretrained(device).generate(text, audio_prompt_path=None)` — a class instantiation + method call, not a module-level `speak()`. Until the fix lands, add a clear operator message: "ChatterboxTTS requires explicit API wiring; see ISSUE-XXX." Do not silently return `spoken=False, error="not callable"` as if it is a version mismatch.

2. **[Medium — generator exhaustion]** In `policy_gate.evaluate()`, materialise the input at function entry:
   ```python
   constraint_list = list(constraints)
   violations = [c for c in constraint_list if c.severity == SEVERITY_BLOCKING]
   ...
   if not violations and constraint_list:
       notes.append(...)
   ```
   This makes the function safe for all `Iterable` inputs as advertised by the type hint.

3. **[Low — dead _matches_command]** Either wire `_matches_command` into `evaluate()`'s filter:
   ```python
   violations = [
       c for c in constraint_list
       if c.severity == SEVERITY_BLOCKING and _matches_command(c, command)
   ]
   ```
   or remove the function, remove the `[command:<name>]` tagging forward-reference from the docstring, and document that per-command scoping is a planned feature.

4. **[Low — island adapter API probing]** When `yggdrasil` and `thoughtforge` APIs stabilise, replace speculative `getattr` probe loops with direct named imports and add integration test stubs that mock the specific function signatures the adapters expect.
