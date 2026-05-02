# TASK — PH-19 Distribution + Hardening (draft proposal)

**Opened:** 2026-05-02
**Branch:** `development`
**HEAD at draft:** `93aa56f` (post-Phase-G of the audit-remediation cycle)
**Author:** Runa Gridweaver Freyjasdottir, drafting on Volmarr's behalf
**Status:** `DRAFT — AWAITING VOLMARR APPROVAL`

---

## Why this draft exists

PH-19 was originally scoped on the master roadmap as **Distribution**:
pip / brew / scoop / aur / winget packaging. The Codex-authored
`docs/MASSIVE_RESEARCH_MULTI_PHASE_IMPROVEMENT_PLAN.md` (landed
mid-session at `cf526c5`) proposes 7 phases of hardening over 16
weeks. Most items in that plan are real value-adds — but ~30%
duplicate work we just shipped, and a few items (first-run wizard,
persona presets) cut against Mythic Engineering's "explicit operator
intent" design grain.

This draft **cherry-picks the high-leverage items into PH-19 and
PH-20** under our existing roadmap shape. Volmarr reviews and
overrides any of these decisions before any code lands.

---

## Operating rules (carry-over)

Same discipline that ran the 2026-05-02 audit remediation cycle:
1. **Additive only — never subtractive** (`feedback_additive_only.md`).
2. TASK file → commit + push → implement → ruff/mypy/pytest green →
   phase closeout memo → memory update → push.
3. ruff + mypy + pytest gate every commit.
4. Stdlib-first; cross-platform; open-source-only.
5. One real-bug or one cohesive feature per commit; no batching.

---

## Proposed PH-19 scope — Distribution + Hardening

The original "packaging" scope is still here (19.7), but it lands
**after** the hardening items so we ship packages against a verified-
clean codebase, not before.

### 19.1 — JSON contract snapshot tests
- **Why:** highest-leverage Phase-1 item from the Codex plan. Catches
  accidental JSON-schema drift the moment it happens.
- **Shape:** `tests/snapshots/` directory; one snapshot per high-value
  JSON command (`status --json`, `workflow plan --json`, `packet list --json`,
  `next --json`, `ai models --provider X --json`, `forge ledger latest --json`,
  `doctor --json`, `surface chat --backend X --run --json`,
  `verify --json`).
- **Approach:** stdlib `json.dumps(sort_keys=True, indent=2)`; tests
  diff fixture-vs-current; updated fixtures land in PRs explicitly.
  No external snapshot lib needed.
- **Deliverable:** `tests/snapshots/*.json` + per-command `assert_snapshot`
  helper in `tests/conftest.py`.
- **Estimated:** ~1-2 hours. Adds 10-20 tests. No production code change.

### 19.2 — `tools/contract_audit.py`
- **Why:** complements existing `drift.py` (which catches undocumented
  handlers / modules / superseded ADRs). The contract auditor closes
  the docs-↔-code drift gate at CI time.
- **Shape:** new top-level `tools/` directory. Script walks
  `docs/COMMAND_CONTRACTS.md` and asserts:
  - every documented command appears in `commands.py:COMMAND_HANDLERS`,
  - every documented alias resolves,
  - every documented exit code is reachable from runtime behavior.
- **CI gate:** `python tools/contract_audit.py --strict` runs in
  CI; non-zero exit fails the build.
- **Estimated:** ~2-3 hours. ~150 lines of code + tests.

### 19.3 — CI OS matrix (Linux × macOS × Windows)
- **Why:** the durable rule says "100% cross-platform" but CI only
  verifies Linux today. **Volmarr runs on Windows.** We need
  evidence, not just a rule.
- **Shape:** `.github/workflows/ci.yml` — extend the matrix:
  ```
  os: [ubuntu-latest, macos-latest, windows-latest]
  python-version: ["3.10", "3.11", "3.12"]
  ```
  9-cell matrix. Some tests may need platform skip markers
  (`@unittest.skipIf(sys.platform == "win32", ...)`) where they
  already exist for legitimate platform reasons (e.g. POSIX
  rlimit test).
- **Open question:** any flaky tests likely to surface? The
  `test_plugin_sandbox.py::test_elapsed_ms_recorded` Windows-timer
  flake noted earlier may also surface here — if so, fix or mark
  as a known-flaky as part of this slice.
- **Estimated:** ~1-2 hours of YAML + likely 1-2 platform fixes.

### 19.4 — Property tests for state migrations
- **Why:** migrations are the most dangerous code we ship — a bad
  migration corrupts user state. Property tests give us
  generative coverage hypothesis-style.
- **Shape:** add `hypothesis` to `[test]` extras in `pyproject.toml`.
  New `tests/property/test_state_migrations.py` generates random
  pre-migration JSON state, runs every registered migration in
  order, asserts: schema invariants hold, idempotent re-run is a
  no-op, no data lost from preserved fields.
- **Open question:** add `hypothesis` as a test-extra dep? It's
  open-source (MPL), pure-Python, mature. Doesn't violate the
  stdlib-first rule for test-time tooling.
