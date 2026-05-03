# Compatibility Policy

**Effective:** 2026-05-02 (Phase 19.6, audit remediation cycle)
**Applies to:** the published `mythic-vibe-cli` package on PyPI,
Homebrew, and Scoop, starting with v1.0.0.

This document is a contract with operators. Anything promised
here is enforced by CI (matrix, smoke tests, deprecation
linting); anything outside the promise is "best effort, may
change without notice." When in doubt, the test matrix in
`.github/workflows/ci.yml` is the authoritative source — this
doc is the human-readable summary of the same intent.

---

## 1. Python version support

| Tier | Versions | Support level |
|------|----------|---------------|
| **Tested** | 3.10, 3.11, 3.12 | Every PR runs the full test suite on each version, on every OS in §2 |
| **Targeted** | 3.13 | Listed in `pyproject.toml` classifiers; not yet in CI matrix (added in a follow-up PH-20 slice once GitHub Actions runners stabilise on 3.13) |
| **Best effort** | 3.14+ | Will likely work — we use no Python-version-specific syntax beyond what 3.10 already provides — but we do not test it before release |
| **Unsupported** | 3.9 and older | `pyproject.toml` declares `requires-python = ">=3.10"`. pip will refuse to install on older interpreters |

### Drop / add cadence

- **Adding a new Python minor:** within 90 days of its `.0`
  stable release, the new version is added to the CI matrix.
  No code change is required to declare support — CI being
  green is the support signal.
- **Dropping an old Python minor:** we follow upstream
  Python's end-of-life dates. A version is considered
  candidate-for-drop once its upstream EOL is announced
  (typically ~5 years after `.0` release). Actual drop happens
  in the next minor release after EOL, with one full minor
  cycle of deprecation warning.

---

## 2. Operating system support

The CI matrix in `.github/workflows/ci.yml` runs the full test
suite on every (OS × Python) combination listed below:

| OS | Architectures | Notes |
|----|---------------|-------|
| Linux (Ubuntu 24.04 LTS) | x86_64, aarch64 | Primary development target. The aarch64 row covers Pi 5 / Pi Zero hardware profiles documented in `docs/hardware_profiles.md` |
| macOS (latest GitHub-Actions runner) | x86_64 (Intel) + arm64 (Apple Silicon, when runner available) | Tested via `macos-latest` |
| Windows (Server 2022, latest runner) | x86_64 | Tested with PowerShell as the primary shell context |

### Out-of-band platforms

We do **not** routinely test the following and will accept bug
reports as best-effort:

- BSD family (FreeBSD / OpenBSD / NetBSD).
- Linux on platforms other than glibc (e.g. Alpine / musl).
- WSL1 (WSL2 is treated as plain Linux).
- macOS versions older than the GitHub Actions `macos-latest`
  baseline.
- Windows on ARM (no Actions runner is currently available).

When such a report comes in, we triage based on (a) is the bug
in code we own vs in stdlib + platform interaction, and (b)
does fixing it require platform-specific code that would need
its own CI lane. Platform-specific fixes that don't break the
supported tiers are welcomed; ones that do are deferred.

---

## 3. Public surface

The "public surface" — everything we promise stability for —
consists of:

| Surface | Stability tier |
|---------|----------------|
| `mythic-vibe` and `mythic` console scripts | **Stable** — names + top-level subcommand verbs are SemVer-stable from 1.0.0 |
| Subcommand argparse flags | **Stable** — no breaking flag rename / removal without deprecation cycle |
| `--json` output schemas | **Stable** — the snapshot tests at `tests/snapshots/` lock these. Field additions are non-breaking; removals or type changes require a major version |
| Exit codes (`mythic_vibe_cli/exit_codes.py`) | **Stable** — codes are part of the contract (CI / scripted callers depend on them) |
| `mythic/status.json` schema | **Stable** — `core/state.py:CURRENT_STATE_SCHEMA_VERSION`; bumps run through `persistence/migrations.py` with backups + property-test coverage (see PH-19.4) |
| `mythic_vibe_cli` Python module imports | **Internal** — direct `from mythic_vibe_cli...` imports are not supported. We do not promise import-path stability for library use; the CLI is the API |
| Plugin extension points (`plugins/extension_points.py`) | **Stable** — extension-point names + signatures are SemVer-stable. Plugins built against a `1.x` MAY assume they keep working through all `1.x` releases |
| File-system layout under `mythic/` | **Stable** — paths and naming conventions are part of the operator contract |
| **Hermes Agent surface** (`mythic_vibe_cli.agent_api`, v1.0) | **Stable** — the 18 default tool names + their input-schema shapes, the HTTP endpoint paths + auth contract, the `HermesAgent` / `HermesCore` / `ToolSpec` / `Invocation` / `InvocationResult` Python class names + signatures. New tools may be added (MINOR); existing fields may be added (MINOR); removals or type changes require MAJOR + the documented deprecation cadence. See [`docs/HERMES_AGENT.md`](HERMES_AGENT.md) §7 for the full enumeration |

