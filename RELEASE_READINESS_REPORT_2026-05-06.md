# Release-Readiness Report — Mythic Vibe CLI

**Generated:** 2026-05-06 by Runa Gridweaver Freyjasdottir, on Volmarr's behalf during the autonomous PH-24 hardening run.
**Branch:** `development`
**HEAD:** `ce9f1ad` (PH-24.6 documentation completeness)
**Tag baseline:** `v1.0.0` at `bf01cfb` (released 2026-05-03)

This document is the slice 24.7 closeout — the final release-readiness smoke. It records what works today, what is gated on operator action, and what remains as known limitations the next session should respect.

---

## Quality gate (this commit)

| Gate | Result |
|---|---|
| `ruff check mythic_vibe_cli/ tests/` | All checks passed |
| `mypy mythic_vibe_cli/` | Success: no issues found in 157 source files |
| `pytest tests/` | **2751 passed, 2 skipped, 109 subtests** in 126 s |
| Aggregate line+branch coverage | **85%** (statement-only: **87.3%**) |
| Files at ≥95% coverage | **75 / 157** (was 5 of 156 at PH-24.1 kickoff) |
| Open audit findings (Critical / High) | **0 / 0** |
| Open audit findings (Medium) | **0** (all closed by 24.1.fix-1) |

---

## Smoke commands run

The following CLI surface invocations all completed cleanly:

| Command | Result |
|---|---|
| `mythic-vibe --version` | `mythic-vibe 1.0.0` |
| `mythic-vibe ai providers --json` | 9 providers registered |
| `mythic-vibe hardware --json` | Full HardwareProfile (OS / CPU / RAM / arch / platform_tags) |
| `mythic-vibe hermes tools --json` | 18 curated agent tools |
| `python -m pytest tests/` | 2751 passed |

Note: `mythic-vibe doctor` is intended to validate **Mythic projects**, not the CLI source repo. Running it on the CLI's own working tree surfaces "missing required file" errors for `SYSTEM_VISION.md` etc. — this is expected and not a release blocker.

---

## What changed since v1.0.0

Commit-by-commit on `development`, in order:

```
bf01cfb  v1.0.0 release commit (2026-05-03)
352b7d1  Hermes Agent control plane (post-v1.0)
... (PH-21 v1.x distribution: 9 slices, 6 new channels)
... (PH-22 v2.0 stretch: 3 foundations — launcher / android / wasi)
... (PH-23 polish: 16 slices)
... (cross-project housekeeping: pygame Phase 1E + 1F + 2A; MindSpark utils; NSE)
ec87338  README + CHANGELOG + docs/INDEX comprehensive doc refresh
90e41b4  packaging/README intro modernization
796a16c  PH-24 task kickoff
c6e4655  PH-24.1 audit (14 findings)
8bf5d4f  PH-24.1.fix-1 (RUF012 + B905 + B010)
38b139d  PH-24.2 part 1 (anthropic + gemini + plunder/github + tcl coverage)
a59e473  PH-24.2 part 2 (http_api error paths)
8cf51c0  PH-24.3 (atomic_write + cross_process_lock cleanup paths)
0a1e972  PH-24 cumulative session log
798e742  PH-24.4 byte-stable artifacts (Windows newline-translation fix)
7b67443  PH-24.5 url-scheme guard (12 urlopen sites)
ce9f1ad  PH-24.6 documentation completeness (env vars + CHANGELOG)
HEAD     this report (PH-24.7)
```

Cumulative since v1.0.0: **2658 → 2751 tests** (+93), aggregate coverage **84% → 85%**, modules at ≥95% **5 → 75** (the big jump is from earlier PH-21/22/23 small-module slices, not just PH-24).

---

## Operator-side blockers still gating a v1.0.1 tag

The release pipeline is complete and tested. The remaining blockers are operator-side configuration that requires Volmarr's authentication context. None of them are CLI defects.

| Blocker | What | Where | Effort |
|---|---|---|---|
| GitHub Pages | Enable for the docs site to actually serve | repo Settings → Pages → Source: GitHub Actions | 1 click |
| AUR repo | Provision `aur-mythic` maintainer repo + `AUR_BUMP_TOKEN` secret | aur.archlinux.org + repo Secrets | ~15 min |
| winget repo | Provision `winget-mythic` maintainer repo + `WINGET_BUMP_TOKEN` secret | github.com/microsoft/winget-pkgs fork + repo Secrets | ~15 min |
| Android keystore | Generate keystore + add 4 secrets (`ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`) | follow `packaging/android/SIGNING.md` | ~10 min |
| PBS SHA256 table | Run `python tools/fetch_pbs_checksums.py` and paste output into `packaging/launcher/src/main.rs:PBS_EXPECTED_SHA256` | repo edit | ~5 min |

After those five operator-side items, `git tag -s v1.0.1 && git push origin v1.0.1` runs the seven-workflow release pipeline end-to-end with full Sigstore + SLSA provenance.

---

## Known limitations (not regressions)

These existed in v1.0.0 and remain. They are intentionally not in scope for this hardening cycle.

- **Doctor on tool repo.** Running `mythic-vibe doctor` on the CLI's own source tree errors because the CLI source isn't a Mythic project. Operators encountering this are looking at the wrong directory; documenting this in the doctor's error message is a future polish slice.
- **POSIX-only branches uncovered.** The Linux/macOS branch of `runtime/cross_process_lock.py` (`fcntl.flock` path) is unreachable on a Windows test host; the CI matrix exercises it on Ubuntu + macOS runners, but the local pytest run cannot reach it.
- **Long-path support on Windows.** The cross-platform regression test for long Windows paths (>260 chars) is permissive — it accepts either successful write OR a clean OSError, because some CI hosts have aggressive path-length limits even when the OS supports long paths.
- **Operator-side WASI execution.** PH-22.3's WASI runtime is foundation-level. The cross-build pipeline produces a `python.wasm` + `.pyz` zipapp; the browser playground (PH-23.16) currently uses a JS stub for command execution. Real `@bjorn3/browser_wasi_shim` integration is a future slice.

None of the above gate v1.0.1 — they're documented in the relevant module READMEs.

---

## Recommendation

The codebase is **production-ready** for v1.0.1 from a code-quality perspective:
- 0 Critical / High audit findings
- 1 real cross-platform defect found AND fixed during this hardening run (Windows newline translation)
- Defence-in-depth url-scheme guard added to all 12 urlopen sites
- 2751 tests, ruff + mypy clean
- 75 of 157 modules at ≥95% coverage

The release should ship once the five operator-side blockers above are completed — they are not code changes, they are credential / repo provisioning steps Volmarr's hands need to perform.

---

## Resume contract

If the autonomous run is interrupted before this report is written, the next session resumes by:

1. Reading `TASK_PH24_PRE_RELEASE_HARDENING.md` for the slice plan + per-slice status updates.
2. Reading `AUDIT_PRE_RELEASE_HARDENING_2026-05-05.md` for the original 14 findings.
3. Reading this report for the final smoke + operator-side blocker list.
4. Running `git log --oneline -20` to confirm HEAD matches the records here.

If new defects surface in subsequent sessions, append a new dated section to this report rather than mutating the existing record. Continuity is maintained by the additive-only rule (`feedback_additive_only.md`).
