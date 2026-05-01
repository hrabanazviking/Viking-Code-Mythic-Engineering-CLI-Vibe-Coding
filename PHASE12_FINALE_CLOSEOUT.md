# PH-12 — Phase Finale Close-out (2026-05-01)

**Branch:** `development`
**Final HEAD:** `0bf5250` (this memo will land the next commit)
**Resume from:** `ea58326` (PH-11 finale)

PH-12 adds first-class CI/CD touchpoints: workflow generation,
automated containerisation, semantic versioning, and rollback
support. All 4 slices shipped in order; working tree clean,
every commit pushed, every existing test still passes (after
two expected updates for the new commands in registry-inventory
tests).

---

## What landed

| Slice | Title | Commit | Net |
|---|---|---|---|
| TASK file | — | `eb81493` | +132 lines |
| 12.1 | `mythic-vibe ci scaffold` | `4bfed63` | +787 lines, +32 tests |
| 12.2 | `mythic-vibe docker scaffold` | `8afc59e` | +535 lines, +13 tests |
| 12.3-12.4 | release + rollback (bundled) | `0bf5250` | +1156 lines, +38 tests |

**Test delta:** 1369 → 1452 (+83 net).
**Coverage:** 76% (held).
**Lint / type:** clean throughout.

---

## Capability summary

### Slice 12.1 — `mythic-vibe ci scaffold`

`mythic_vibe_cli/cicd/stack_detector.py` returns a typed
`DetectedStack` from a manifest-first inspection — pyproject /
package.json / Cargo / go.mod / pom.xml / Gemfile. Captures
Python tooling (test_runner, linters, min_version), Node
package manager (npm/yarn/pnpm via lockfile), and presence
flags for the rest.

`mythic_vibe_cli/cicd/ci_scaffold.py` renders
`.github/workflows/ci.yml` with five per-language templates:
python (matrix + conditional ruff/mypy/pytest), node (matrix +
package-manager-aware install), rust (clippy + fmt + test), go
(vet + test), and an unknown TODO scaffold. Honours `--force`
and `--dry-run`.

### Slice 12.2 — `mythic-vibe docker scaffold`

Three-file generator:
- Dockerfile (multi-stage per language: python:3.12-slim,
  node:20-alpine, rust:1.79-slim → debian:bookworm-slim,
  golang:1.22-alpine → distroless/base-debian12).
- .dockerignore — security-aware default-deny (.env, *.pem,
  *.key, *.token, mythic/) plus standard build/cache exclusions.
- docker-compose.yml — single-service scaffold with TODO comments
  for ports / volumes / env.

Per-file `--force` and `--dry-run` granularity via the
`DockerScaffoldFile` records.

### Slice 12.3 — `mythic-vibe release`

Semver-aware release helper. `Version` dataclass with
`parse()`/`bump()`. `read_pyproject_version()` /
`write_pyproject_version()` use a targeted regex replace over
the `[project] version` line so we don't need a full TOML
round-tripper.

`prepare_release()` orchestrates:
- Dry-run by default (no writes).
- `--apply` writes the new version to `pyproject.toml`.
- `--tag` (in addition to `--apply`) creates a local git tag
  via `subprocess.run(["git", "tag", ...])`.
- **Never pushes.** Operators own the publish step. Defense in
  depth — `git push` is in the global "risky actions" list and
  the release helper has no path to it.

CLI: `mythic-vibe release [--bump patch|minor|major] [--apply]
[--tag] [--summary "..."]`.

### Slice 12.4 — Rollback summariser

`summarise_rollback(root, since_ref)` walks
`git log <ref>..HEAD` and `git diff --name-only <ref>..HEAD`,
returning a typed `RollbackReport` (commits, files, notes,
error).

Custom `\x1f` (Unit Separator) delimiter on the git-log format
string so commit subjects with `|` characters don't break the
parser.

**Read-only:** the helper never reverts anything. Output
explicitly reminds operators to run `git revert <sha>` or
`git reset --hard <ref>` themselves.

CLI: `mythic-vibe rollback --since <ref> [--json]`.

---

## Master-roadmap impact

PH-12 closed. All 4 slices shipped:
- 12.1 CI scaffold ✓
- 12.2 Docker scaffold ✓
- 12.3 Release helper ✓
- 12.4 Rollback summariser ✓

**Phases now fully closed:** PH-01, PH-02, PH-03, PH-04, PH-05,
PH-06 (5/6), PH-07, PH-08, PH-09, PH-10, PH-11, **PH-12**, PH-13,
PH-15. (14 of 20 — 70% of roadmap.)

PH-12 unblocks no other phase directly — pure capability
addition. Remaining phases: **PH-14 (Policy Engine — newly
unblocked by PH-11)**, PH-16 (MCP/ACP/OpenTelemetry), PH-17
(Multi-Surface Access), PH-18 (Robustness Sweeps), PH-19
(Distribution), PH-20 (v1.0.0 Sovereign OS Launch).

**Recommended next move:** PH-14 (Policy Engine & Constraint
Verification) — the natural follow-on. PH-11's typed `*Policy`
dataclasses and `security audit` aggregator are the building
blocks for a richer policy engine. PH-19 (Distribution) is an
alternative if you want the release helper exercised through
PyPI publish pipelines first.

---

## Operational notes

- Every PH-12 capability is **additive**. No existing flow was
  altered; the four new commands plug into the same argparse +
  slash-command + dispatcher machinery as the rest of the CLI.
- Generated artefacts always land at convention paths
  (.github/workflows/ci.yml, Dockerfile, etc) and never
  overwrite existing files without `--force`.
- `git push` is never invoked from any PH-12 helper — operators
  own the publish step. This is enforced at the module level
  (the helpers simply do not have the call site).
- Memory updated incrementally after each slice (per the
  durable rule about not batching).
- No new ADRs required — PH-12 adds capabilities, not new
  boundaries.