Anything not listed above is internal and may change without
notice. In particular: undocumented helper modules, internal
test fixtures, sandbox internals, and AI-provider-specific
tuning constants.

---

## 4. SemVer interpretation

We follow [Semantic Versioning 2.0.0](https://semver.org/) with
these specific interpretations:

- **MAJOR** — breaking change to anything in the §3 "Stable"
  tier. Examples: subcommand removal, JSON schema field type
  change, exit-code reuse, status.json schema break that the
  migration cannot transparently handle.
- **MINOR** — additive new functionality on the public surface.
  Examples: new subcommand, new flag (with a sane default), new
  optional JSON field, new plugin extension point. Existing
  callers are unaffected.
- **PATCH** — bug fix, performance improvement, internal-only
  change, doc update, dependency floor bump within an existing
  major. No public-surface change.

**Pre-1.0:** versions in the `0.x.y` range follow these same
rules but with one extra freedom — `0.x` to `0.(x+1)` is
allowed to break stable surfaces. From `1.0.0` onward, the
SemVer contract is binding.

---

## 5. Deprecation cadence

When we need to remove a public surface:

1. **Announce.** The changelog entry adds a `Deprecated:` line.
   Runtime starts emitting a `DeprecationWarning` to stderr
   (suppressible per Python's standard warning filter).
2. **Wait.** A full minor version cycle (~3-6 months) passes
   with the deprecation warning live. Users get at least one
   release where they can fix their integration without their
   workflow breaking.
3. **Remove.** The next major version drops the surface. The
   changelog entry restates the removal under `Removed:` and
   links back to the original `Deprecated:` notice.

We never remove a stable surface in a patch release. We never
remove a stable surface without a prior minor-release
deprecation warning.

---

## 6. Dependency policy

- **Runtime base** — `pyproject.toml` `[project.dependencies]`
  is empty. The CLI works against pure stdlib for its core
  functionality. This minimises supply-chain surface.
- **Optional features** — declared via extras
  (`[ai]`, `[otel]`, `[ux]`, `[tui]`, etc.). Each extra is
  opt-in; the lower bound is pinned in `pyproject.toml`. Upper
  bounds are NOT pinned — operators can upgrade transitive deps
  without waiting for us to bless each release.
- **Floor bumps** are PATCH if the lower bound rises within a
  major (e.g. `>=8.0` → `>=8.5`); MINOR if a new optional
  surface introduces a new dep family.
- **SBOM** at `docs/security/sbom.json` (regenerated each
  release via `scripts/regenerate_sbom.py`) is the
  authoritative inventory of every transitively-installed
  package for the documented extras.

---

## 7. Configuration & env-var compatibility

Operator-facing environment variables (`MYTHIC_*`) are part of
the stable surface. Renaming one requires a deprecation cycle
per §5: the old name keeps working with a warning for one
minor cycle, then is removed in the next major.

The current `MYTHIC_*` set is enumerated in:

- `mythic_vibe_cli/config.py` (resolution layer)
- `docs/INSTALL.md` (operator-facing)

Project-local config files (`mythic/security.toml`,
`mythic/config.toml`, etc.) follow the same SemVer contract as
JSON schemas: field additions are non-breaking; renames /
removals require a deprecation cycle; type changes require a
major.

---

## 8. Verification

This policy is enforced mechanically wherever possible:

- §1 (Python versions) — `.github/workflows/ci.yml` matrix.
- §2 (OS support) — same matrix.
- §3 (JSON schemas) — `tests/snapshots/*.json` (PH-19.1).
- §3 (CLI verbs documented) — `tools/contract_audit.py`
  (PH-19.2).
- §3 (status.json schema) — `tests/property/test_state_migrations.py`
  (PH-19.4).
- §6 (SBOM) — `tests/test_sbom_committed.py` (PH-19.5).

Anything that drifts from the policy in code-review-only fashion
(deprecation cycle skipped, surface dropped without notice,
etc.) is a process failure, not a tooling failure. The release
checklist in `docs/RELEASE_CHECKLIST.md` includes a manual
"compatibility-policy review" step for every release.

---

## 9. Update procedure

Edits to this document follow the same additive-only rule that
governs the rest of the project: changes are appended as dated
revision blocks under §10 below, with the relevant tier table
updated in place. We do not silently rewrite history — operators
reading an older release's docs should be able to see what the
contract was at that release.

---

## 10. Revision history

- **2026-05-02 — v1.0** (Phase 19.6 closeout)
  Initial publication. Tiers, cadences, and verification
  pointers all match the state of the repo at HEAD `17c6df4`
  (post-PH-19.5).
