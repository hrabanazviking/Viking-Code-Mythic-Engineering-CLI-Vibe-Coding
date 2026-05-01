# TASK — PH-10 Plugin Ecosystem & Community Infrastructure

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `d189344` (PH-09 finale)

PH-10 matures the plugin layer from "hooks fire" to a real
ecosystem with discovery, isolation, sandboxing, a plugin
registry, an authoring guide, and a community contribution
workflow.

**Master roadmap dependency:** `[PH-01, PH-02]` — both closed.

**Existing infrastructure (already shipped):**
- `mythic_vibe_cli/plugins/api.py` — PLUGIN_HOOKS list, PluginRecord
  dataclass, validate_hooks
- `mythic_vibe_cli/plugins/loader.py` — inspect_plugin() with
  module:object entry-point shape
- `mythic_vibe_cli/plugins/registry.py` — JSON registry at
  `mythic/plugins.json`
- `mythic_vibe_cli/plugins/dispatcher.py` — fires the 8 hooks
  (before/after × scan/packet/verify/reflect)
- `cmd_plugin_list / inspect / disable` — CLI surfaces

**What PH-10 adds:**
- Slice 10.1: standardised PyPI / setuptools entry-point discovery
- Slice 10.2: sandbox isolation layer
- Slice 10.3: typed extension-point contracts (6 categories)
- Slice 10.4: PLUGIN_AUTHORING_GUIDE.md
- Slice 10.5: REGISTRY.md community index
- Slice 10.6: reference plugin in examples/plugins/
- Slice 10.7: CONTRIBUTING.md

---

## Slice 10.1 — Entry-point discovery

**Goal:** allow plugins published to PyPI (or installed locally)
to register via the standard Python entry-points mechanism. The
operator runs `pip install some-mythic-plugin` and the plugin is
discoverable without manual registry editing.

**Files:**
- `mythic_vibe_cli/plugins/entry_points.py` (new) — uses
  `importlib.metadata.entry_points(group="mythic_vibe.plugins")`
  to enumerate installed plugins. Returns a list of typed
  records.
- `mythic_vibe_cli/commands.py`:
  - `cmd_plugin_discover` — list installed entry-points (no
    registry mutation).
  - `cmd_plugin_install <package-or-entrypoint>` — register an
    installed entry-point in the project's plugin registry.
- `mythic_vibe_cli/app.py` — argparse subcommands.
- Tests.

**Group name:** `mythic_vibe.plugins` (per master roadmap spec).

**Acceptance:**
- `mythic-vibe plugin discover` lists every installed entry-point
  in the `mythic_vibe.plugins` group, even when none are
  registered in the project.
- `mythic-vibe plugin install <name>` registers a discovered
  entry-point into `mythic/plugins.json` (calls existing
  `PluginRegistry.add`).
- All existing plugin tests pass.

**Progress:** [ ] not started

---

## Slice 10.2 — Sandbox layer

**Goal:** new `mythic_vibe_cli/plugins/sandbox.py` providing
exception isolation, per-hook timing budgets, and resource-cap
reporting. Wired into the existing `PluginHookDispatcher.emit`.

**Cross-platform notes:**
- Use `threading.Timer` for timeouts (signal.alarm is
  Unix-only).
- Resource caps via `resource.RLIMIT_*` are POSIX-only; on
  Windows fall back to "advisory only" with a clear warning in
  the plugin health record.
- Exception isolation = wrap each plugin hook call in
  try/except + log to plugin health.

**Files:**
- `mythic_vibe_cli/plugins/sandbox.py` (new).
- `mythic_vibe_cli/plugins/dispatcher.py` — opt-in route through
  the sandbox helper.
- Tests.

**Default behaviour:** exception isolation is on (already implicit
in the dispatcher's try/except); timing budgets are off by default
(opt in via `MYTHIC_PLUGIN_TIMEOUT_SEC`); resource caps are
advisory-only.

**Progress:** [ ] not started

---

## Slice 10.3 — Extension points

**Goal:** define typed `Protocol` classes for the six declared
extension-point categories in
`mythic_vibe_cli/plugins/extension_points.py`. These are
compile-time / static contracts; runtime dispatch still goes
through the existing hooks.

**Six extension points:**
- `RitualPlugin` — adds new ritual / phase commands
- `ProviderPlugin` — registers a new AIProvider with the registry
- `ScannerPlugin` — adds a context-scan rule
- `VerificationGate` — adds a custom verify gate
- `ArtifactTemplate` — declares a new template for `mythic/templates/`
- `SlashCommandPlugin` — declares a new `/slashname` command

Each is a `runtime_checkable` Protocol with the minimum surface a
plugin must implement.

**Files:**
- `mythic_vibe_cli/plugins/extension_points.py` (new).
- `mythic_vibe_cli/plugins/__init__.py` — re-export.
- Tests covering each Protocol.

**Progress:** [ ] not started

---

## Slice 10.4 — `docs/PLUGIN_AUTHORING_GUIDE.md`

**Goal:** step-by-step tutorial. Covers entry-point declaration,
the six extension points, hook lifecycle, sandbox contract,
testing, packaging, and PyPI publish.

Real, runnable code samples. Cross-references the reference
plugin (slice 10.6).

**Files:**
- `docs/PLUGIN_AUTHORING_GUIDE.md` (new).

**Progress:** [ ] not started

---

## Slice 10.5 — `plugins/REGISTRY.md`

**Goal:** index of known community plugins. Initially has the
template + the reference plugin (slice 10.6) listed. Documents
inclusion criteria (open-source license, ME laws compliance,
tests pass).

**Files:**
- `plugins/REGISTRY.md` (new) — yes, repo-root `plugins/`
  directory. Don't conflate with `mythic_vibe_cli/plugins/`.

**Progress:** [ ] not started

---

## Slice 10.6 — Reference plugin

**Goal:** ship `examples/plugins/mythic_vibe_example_plugin/` —
a real installable Python package that exercises every extension
point + hook. Operators can `pip install -e
examples/plugins/mythic_vibe_example_plugin/` and see plugins
working end-to-end.

**Files:**
- `examples/plugins/mythic_vibe_example_plugin/pyproject.toml`
- `examples/plugins/mythic_vibe_example_plugin/src/mythic_vibe_example_plugin/__init__.py`
- `examples/plugins/mythic_vibe_example_plugin/README.md`
- entry-points declared as `mythic_vibe.plugins`.

**Progress:** [ ] not started

---

## Slice 10.7 — `CONTRIBUTING.md`

**Goal:** `CONTRIBUTING.md` at repo root. Contribution workflow,
ADR process, plugin validation requirements, link to the
authoring guide and ME laws.

**Files:**
- `CONTRIBUTING.md` (new at repo root).

**Progress:** [ ] not started

---

## Phase finale

After all 7 slices ship:

- `PHASE10_FINALE_CLOSEOUT.md` — summary memo.
- Update memory + status file.
- Push.
- PH-10 closed in tracker.

---

## Operational notes

- ME laws apply: stdlib-first, optional deps via try-import,
  cross-platform, default-off feature gates.
- After each slice: update memory + status file immediately.
- Don't break existing plugin tests — every existing
  `cmd_plugin_*` flow must keep working.