- **Estimated:** ~2-3 hours. ~50 generative tests cover the full
  migration matrix.

### 19.5 — Threat model document
- **Why:** essential before v1.0; cheap to write. Surfaces the
  attack surface explicitly so operators / contributors know what
  the project's security posture is.
- **Shape:** new `docs/security/threat_model.md`. Sections:
  - Attack surface (CLI, plugins, providers, chat bridge,
    web terminal, MCP server, ACP bridge).
  - Trust boundaries (operator → CLI; CLI → plugins; CLI →
    providers; CLI → chat bridge; chat bridge → external chat
    services).
  - Threats (RCE via plugin, secret exfiltration via provider,
    chat-bridge command-injection, web-terminal token theft,
    MCP-server unbounded resource use, etc.).
  - Mitigations in place (sandbox `safe_call`, plugin capability
    model — when 20.3 lands —, allowlist refusal in chat bridge,
    `secrets.compare_digest` in web terminal, ADR-0009 internal-API
    surfaces).
  - Known residual risk (operators run with full permissions,
    plugin code review is operator's responsibility, etc.).
- **Estimated:** ~2 hours of writing.

### 19.6 — Compatibility policy document
- **Why:** v1.0-essential. Pre-v1.0 the CLI is allowed to break;
  post-v1.0 we owe operators stability promises. Without an
  explicit policy, breaking changes will leak in.
- **Shape:** new `docs/compatibility_policy.md`. Sections:
  - **Stability grades** per surface:
    - **Stable** — JSON output schemas, exit codes, slash command
      names, argparse arg names. Breaking changes require
      deprecation window + ADR.
    - **Stable-with-tolerance** — human-readable text output
      (operators are expected to grep the JSON, not the prose).
    - **Internal** — anything under a `_` prefix or in a module
      not re-exported from `mythic_vibe_cli/__init__.py`.
  - **Deprecation window:** minimum 1 minor release of warning
    emit before removal in a major.
  - **Migration advisories:** standardized header in CHANGELOG
    when a stable surface changes.
- **Estimated:** ~2 hours of writing.

### 19.7 — Distribution packaging
- **Why:** the original PH-19 scope. Land **after** 19.1-19.6 so
  packages ship against a verified codebase.
- **Shape:**
  - **pip** — `python -m build` already works. Add a release
    workflow that publishes to TestPyPI on `development` tags and
    PyPI on `main` tags. Trusted publishing (PyPI's OIDC) so we
    don't store API tokens.
  - **Homebrew** — formula in a `homebrew-mythic` tap repo (or
    homebrew-core eventually). Tarball-based.
  - **Scoop** — manifest in a `scoop-mythic` bucket repo.
    Windows-friendly.
  - **AUR** — `mythic-vibe-cli-bin` package in AUR (binary; we
    don't depend on system Python being a specific version).
  - **winget** — manifest PR to `winget-pkgs` once we have a stable
    1.0 line.
- **Open question:** which stores require a Microsoft / Apple
  developer account? winget's manifest review is free. Apple's
  notarization (for signed binaries) needs an Apple Developer
  account — defer to PH-20+ if that's a yes/no decision.
- **Estimated:** ~4-6 hours. May spread across multiple commits
  (one per channel).

### 19.8 — Stale-catalog watchdog
- **Why:** ADR-0010 already exposes `last_updated` per `ModelInfo`
  record. A doctor check that warns when the value is older than
  policy threshold (e.g. 90 days) is one new function. Closes the
  loop on the model-listing remediation.
- **Shape:** extend `cmd_doctor` with a new `model_catalog_freshness`
  check. When any static catalog's `last_updated` is older than 90
  days, doctor emits a `warning` with the affected provider names.
- **Estimated:** ~30 min.

### Phase 19 closeout
- Each slice gets its own commit + closeout addendum to a
  PH-19 finale memo.
- `MEMORY.md` + `project_mythic_engineering_cli_status.md` updated.
- v1.0-rc tag candidate.

---

## Proposed PH-20 scope — Polish + v1.0.0 Launch

After PH-19 lands, the codebase is hardened. PH-20 adds polish that
makes v1.0 feel finished without bloating the surface.

### 20.1 — `packet lint` command
- New top-level subcommand. Lints packets for missing acceptance
  criteria, unclear test strategy, ambiguous task wording (heuristic),
  insufficient architectural anchors. Per-rule severity.
- ~3-4 hours, ~20 tests.

### 20.2 — `doctor --fix` (tightly scoped)
- New `--fix` flag on `cmd_doctor`. Auto-remediates safe, reversible
  issues only:
  - Missing `mythic/` subdirectories.
  - Stale `mythic/method_manifest.json` (regenerates from current
    method corpus).
  - Missing CHANGELOG `[Unreleased]` section (creates an empty one).
- **Hard-rule: never auto-fix anything that touches user-authored
  content** (constraints, oaths, ADRs, packets, decisions).
- ~2-3 hours, ~10 tests.

### 20.3 — Plugin capability model + `plugin doctor` + circuit breaker
- Largest PH-20 item. Three sub-pieces:
  - **Capability declarations** in `mythic/plugins.json` schema:
    `capabilities: ["read", "network", "subprocess", "file-write"]`.
    Default-deny: a plugin without explicit capabilities can read
    its own context only.
  - **`plugin doctor`** — new command that audits installed plugins
    against declared capabilities + runtime health.
  - **Circuit breaker** — extends `safe_call` so a plugin that
    times out 3 times in a row is auto-disabled with a stderr log.
- ~5-6 hours, ~30 tests.

### 20.4 — `ai recommend` command
- New top-level subcommand. Given task constraints (`--task`,
  `--max-context`, `--vision-required`, `--cost-class`), scores
  models from the Phase-D catalog and recommends top-N.
- Pure-policy DSL; no provider call needed.
- ~3-4 hours, ~15 tests.

### 20.5 — Provider conformance test suite
- `tests/providers/test_contract_conformance.py` — runs the same
  contract assertions against every provider in `ProviderRegistry`.
  Asserts each implements `validate_config / estimate / run` with
  the documented signatures and that errors / timeouts fall into
  declared exit-code classes.
- ~2 hours, ~20 tests.

### 20.6 — `mythic-vibe provenance verify` command (checksums only)
- Verifies plunder-imported file checksums match recorded provenance.
- Signed artifacts with GPG / Sigstore deferred to v1.x.
- ~1-2 hours, ~10 tests.

### 20.7 — v1.0.0 release tag + final closeout
- `CHANGELOG.md` v1.0.0 entry; `RELEASE_CHECKLIST.md` walkthrough;
  tag pushed to `main`; release workflow publishes everywhere.
- Closeout memo at `RELEASE_v1_0_0_2026-XX-XX.md`.

---

## Items deliberately rejected from the Codex plan

These cut against Mythic Engineering's design grain or duplicate
existing infrastructure. **Volmarr can override any of these.**

| Item | Why rejected |
|---|---|
| **First-run wizard** (Codex Phase 5) | Conflicts with the "explicit operator intent" rule. `mythic-vibe init/imbue/start` is intentionally non-interactive. A wizard would feel like bloat. **If accepted, would belong as an opt-in `--interactive` flag, not a default flow.** |
| **Persona-driven command presets** (Codex Phase 5) | Same. Mythic Engineering doesn't gate the surface by role; every operator gets the full toolkit and chooses what's appropriate. |
| **Full GPG / Sigstore signed artifacts** (Codex Phase 6) | Big infra scope (key management, OIDC, transparency log). Checksums in PH-19's distribution work give 80% of the value. **Defer to v1.x.** |
| **Architecture drift dashboard** (Codex Phase 7) | `drift.py` already produces structured output; a JSON `drift scorecard` rollup is a 30-min addition we can drop into 19.2's contract auditor or PH-20. A full dashboard is operator-facing UX bloat. |
| **TUI verification heatmap / plugin risk indicators** (Codex Phase 5) | Information-density risk. The current TUI's drift panel + status bar are dense enough. Add only when a real operator-pain-point surfaces. |
| **`verify replay` command** (Codex Phase 1) | Duplicates `forge resume` (PH-03 slice 3.8). A one-line shortcut `verify --rerun-last` is fine; a new top-level command is unjustified. |

## Items deferred to v1.x (post-v1.0.0)

These are reasonable but post-v1.0 scope:
- Plunder modified-lines attestation (extends existing provenance).
- Quarterly architecture review cadence (operational practice, not code).
- Automated changelog classification by PR labels (operational; manual
  classification is fine for a small team).
- Context budget optimizer for packets (real value, but not v1.0
  load-bearing).
- Workflow lineage viewer (graph visualization — `forge_reflection`
  output is enough for v1.0).

---

## Open questions for Volmarr

1. **`hypothesis` test-time dep (19.4)** — OK to add? Pure-Python,
   MPL, mature, only loaded for property tests.
2. **Trusted publishing on PyPI (19.7)** — your account, your call on
   account setup. Or do you have an existing PyPI identity?
3. **Homebrew + Scoop tap repos (19.7)** — create as
   `hrabanazviking/homebrew-mythic` + `hrabanazviking/scoop-mythic`?
   Or stage in this repo until they grow up?
4. **`doctor --fix` scope** (20.2) — comfortable with the three
   listed auto-remediations, or want a tighter / wider scope?
5. **`plugin doctor` circuit-breaker threshold** (20.3) — auto-disable
   after 3 consecutive timeouts? Or higher / configurable?
6. **First-run wizard rejection** — agreed, or do you want me to
   reconsider with an opt-in `--interactive` design?

---

## Estimated scope summary

| Phase | Slices | Estimated effort |
|---|---|---|
| PH-19 | 19.1 → 19.8 | **~12-18 hours** spread over 4-6 commits |
| PH-20 | 20.1 → 20.7 | **~17-22 hours** spread over 7-8 commits |
| **Total** | 15 slices, 11-14 commits | **~30-40 hours** |

For comparison: the 2026-05-02 audit remediation cycle ran 19
commits in ~10 hours. PH-19+20 is roughly 3x that, so ~3
working days at the pace we just demonstrated.

---

## Status

`STATUS: DRAFT — AWAITING VOLMARR APPROVAL`

**Next step:**
1. Volmarr reviews this draft.
2. Volmarr accepts / rejects each item + answers the open questions.
3. On approval, this file's status flips to `OPEN — PHASE 19.1 KICKOFF`
   and 19.1 begins.

The draft will be committed + pushed to `development` so the
review record is durable. No code work begins until Volmarr's
explicit go-ahead.

---

## Volmarr's Decisions — 2026-05-02 (additive)

The six open questions have been answered. Below are the decisions
captured verbatim, locked into the plan. The draft above is preserved
unchanged per the additive-only rule.

### Q1 — `hypothesis` test-time dep (19.4)
**Decision:** **ADD it.** `hypothesis` lands in `pyproject.toml`'s
`[test]` extras. Pure-Python, MPL-licensed, mature. Only loaded
during property tests; doesn't affect production runtime.

### Q2 — PyPI publishing (19.7)
**Volmarr asked: "what is PyPI?"** Brief answer recorded for
durable reference: PyPI (`pypi.org`) is the Python Package Index,
the standard online registry where Python packages live. `pip
install <name>` downloads from PyPI by default. Publishing
requires a free PyPI account; modern best practice is **trusted
publishing** via GitHub Actions OIDC (no API token stored in repo).
Once configured, every git tag on the right branch triggers a
build + upload, and `pip install mythic-vibe-cli` works worldwide.

**Decision (recorded for kickoff):** Volmarr will create or confirm
a PyPI identity at kickoff. The 19.7 commit will:
- Add a release workflow (`.github/workflows/release.yml`) that
  builds wheel + sdist on tag push.
- Configure trusted publishing pointing at this repo.
- Test on TestPyPI first (a sandbox PyPI), then promote to real
  PyPI.

### Q3 — Homebrew + Scoop tap repos (19.7)
**Volmarr asked: "Explain what is Homebrew + Scoop?"** Brief
durable answer:
- **Homebrew** = macOS/Linux package manager. Users run `brew
  install <name>`. Publishing options: official `homebrew-core`
  (strict review, requires an established project) or a self-managed
  **tap** — a GitHub repo named `homebrew-<word>` that anyone uses
  via `brew tap <user>/<word>; brew install <thing>`. Tap = no
  review, you control it, standard for new projects.
- **Scoop** = the Windows equivalent. Users run `scoop install
  <name>`. The tap-equivalent is a **bucket** — a GitHub repo with
  JSON manifests. Lighter than Homebrew (no Ruby, just JSON).

Both are free, open-source, GitHub-only. No Apple / Microsoft
developer account required for the tap/bucket path. Homebrew
formulas don't need notarization unless we ship signed binaries.

**Decision:** create separate tap / bucket repos at kickoff:
- `hrabanazviking/homebrew-mythic` — Homebrew formula.
- `hrabanazviking/scoop-mythic` — Scoop bucket.
This keeps the main repo clean and lets future projects (NSE,
WYRD, MindSpark, pygame) join the same tap/bucket without churn.

### Q4 — `doctor --fix` scope (20.2)
**Decision:** **"yes make all the doctor stuff"** — interpreted as:
do all three listed auto-remediations **plus any natural reversible
extensions** the doctor surface ought to have. Concrete extensions
to fold in:
- Missing `mythic/` subdirectories ✓ (original)
- Stale `mythic/method_manifest.json` regeneration ✓ (original)
- Missing CHANGELOG `[Unreleased]` section ✓ (original)
- **+** Missing `docs/ADRS/` directory creation
- **+** Missing `mythic/handoffs/` / `mythic/reflections/` /
  `mythic/packets/` / `mythic/checkins/` directory creation
- **+** Missing `.gitignore` lines for `mythic/ai/provider_calls.jsonl`
  (which contains secrets and should never commit)
- **+** Stale `mythic/project_index.json` regeneration (when older
  than 7 days and `mythic/scan.json` exists)
- **+** Missing `mythic/oaths.md` template scaffold (empty section
  headers only)

**Hard-rule preserved:** never auto-fix anything that touches user-
authored content (constraints, oath text, ADRs prose, packets,
decisions). Only structure / regenerable artefacts / safety hygiene.

20.2 effort estimate revised: **~3-4 hours** (was 2-3); adds ~15
tests (was ~10).

### Q5 — Plugin circuit-breaker threshold (20.3)
**Decision:** **configurable.** Threshold lives in `mythic/plugins.json`
schema as a per-plugin override, with a project-level default and
an env-var top-level override:

```
priority: env var > project default > schema default
MYTHIC_PLUGIN_TIMEOUT_THRESHOLD  >  mythic/plugins.json:default_timeout_threshold  >  3 (built-in)
```

Per-plugin override:
```json
{
  "entrypoint": "mypkg:Plugin",
  "timeout_threshold": 5,
  ...
}
```

Auto-disable after threshold consecutive timeouts. Reset counter on
any successful invocation. Disabled plugins surface in `plugin doctor`
with a re-enable hint.

### Q6 — First-run wizard (revised)
**Decision:** **opt-in.** Move the wizard from the "rejected" list
to a new opt-in slice in PH-20:

**20.0 (new) — `mythic-vibe init --interactive` opt-in wizard**
- Default `mythic-vibe init` behaviour is **unchanged** (preserves
  the explicit-operator-intent rule).
- New `--interactive` flag opens a stdin-based Q&A that asks for:
  - Project name
  - Default AI provider (one of the registered providers)
  - Operator name (defaults to `$USER` / `$USERNAME`)
  - Whether to scaffold a sample ADR / oath / constraint file
- Wizard writes `mythic/project_settings.json` and the chosen
  scaffolds. Operator can run `mythic-vibe init` repeatedly to
  reconfigure (idempotent — won't overwrite without `--force`).
- **Strict-additive:** zero change to non-interactive behaviour.
  Operators who never pass `--interactive` see no difference.
- Effort estimate: **~2-3 hours, ~10 tests.**

This expands PH-20 to **8 slices** (was 7); revised total
estimate: **~19-25h** (was ~17-22h). Cumulative PH-19 + PH-20:
**~31-43h** (was ~30-40h).

---

## Status (revised after Volmarr's decisions)

`STATUS: DRAFT — DECISIONS LOCKED — AWAITING FINAL GO/NO-GO ON KICKOFF`

All six open questions answered; scope is locked. Original draft
(slices 19.1-19.8 + 20.1-20.7) preserved verbatim above. The
decisions section adds:
- 20.2 expanded with extra reversible auto-remediations.
- 20.3 circuit-breaker threshold made configurable (env var > config > built-in default).
- New 20.0 opt-in `--interactive` wizard slice.

When Volmarr says **"go for PH-19"**, this file's status flips
to `OPEN — PHASE 19.1 KICKOFF` and 19.1 (JSON contract snapshot
tests) begins.

---

## Update 2026-05-02 — Distribution channel scope locked (additive)

Volmarr confirmed: **the three v1.0 package channels are PyPI,
Homebrew, and Scoop.** AUR and winget are deferred to v1.x.

**Why this matters for slice 19.7:** the original draft listed five
channels (pip / brew / scoop / aur / winget) which would have made
19.7 a multi-day slice. Cutting to three keeps it ~4-6 hours and
focuses on the channels that cover the durable cross-platform rule:

| Channel | OS coverage | Estimated effort |
|---|---|---|
| **PyPI** | All — anyone with Python | ~2h (release workflow + trusted publishing setup) |
| **Homebrew** | macOS + Linux | ~1-2h (formula in tap repo) |
| **Scoop** | Windows | ~1h (manifest in bucket repo) |
| ~~AUR~~ | ~~Arch Linux only~~ | **deferred to v1.x** |
| ~~winget~~ | ~~Windows (modern)~~ | **deferred to v1.x** |

Operators who use AUR or winget can install from PyPI in the
meantime (pip works everywhere). After v1.0 ships and gets real-
world feedback, AUR + winget become reasonable v1.x additions
without blocking the launch.

**Slice 19.7 revised effort:** ~4-5 hours (was 4-6).
**PH-19 cumulative revised:** **~12-17 hours** (was 12-18).

---

## Update 2026-05-02 — Cross-platform plan fold-ins (additive)

After reading `docs/CROSS_PLATFORM_MULTIPHASE_PLAN.md` (the second
Codex-authored research plan), three concrete fold-ins land into
slice **19.3 (CI OS matrix)** before kickoff. The rest of that
plan is either already done in the codebase (the plan author
didn't see `hardware.py`, `file_mutation_queue.py`, `FileLock`,
or `docs/hardware_profiles.md` — all of which already cover what
the plan recommends) or correctly deferred to post-v1.0.

### 19.3 expansion — three additions

**Original 19.3:** Linux × macOS × Windows × Python 3.10/3.11/3.12 matrix.

**Now adds:**

1. **`ubuntu-24.04-arm` runner row.** GitHub Actions provides a
   free arm64 Linux runner for public repos. Adding it verifies
   that the Pi tier (`pi_zero` / `pi_5` profiles already
   documented in `docs/hardware_profiles.md`) actually runs the
   test suite on its target architecture. ~1 hour.

2. **Cross-platform install smoke test.** One job per OS that runs:
   ```bash
   pip install .
   mythic-vibe --help
   mythic-vibe doctor
   mythic-vibe surface chat --backend matrix    # legacy scaffolding-and-exit
   ```
   Asserts exit-0 and expected output on each platform. Catches
   the "works on my machine" class of regression that unit tests
   miss. ~1 hour.

3. **Windows long-path test.** Single regression test that creates
   a path > 260 chars (the historical Windows MAX_PATH limit) and
   exercises file_mutation_queue + FileLock against it. Catches
   the long-path gotcha most cross-platform Python projects hit
   eventually. ~30 minutes.

### Slice 19.3 revised effort: **~3-4 hours** (was 1-2)
### PH-19 cumulative revised: **~14-19 hours** (was 12-17)

### Cross-platform plan items deferred to v1.x or PH-21+

For the durable record of decisions:

| Plan item | Defer to | Why |
|---|---|---|
| Single-file executables (PyInstaller / Nuitka) | v1.x | PyPI/Brew/Scoop cover install needs |
| Container/OCI image | v1.x | Useful for CI agents but not v1.0 essential |
| Android/Termux formal support | post-v1.0 | Termux works through PyPI today |
| Native Android wrapper app | indefinite | Months of work; not on Volmarr's priority list |
| SBOM generation | v1.x | CI overhead; checksums (20.6) cover integrity |
| Wheelhouse offline install | v1.x | Niche use case |
| macOS notarization | with PyInstaller defer | Only relevant for signed binaries |
| Reproducible builds + tag signing | v1.x | Sigstore infra; checksums first |
| Rust/Go launcher shim | v2.0 strategic | Months of work |
| WASI experimental runtime | indefinite | Pure speculation |

### Cross-platform plan items already covered by existing code
(captured here so future readers don't re-relitigate them)

| Plan recommendation | Already exists at |
|---|---|
| Platform detection helper module | `mythic_vibe_cli/hardware.py` (PH-06 slice 6.6) |
| Path/data-dir abstraction | `mythic_vibe_cli/config.py` |
| Atomic write + Windows-safe locking | `runtime/file_mutation_queue.py`, `persistence/json_store.py:FileLock` |
| `pathlib` standardization | Already used throughout |
| `utf-8` encoding default | Used throughout |
| Raspberry Pi support tier | `docs/hardware_profiles.md` (`pi_zero`, `pi_5`) |
| `doctor` with platform diagnostics | `cmd_doctor` + `hardware.py` integration |
| Optional heavy deps as extras | `pyproject.toml` already has `[ai]`, `[tui]`, `[voice]`, `[mindspark]`, `[wyrd]`, etc. |
| Compatibility changelog section | Folded into 19.6 (compatibility policy) |
| PowerShell completion script | `mythic-vibe completion --shell powershell` already exists per the slash catalog |

---

## Update 2026-05-02 — Volmarr's "add everything" expansion (additive)

Volmarr's call: **"I want to add all of them that are not already
being addressed into the current plan."** That overrides every
"rejected" / "deferred to v1.x" / "deferred to PH-21+" decision
above. The original draft prose is preserved verbatim per the
additive-only rule. This section adds **every previously-deferred
item** as in-scope work.

The expansion adds **two new phases (PH-21, PH-22)** plus new
slices to existing PH-20 to honour the "all in" directive while
keeping v1.0 release-shippable. The original PH-19 → PH-20.7
sequence remains the **v1.0 launch path**; the new items either
fold into existing slices or become explicit follow-ons.

### Re-classification of previously-rejected/deferred items

| Item | Original status | New status |
|---|---|---|
| First-run wizard | rejected → opt-in 20.0 | already in plan (20.0) |
| Persona-driven command presets | rejected (philosophical conflict) | **NEW slice 20.A** — opt-in via `--preset` flag, default behaviour preserved |
| Full GPG / Sigstore signed artifacts | deferred to v1.x | **NEW slice 21.5** |
| Architecture drift dashboard | rejected (drift.py + JSON enough) | **NEW slice 20.E** — wraps existing `drift.py` with a `drift dashboard` command emitting markdown + JSON scorecard |
| TUI verification heatmap / plugin risk indicators | rejected (density risk) | **NEW slice 20.I** — opt-in TUI panel, `mythic-vibe tui --panels=heatmap,risk` |
| `verify replay` command | rejected (duplicates `forge resume`) | **NEW slice 20.B** — thin shortcut command that delegates to `forge resume` machinery |
| Plunder modified-lines attestation | deferred to v1.x | **NEW slice 20.G** |
| Quarterly architecture review cadence | deferred to v1.x | **NEW slice 20.H** — `mythic-vibe review architecture` command + `docs/governance/quarterly_review.md` |
| Automated changelog classification | deferred to v1.x | **NEW slice 20.F** — extends `scripts/check_changelog.py` |
| Context budget optimizer | deferred to v1.x | **NEW slice 20.D** |
| Workflow lineage viewer | deferred to v1.x | **NEW slice 20.C** — `mythic-vibe workflow lineage` reads existing `forge_reflection` + `forge_ledger` data, emits a graph view |
| Single-file executables (PyInstaller) | deferred to v1.x | **NEW slice 21.2** |
| Single-file executables (Nuitka, alternative) | deferred to v1.x | **NEW slice 21.3** |
| Container / OCI image | deferred to v1.x | **NEW slice 21.1** |
| Android / Termux formal support | deferred to v1.x | **NEW slice 21.9** — docs + detection adjustments |
| Native Android wrapper app | indefinite | **NEW slice 22.2** ⚠ multi-week |
| SBOM generation | deferred to v1.x | **NEW slice 19.5b** — folds into 19.5 (threat model) |
| Wheelhouse / offline install | deferred to v1.x | **NEW slice 19.7b** — folds into 19.7 (distribution) |
| macOS notarization | deferred with PyInstaller | **NEW slice 21.4** — tied to 21.2/21.3 |
| Reproducible builds + tag signing | deferred to v1.x | **NEW slice 21.6** |
| AUR package | deferred to v1.x | **NEW slice 21.7** |
| winget manifest | deferred to v1.x | **NEW slice 21.8** |
| Rust / Go launcher shim | v2.0 strategic | **NEW slice 22.1** ⚠ multi-week |
| WASI experimental runtime | indefinite | **NEW slice 22.3** ⚠ multi-week, speculative |

### PH-19 expansions (small fold-ins)

- **19.5b** SBOM generation — adds `cyclonedx-bom` (open-source) to dev extras; CI step generates `mythic-vibe.cdx.json` per release. ~1-2h.
- **19.7b** Wheelhouse / offline install bundle — release workflow produces a `mythic-vibe-wheelhouse-<version>.tar.gz` containing all dependency wheels for offline `pip install --no-index` on constrained networks. ~1h.

**Revised PH-19 effort: ~16-22h** (was 14-19h).

### PH-20 expansions (9 new slices folded in pre-launch)

The original PH-20 had 8 slices (20.0-20.7). The expansion adds 9
more (20.A-20.I) pre-`v1.0.0 release tag (20.7)`, so the v1.0
launch ships with everything Volmarr asked for.

| Slice | What | Estimated effort |
|---|---|---|
| **20.A** | Persona-driven command presets (`solo` / `team-lead` / `auditor`) — opt-in via new `--preset` flag on relevant commands; default behaviour preserved | ~3-4h |
| **20.B** | `verify replay` command — thin shortcut that delegates to `forge resume` | ~1h |
| **20.C** | `workflow lineage` viewer — emits graph from existing `forge_reflection` + `forge_ledger` data; markdown + JSON output | ~3-4h |
| **20.D** | Context budget optimizer — per-role token-aware packet trimming in `codex_bridge:PacketBuilder` | ~3-4h |
| **20.E** | Architecture drift dashboard — wraps `drift.py` with `mythic-vibe drift dashboard` (markdown + JSON scorecard) | ~2h |
| **20.F** | Automated changelog classification by PR labels — extends `scripts/check_changelog.py` | ~2h |
| **20.G** | Plunder modified-lines attestation — extends `mythic_vibe_cli/plunder/provenance.py` to record per-line diff hash | ~3h |
| **20.H** | `review architecture` command + quarterly cadence doc | ~2h |
| **20.I** | TUI heatmap + plugin risk indicators panel — opt-in via `--panels` flag, default TUI unchanged | ~4-5h |

**Revised PH-20 effort: ~42-54h** (was 19-25h, +23-29h from these 9 slices).

20.7 (v1.0.0 release tag) lands **after** 20.A through 20.I, so the
v1.0 release artifact has all the polish Volmarr asked for.

### PH-21 — v1.x Distribution Expansion (NEW phase, post-v1.0 release)

These 9 slices are too big to gate v1.0 on but Volmarr wants them in
the plan. They land **after v1.0 ships**, in a v1.1.0 / v1.2.0
release wave.

| Slice | What | Estimated effort | Notes |
|---|---|---|---|
| **21.1** | Container / OCI image (multi-arch via `buildx`) — published to GHCR + Docker Hub | ~3-4h | |
| **21.2** | Single-file executables via PyInstaller for Linux + Windows + macOS | ~6-8h | Larger because of per-OS quirks |
| **21.3** | Single-file executables via Nuitka (alternative; faster startup, smaller binaries) | ~6-8h | Optional alongside 21.2 — operator picks |
| **21.4** | macOS notarization for binary releases | ~3-4h | Requires Apple Developer account ($99/yr) — **flag for Volmarr** |
| **21.5** | Full GPG / Sigstore signed artifacts (replaces 20.6 checksums-only) | ~6-8h | Sigstore OIDC keyless signing avoids GPG key management |
| **21.6** | Reproducible build attestations + tag signing | ~4-6h | |
| **21.7** | AUR `mythic-vibe-cli-bin` package + maintainer scripts | ~2h | |
| **21.8** | winget manifest PR to `winget-pkgs` | ~2h | |
| **21.9** | Android / Termux formal support (docs + platform detection adjustments) | ~3-4h | Termux already works through PyPI; this is polish |

**PH-21 estimated effort: ~35-46h.**

### PH-22 — v2.0 Strategic Stretch (NEW phase, ⚠ multi-week each)

Three items genuinely sized in **weeks**, not hours. Volmarr asked
for them in scope, so they land in the plan — but flagged
explicitly so timeline expectations are accurate.

| Slice | What | Estimated effort | Notes |
|---|---|---|---|
| **22.1** | Rust / Go launcher shim around the Python runtime — gives operators a single static binary with no Python dep | **~2-4 weeks** | New code language adopted; distribution simplifies dramatically; v2.0 strategic option |
| **22.2** | Native Android wrapper app — Kotlin/Java app embedding the Python runtime via Chaquopy or BeeWare; presents the CLI as native Android UI | **~3-6 weeks** | Major new product surface; Android dev tooling required; v2.0 strategic |
| **22.3** | WASI experimental runtime — Mythic Vibe CLI compiled to WebAssembly for browser/sandbox use | **~4+ weeks (speculative)** | Pure exploration; many Python deps don't WASI-compile yet; v2.0 R&D |

**PH-22 estimated effort: ~9-14 weeks (~360-560h).**

### Cumulative totals after expansion

| Phase | Slice count | Estimated effort |
|---|---|---|
| PH-19 (Distribution + Hardening) | 10 | ~16-22h |
| PH-20 (Polish + v1.0.0 Launch) | 17 | ~42-54h |
| **v1.0 launch gate (PH-19 + PH-20)** | **27 slices** | **~58-76h** |
| PH-21 (v1.x Distribution Expansion) | 9 | ~35-46h |
| PH-22 (v2.0 Strategic Stretch) | 3 | ~360-560h |
| **Cumulative all phases** | **39 slices** | **~450-680h** |

At our demonstrated remediation-cycle pace (~1 commit/hour), v1.0
launch is **~6-8 working days** of focused work. PH-21 adds
another **~4-6 working days**. PH-22 alone is **9-14 weeks** if
all three stretch items are pursued.

### Confirmation requests for Volmarr

The expansion is locked, but two items deserve explicit confirmation
before kickoff because they have real-world cost or scope implications:

1. **macOS notarization (21.4)** requires an **Apple Developer
   account ($99/year)**. Confirm willingness to register, or skip
   21.4 and ship un-notarized macOS binaries (operators will see
   Gatekeeper warnings on first run).
2. **PH-22 stretch items (22.1 / 22.2 / 22.3)** are genuinely
   weeks-each work. Confirm: keep all three in the plan, or trim
   to 1-2 (recommend keeping 22.1 Rust/Go shim — biggest distribution
   win — and treating 22.2/22.3 as deferred research)?

### Reordering — what kicks off first

Despite the expansion, **the kickoff sequence is unchanged**: 19.1
(JSON contract snapshot tests) is still the smallest, safest first
slice. The expansion only adds work AFTER what was already planned;
nothing reshuffles the front of the queue.

`STATUS (revised): DRAFT — DECISIONS LOCKED, ALL ITEMS IN SCOPE — AWAITING FINAL GO/NO-GO ON KICKOFF`

---

## Update 2026-05-02 — Final two confirmations resolved (additive)

Volmarr's call:
1. **macOS notarization (21.4):** **skip — ship un-notarized binaries.**
2. **PH-22 stretch items:** **keep all three** (22.1 + 22.2 + 22.3).

### 21.4 rescoped — Gatekeeper override docs instead of full notarization

Slice 21.4 changes from "macOS notarization" (Apple Developer
account, ~3-4h workflow + $99/year) to a much smaller scope:

**21.4 (rescoped) — macOS Gatekeeper override documentation.** When
operators run a PyInstaller/Nuitka-built `mythic-vibe` binary on
macOS for the first time, Gatekeeper will block it with a "cannot be
opened because it is from an unidentified developer" dialog. The
release docs (`docs/INSTALL.md` + per-platform guides folded into
21.7/21.8/21.9) need a clear "How to bypass Gatekeeper on first
launch" section covering:
- Right-click → Open (the operator-friendly path)
- `xattr -d com.apple.quarantine /path/to/mythic-vibe` (the CLI path)
- Why we ship un-notarized (operator-sovereignty + open-source
  philosophy + no $99/yr Apple tax)

**21.4 revised effort: ~30 minutes** (was 3-4h). **PH-21 cumulative
revised: ~32-43h** (was 35-46h).

If operator demand for notarization grows post-v1.0, the plan can
revisit by adding a separate v1.x slice with the Apple Developer
account work.

### PH-22 confirmed in scope

All three stretch items remain in the plan:

- **22.1** Rust / Go launcher shim — ~2-4 weeks
- **22.2** Native Android wrapper app — ~3-6 weeks
- **22.3** WASI experimental runtime — ~4+ weeks (speculative)

PH-22 cumulative: **~9-14 weeks** when all three are pursued in
sequence. Operating expectation: PH-22 is **post-v1.0 R&D**, not
gating any release. v1.0 ships at the end of PH-20; v1.x channels
ship after PH-21; v2.0 emerges from PH-22 work as the strategic
items mature.

### Final cumulative totals (decisions locked)

| Tier | Slices | Hours / weeks | Calendar at our pace |
|---|---|---|---|
| v1.0 launch gate (PH-19 + PH-20) | **27** | ~58-76h | ~6-8 working days |
| v1.x expansion (PH-21) | **9** | ~32-43h | ~4-5 working days |
| v2.0 stretch (PH-22) | **3** | ~360-560h | ~9-14 weeks |
| **All phases** | **39** | ~450-680h | — |

### Status (final, decisions complete)

`STATUS: DRAFT — ALL DECISIONS LOCKED — READY FOR KICKOFF ON COMMAND`

Volmarr's word **"go for PH-19"** flips the file's live status to
`OPEN — PHASE 19.1 KICKOFF` and the cycle begins. First commit:
slice 19.1 (JSON contract snapshot tests) — smallest, safest, zero
production-code change.
