# Cross-Platform Expansion Plan (Windows, Linux, macOS, Android, Raspberry Pi, and Beyond)

**Status:** Proposed multi-phase program  
**Date:** 2026-05-02  
**Scope:** Active CLI runtime (`mythic_vibe_cli/`) plus packaging, distribution, CI/CD, and deployment surfaces.

---

## Executive Summary

This plan turns the current Python CLI into a robust cross-platform product line with predictable behavior across:

- **Desktop:** Windows, Linux, macOS
- **Mobile-adjacent:** Android via Termux and optional native wrapper strategy
- **Edge/Embedded:** Raspberry Pi (Pi OS arm64/armv7) and similar ARM Linux SBCs
- **Future targets:** Container-native, WASI experiments, and plugin-hosted execution surfaces

The strategy is intentionally staged. Early phases focus on compatibility hardening and reproducible packaging; later phases add performance, platform-native polish, and operational maturity.

---

## Current State Snapshot (What Exists Today)

From the repository docs and structure, the project already has a strong base for cross-platform expansion:

1. Install instructions for Windows, Linux, and macOS exist.  
2. Entrypoint and architecture boundaries are explicit (`mythic_vibe_cli` as active runtime).  
3. There are governance docs and release checklist patterns that can be extended into platform release trains.

This is excellent groundwork; the gaps are mostly around advanced packaging, platform-specific QA matrices, Android/Pi hardening, and long-term binary/distribution ergonomics.

---

## Design Principles for Cross-Platform Success

1. **Single behavioral contract, many transport layers.**  
   Keep command semantics consistent; vary installer, packaging, and runtime adapter by platform.

2. **Deterministic builds and reproducible environments.**  
   Prefer pinned dependencies, lock files, and reproducible CI targets.

3. **Progressive enhancement.**  
   Baseline portable mode first (pure Python CLI), then optional acceleration/native wrappers.

4. **Fail loudly with actionable diagnostics.**  
   Platform detection + explicit fallback messaging reduces support burden.

5. **Treat ARM as first-class.**  
   Cross-platform now means x86_64 + arm64 + armv7 coverage.

---

## Multi-Phase Plan

## Phase 0 — Discovery, Contract Lock, and Compatibility Audit

**Goal:** Produce a factual compatibility baseline and risk register before changing core behavior.

### Actions

- Build a command inventory with OS-sensitive risk tags (filesystem paths, shell calls, encoding, terminal behavior, subprocess assumptions).
- Add a platform capability matrix document covering:
  - shell/terminal assumptions,
  - filesystem behaviors,
  - dependency wheel availability per architecture,
  - permissions model differences.
- Define supported tiers:
  - Tier 1: full support (Windows/macOS/Linux x86_64+arm64)
  - Tier 2: validated community support (Raspberry Pi, Android/Termux)
  - Tier 3: experimental.

### Deliverables

- `docs/platform_support_matrix.md`
- `docs/platform_risk_register.md`
- Updated `docs/RELEASE_CHECKLIST.md` with platform gates.

### Exit Criteria

- Every CLI command is tagged with compatibility risk level.
- No ambiguous “works on my machine” zones remain undocumented.

---

## Phase 1 — Runtime Portability Hardening (Code-Level)

**Goal:** Make the active runtime path-clean, encoding-safe, and shell-agnostic.

### Actions

- Standardize on `pathlib` and avoid shell-specific path concatenation.
- Normalize line endings and text encoding handling (`utf-8` with explicit error strategy where needed).
- Replace shell-dependent flows with Python-native equivalents where possible.
- Harden temp-file + atomic write behavior for Windows locking semantics.
- Add platform-aware abstractions for:
  - opening files/editors,
  - command completion setup hints,
  - process invocation.

### Deliverables

- Refactors in `mythic_vibe_cli/` reducing OS conditionals.
- New utility module for platform detection and capability negotiation.

### Exit Criteria

- All existing tests pass on Linux, macOS, Windows.
- No command hard-fails due to path separator or shell dependency.

---

## Phase 2 — Packaging and Distribution Strategy

**Goal:** Offer clean install paths for each target platform without changing command UX.

### Recommended Packaging Tracks

1. **Python-native (baseline):** PyPI + pip/pipx/uv (already partially present).
2. **Single-file executables:** PyInstaller / Nuitka builds for users without Python.
3. **OS package managers:**
   - Windows: Scoop/WinGet manifest
   - macOS: Homebrew tap
   - Linux: pipx + optional distro packages (AUR, .deb/.rpm community path)
4. **Container image:** minimal OCI image for CI agents and remote runners.

### Actions

- Publish a canonical dependency lock strategy per Python minor version.
- Produce reproducible build scripts for each package target.
- Add signed artifacts and checksums.

### Deliverables

- `docs/packaging_strategy.md`
- CI release workflows producing multi-platform artifacts.

### Exit Criteria

- One-command install path verified on each Tier 1 platform.
- Checksummed/signed artifacts published per release.

---

## Phase 3 — CI Matrix and Automated Verification at Scale

**Goal:** Prevent regressions by continuously testing real platform combinations.

### Actions

- Expand CI matrix by OS + architecture + Python version.
- Add smoke tests for install + `--help` + key workflow commands.
- Add snapshot tests for output stability across terminal environments.
- Include arm64 runners (native where possible; emulation only as fallback).

### Suggested Matrix (Initial)

- Windows: 11, Python 3.10/3.11/3.12
- Ubuntu: LTS, Python 3.10/3.11/3.12
- macOS: latest + previous major, universal coverage focus
- Linux arm64: native runner for packaging/tests

### Deliverables

- CI templates/workflows + platform smoke-test harness.

### Exit Criteria

- Green matrix on every merge to main branch.
- Release blocked automatically on matrix failures.

