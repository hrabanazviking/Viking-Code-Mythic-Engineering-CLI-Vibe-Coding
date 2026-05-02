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
