# TASK — Wire Pi-Plundered Safety Primitives into Existing Surfaces

**Opened:** 2026-04-29
**Owner:** Runa
**Predecessor slices:** `549c8a1` (file-mutation-queue) + `0ae9d54` (output-guard).

---

## Why this slice now

The two pi primitives we just landed are plumbing nobody calls. They become real safety only when wired into existing entry points. The wiring is the value-per-line slice the DEVLOG continuity thread named:

> *"The natural next slice wires both `take_over_stdout()` and `file_mutation_queue` into the existing `--json` and `--dry-run` entry points so JSON output stays clean even when noisy libraries import or print during command execution."*

## Two halves

### Half A — Output guard on every `--json` command

**Goal:** when any command runs with `--json`, only the deliberate JSON payload may land on real stdout. Accidental `print()`, third-party library output, deprecation warnings, and anything else writing to `sys.stdout` is structurally redirected to `sys.stderr`.

**Mechanism:**

1. `app.main()` detects `getattr(args, "json", False)`. If set, calls `take_over_stdout()` before the handler and `restore_stdout()` in a `finally` block.
2. `output.py:write_json()` is updated to use `write_raw_stdout()` instead of `write_line(..., force=True)`. This bypasses the takeover for the *intentional* JSON path so JSON lands on real stdout. Everything else (`write_line`, accidental `print`, library noise) routes to stderr.
3. Existing tests that capture stdout via `redirect_stdout(StringIO)` still work: the guard captures the redirected StringIO as the "original stdout" and `write_raw_stdout()` writes to it.

### Half B — Mutation queue on every file write

**Goal:** when two commands try to write the same file at the same time, the queue serializes them so the second waits for the first. Today our writers don't have concurrent-write protection.

**Mechanism:**

Wrap every `Path.write_text(...)` site that touches a project-controlled artifact with `with file_mutation_queue(target):`. Three obvious surfaces:

- `codex_bridge.PacketBuilder._write_record` and `_write_ingested_record` (writes packets to disk)
- `codex_bridge.PacketBuilder._write_context_manifest` (writes context manifest)
- Any future workflow runner write (deferred — not part of this slice; queue is ready when needed)

Half B is bounded — we only wire the queue into surfaces that already exist. New surfaces from Pi or elsewhere wire themselves when they land.

## Out of scope

- Wiring the queue into `init`, `import-md`, or other one-shot scaffolders that are inherently single-writer
- Wiring the guard into non-`--json` commands (it would route human progress to stderr — wrong contract)
- Adding subprocess integration tests à la pi's `stdout-cleanliness.test.ts` — out of scope; unit-level verification is enough
- Touching the workflow runner itself (still always-blocked behind `--dry-run`)

## Files to Touch

| File | Change |
|---|---|
| `mythic_vibe_cli/runtime/output_guard.py` | Add `json_output_guard` context manager (small additive helper) |
| `mythic_vibe_cli/runtime/__init__.py` | Re-export the new helper |
| `mythic_vibe_cli/app.py` | Wire `json_output_guard(args.json)` around the handler call |
| `mythic_vibe_cli/output.py` | `write_json` uses `write_raw_stdout` |
| `mythic_vibe_cli/codex_bridge.py` | Wrap writer sites with `file_mutation_queue` |
| `tests/test_output_guard.py` | Test the new context manager |
| `tests/test_cli_kernel.py` | Add a JSON-cleanliness test (incidental print does not pollute) |
| `tests/test_config_and_bridge.py` or new file | Verify packet writer concurrency behavior |
| `CHANGELOG.md` | Unreleased entry |
| `DEVLOG.md` | New 2026-04-29 entry |

## Progress Tracker

- [x] Task file written
- [x] Task file committed + pushed
- [ ] Add `json_output_guard` context manager to `output_guard.py`
- [ ] Re-export from `runtime/__init__.py`
- [ ] Wire into `app.main()`
- [ ] Update `output.py:write_json`
- [ ] Wrap packet writer sites with `file_mutation_queue`
- [ ] New JSON-cleanliness test passes
- [ ] New packet writer concurrency test passes
- [ ] All existing tests still pass
- [ ] `ruff` + `mypy` green
- [ ] CHANGELOG entry
- [ ] DEVLOG entry
- [ ] Memory snapshot updated
- [ ] Final commit + push

## Resume Instructions

1. Read this file for full task scope.
2. Half A first (smaller blast radius). Half B second.
3. After Half A: run full test suite. If any `--json` test fails, the failure is signal — investigate before moving on.
4. The JSON-cleanliness test should deliberately introduce a `print()` from an injected handler (or via a stub `cmd_*` function) and verify the captured stdout is parseable JSON.
5. The mutation-queue concurrency test should fork two threads writing the same packet file and verify both writes complete cleanly without interleaving.