---

## Phase 4 — Android and Mobile-Terminal Enablement

**Goal:** Provide a first-class Android usage mode without overcommitting to full native app complexity.

### Strategy A (Fastest): Termux-first support

- Official Termux install guide.
- Tested dependency set and constrained feature profile.
- Storage permission + filesystem path guidance.

### Strategy B (Mid-term): Native wrapper shell

- Thin Android app wrapper hosting CLI runtime (via embedded Python/runtime layer).
- Focus on command presets, logs, and task execution views.

### Actions

- Detect Android/Termux runtime and adjust defaults (cache dirs, temp dirs, editor behavior).
- Provide offline-friendly docs bundles and examples.

### Deliverables

- `docs/ANDROID_TERMUX.md`
- Optional `docs/android_wrapper_architecture.md`

### Exit Criteria

- Documented, repeatable install and run path on Android (Termux).
- Core command set validated on a maintained Android test device matrix.

---

## Phase 5 — Raspberry Pi / ARM Edge Optimization

**Goal:** Make Raspberry Pi a dependable supported environment for local/offline workflows.

### Actions

- Validate on Pi OS (arm64 + armv7 where feasible).
- Produce performance profile for low-RAM modes.
- Add lightweight profile flags (reduced concurrency, compact logs, optional feature toggles).
- Ensure wheels/dependencies are available or offer source-build fallback docs.

### Deliverables

- `docs/RASPBERRY_PI.md`
- `docs/hardware_profiles.md` additions for Pi classes.

### Exit Criteria

- Stable execution on target Pi profiles with documented performance expectations.
- Clear troubleshooting playbook for ARM-specific issues.

---

## Phase 6 — Platform-Native UX and Integration Layer

**Goal:** Improve ergonomics and adopt platform conventions while retaining one logical CLI API.

### Enhancements

- Windows:
  - PowerShell-first completion/profile scripts,
  - WinGet and signed binaries,
  - native path UX and long-path safeguards.
- macOS:
  - Homebrew reliability, notarization/signing path for binaries.
- Linux:
  - clean XDG paths, distro-friendly config/data layout.
- All platforms:
  - richer diagnostics command output (`mythic-vibe doctor`) with platform hints.

### Exit Criteria

- Support ticket categories for “install/runtime setup issues” reduced release-over-release.

---

## Phase 7 — Reliability, Security, and Supply-Chain Hardening

**Goal:** Ensure cross-platform scale does not degrade trust.

### Actions

- SBOM generation for release artifacts.
- Dependency vulnerability scanning in CI.
- Reproducible build attestations.
- Signed tags + signed release artifacts.
- Security response process for platform-specific vulnerabilities.

### Exit Criteria

- Every release includes provenance artifacts and vulnerability status.

---

## Phase 8 — Long-Term Evolution Options

**Goal:** Keep future portability options open.

### Strategic Options

1. **Rust/Go launcher shim** around Python runtime for stronger binary UX.
2. **Plugin-host model** for platform adapters.
3. **WASM/WASI experimental runtime** for browser/sandbox use cases.
4. **Hybrid architecture**: core orchestration protocol separated from CLI transport.

These options are not required for near-term success but can reduce long-term operational and support cost.

---

## Cross-Platform Techniques Catalog (Concrete Recommendations)

1. Use `pathlib`, `platform`, `shutil.which`, and explicit env var fallbacks.
2. Keep all paths relative to a deterministic app data root per OS.
3. Avoid shell-script-only installation logic; mirror with Python commands.
4. Detect interactive vs non-interactive terminals and degrade gracefully.
5. Provide “portable mode” with minimal dependencies.
6. Split optional heavy dependencies into extras (e.g., `[ux]`, `[dev]`, `[android]`, `[pi]`).
7. Add a `doctor` command with targeted platform diagnostics.
8. Ship preflight checks before critical workflows.
9. Use structured error codes and remediation hints per platform.
10. Publish known-good version bundles (Python + package + optional deps).
11. Provide offline install docs and wheelhouse strategy for constrained devices.
12. Maintain a compatibility changelog section every release.

---

## Suggested Backlog (First 12 High-Impact Tasks)

1. Author platform support matrix and tier policy.
2. Add platform detection helper module.
3. Implement robust path/data-dir abstraction.
4. Add Windows file-lock/atomic write tests.
5. Build CI matrix across Tier 1 platforms.
6. Add Linux arm64 runner coverage.
7. Produce Android Termux quickstart and smoke tests.
8. Produce Raspberry Pi install + optimization guide.
9. Add `mythic-vibe doctor` platform diagnostics.
10. Implement release artifact signing and checksum publication.
11. Add pipx/uv install smoke tests in CI.
12. Publish binary packaging PoC (single-file executable).

---

## Success Metrics

Track these metrics per release:

- Install success rate by platform.
- Time-to-first-successful-command (TTFSC).
- Platform-specific bug incidence per 1,000 users.
- CI matrix pass rate and flaky-test rate.
- Median command latency on desktop vs Raspberry Pi.
- Support ticket volume tagged by platform category.

---

## Recommended Governance Additions

- Add **Platform Compatibility Owner** rotation.
- Require platform impact note in PR template.
- Require “tested on” metadata for runtime changes.
- Add quarterly platform deprecation/upgrade policy review.

---

## Implementation Order Recommendation

If you want maximum impact quickly:

1. **Phase 0 + 1 + 3 first** (compatibility audit, hardening, CI matrix).
2. **Phase 2 next** (packaging/distribution confidence).
3. **Phase 4 + 5** (Android + Raspberry Pi practical support).
4. **Phase 6+** once baseline reliability and install success are stable.

This sequence gives the highest reduction in cross-platform breakage risk per unit effort.
