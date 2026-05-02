# PH-10 — Phase Finale Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `ae9e4f5` (this memo will land the next commit)
**Resume from:** `d189344` (PH-09 finale)

PH-10 matures the plugin layer from "hooks fire" to a real
ecosystem with discovery, isolation, sandboxing, a plugin
registry, an authoring guide, and a community contribution
workflow. All 7 slices closed in order; working tree clean,
every commit pushed, every existing test still passes.

---

## What landed

| Slice | Title | Commit | Net |
|---|---|---|---|
| TASK file | — | `4ddf274` | +209 lines |
| 10.1 | Entry-point discovery + `plugin install` | `d1107e5` | +672 lines, +24 tests |
| 10.2 | Plugin sandbox layer | `0bec1aa` | +481 lines, +25 tests (1 skipped on Windows) |
| 10.3 | Extension-point Protocols | `598af55` | +318 lines, +12 tests |
| 10.4-10.7 | Authoring guide + REGISTRY + reference plugin + CONTRIBUTING | `ae9e4f5` | +920 lines, +10 tests |

**Test delta:** 1162 → 1233 (+71 net across the four implementation slices).
**Coverage:** 76% (held).
**Lint / type:** clean throughout.

---

## Capability summary

### Slice 10.1 — Entry-point discovery + `plugin install`

New `mythic_vibe_cli/plugins/entry_points.py` discovers every
installed entry-point under the `mythic_vibe.plugins` group via
`importlib.metadata.entry_points`. Operators publish plugins to
PyPI (or install editable locally), then run:

```bash
mythic-vibe plugin discover           # list discovered EPs
mythic-vibe plugin install <name>     # register in mythic/plugins.json
```

Defensive against both the modern `entry_points(group=...)`
signature and the older dict-shaped fallback.

### Slice 10.2 — Plugin sandbox layer

New `mythic_vibe_cli/plugins/sandbox.py` provides:

- `safe_call(func, *args, timeout_sec=None, plugin_id="", **kwargs)` — exception isolation always; opt-in soft timeout via `MYTHIC_PLUGIN_TIMEOUT_SEC` env or explicit `timeout_sec=`.
- `probe_resource_caps()` — POSIX `getrusage`/`getrlimit` snapshot; Windows hosts get `advisory_only=True`.
- Typed `SandboxResult` and `ResourceProbe` for round-trippable health reporting.

Not yet wired into `PluginHookDispatcher` — that integration
fits naturally with PH-11 (Security/Sandbox/Permissions). For
now the sandbox is an importable utility for plugin authors and
tests.

### Slice 10.3 — Extension-point Protocols

New `mythic_vibe_cli/plugins/extension_points.py` defines six
`runtime_checkable` Protocols matching the master roadmap spec:

- `RitualPlugin` (rituals)
- `ProviderPlugin` (providers)
- `ScannerPlugin` (scanner_rules)
- `VerificationGatePlugin` (verification_gates)
- `ArtifactTemplatePlugin` (artifact_templates)
- `SlashCommandPlugin` (slash_commands)

Plus `categorise_plugin(obj) → list[str]` for runtime
introspection — used by inspection tooling and by plugin tests
to confirm Protocol coverage.

### Slice 10.4 — Plugin Authoring Guide

`docs/PLUGIN_AUTHORING_GUIDE.md` — the canonical author
tutorial. Covers mental model, hook table, all six extension
points with code examples, packaging, the sandbox contract,
testing recipe, and publishing.

### Slice 10.5 — Community plugin registry

`plugins/REGISTRY.md` — curated index of community plugins.
Inclusion criteria, reviewer checklist, removal policy. Initial
listing: the slice 10.6 reference plugin.

### Slice 10.6 — Reference plugin

`examples/plugins/mythic_vibe_example_plugin/` — real
installable Python package. Implements every extension-point
Protocol AND every event-bus hook. Operators verify the plugin
pipeline end-to-end via `pip install -e ...` →
`mythic-vibe plugin install mythic_vibe_example`.

### Slice 10.7 — CONTRIBUTING.md

Repo-root contribution guide. Six ME Laws, workflow, ADR
process with template, plugin route, code style, test
conventions, commit format, security policy, code of conduct.

---

## Master-roadmap impact

PH-10 closed. All 7 slices shipped:

- 10.1 Entry-point discovery ✓
- 10.2 Sandbox layer ✓
- 10.3 Extension points ✓
- 10.4 Authoring guide ✓
- 10.5 Registry index ✓
- 10.6 Reference plugin ✓
- 10.7 CONTRIBUTING.md ✓

**Phases now fully closed:** PH-01, PH-02, PH-03, PH-04, PH-05,
PH-06 (5/6), PH-07, PH-08, PH-09, **PH-10**, PH-13, PH-15.
(12 of 20.)

PH-10 unblocks no other phase directly — pure capability
addition. Remaining phases: PH-11 (Security/Sandbox), PH-12
(CI/CD), PH-14 (Policy Engine — PH-11 still blocking), PH-16
(MCP/ACP/OpenTelemetry), PH-17 (Multi-Surface Access), PH-18
(Robustness Sweeps), PH-19 (Distribution), PH-20 (v1.0.0).

**Recommended next move:** PH-11 (Security/Sandbox/Permissions) —
priority **critical**, deps `[PH-01]` satisfied. Natural
follow-on now that the plugin ecosystem exists: harden the
surface that plugins, providers, and operators interact with.
The slice 10.2 sandbox helper is a building block — PH-11 wires
it into the dispatcher and adds approval modes, redaction,
secret scanning, sandbox execution.

---

## Operational notes

- All 7 slices shipped under the ME laws: stdlib-first,
  optional deps via try-import + clean install hints, default-
  off behaviour preserved on every existing flow,
  cross-platform.
- Pre-existing 3 plugin tests still pass — every existing
  `plugin list / inspect / disable` command surface is
  unchanged. New `plugin discover` and `plugin install` are
  pure additions.
- No new ADRs were required this phase — every change ships
  inside the existing plugin module boundary established by
  ADR-0001 + ADR-0002. PH-11 will likely add ADR-0009
  (Approval Modes) and ADR-0010 (Redaction Engine).
- Sandbox layer is **available but not wired** into the
  dispatcher. That wiring belongs with PH-11's permissions
  layer; landing it now would couple two phases unnecessarily.

---

## Update Notice — 2026-05-02 (additive)

A later audit (`AUDIT_FAKE_TEMP_CODE_2026-05-02.md`, HEAD `e0953b6`) re-measured the project on 2026-05-02. The original closeout above is preserved unchanged; this notice is purely additive.

- **Coverage:** the figure above recorded as **"76% (held)"** was a stale carry-over. Live measurement (`pytest --cov=mythic_vibe_cli --cov-report=term-missing`) on 2026-05-02 reports **82%** branch+line coverage on the production package (1694 passed, 1 skipped, 14 subtests). The historical figure is left in place; current coverage is ~6 points higher than recorded.
- **Sandbox wiring (good news):** the closeout above states the sandbox is "available but not wired" into the dispatcher. As of HEAD `e0953b6` that wiring **was completed in a subsequent phase** — `plugins/dispatcher.py:31` imports `safe_call`, and `dispatcher.py:200` invokes it inside `_fire`. The original prose is left in place for historical accuracy; the wiring exists today.

— *Sólrún Hvítmynd & Runa, additive correction*
