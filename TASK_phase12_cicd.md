# TASK — PH-12 CI/CD & Deployment Integration

**Created:** 2026-05-01
**Branch:** `development`
**Operator:** Volmarr
**Resume from:** HEAD `ea58326` (PH-11 finale)

PH-12 adds first-class CI/CD touchpoints — workflow generation,
automated containerisation, semantic versioning, and rollback
support.

**Master roadmap dependency:** `[PH-01, PH-11]` — both closed.

---

## Slice 12.1 — `mythic-vibe ci scaffold`

**Goal:** generate a `.github/workflows/ci.yml` tuned to the
detected tech stack. Re-uses the slice-2 / slice-5 scanner +
indexer to detect languages and key tooling
(pyproject.toml + ruff/mypy/pytest, package.json + npm scripts,
Cargo.toml, go.mod, etc).

**Files:**
- `mythic_vibe_cli/cicd/__init__.py` (new package).
- `mythic_vibe_cli/cicd/stack_detector.py` (new) — pure
  detector returning a typed `DetectedStack` dataclass.
- `mythic_vibe_cli/cicd/ci_scaffold.py` (new) — template
  renderer.
- `mythic_vibe_cli/commands.py` — `cmd_ci_scaffold` +
  dispatcher.
- `mythic_vibe_cli/app.py` — `mythic-vibe ci scaffold`
  argparse subcommand.
- Tests.

**Acceptance:**
- Detects Python / JS-TS / Rust / Go / multi-language repos.
- Honours `--force` to overwrite + `--dry-run` to preview.
- Generated YAML is valid (parseable via stdlib alternative or
  reasonable string assertions in tests).

**Progress:** [ ] not started

---

## Slice 12.2 — `mythic-vibe docker scaffold`

**Goal:** produce `Dockerfile`, `.dockerignore`, and
`docker-compose.yml` tuned to the detected stack.

**Files:**
- `mythic_vibe_cli/cicd/docker_scaffold.py` (new).
- `mythic_vibe_cli/commands.py` — `cmd_docker_scaffold`.
- argparse + tests.

**Acceptance:**
- Python projects get a multi-stage Dockerfile with pip install.
- Node projects get a multi-stage Dockerfile with npm install.
- `--force` and `--dry-run` honoured.

**Progress:** [ ] not started

---

## Slice 12.3 — `mythic-vibe release`

**Goal:** semver-aware release command. Bumps version in
`pyproject.toml` (or whichever manifest is detected), creates a
git tag, prepares the CHANGELOG entry. **No git push by default
— operator owns the publish step.**

**Files:**
- `mythic_vibe_cli/cicd/release.py` (new) — version bump +
  changelog rendering.
- `mythic_vibe_cli/commands.py` — `cmd_release`.
- argparse + tests.

**Default behaviour:** dry-run unless `--apply` is set. The
command never pushes to a remote unless `--push` is explicitly
passed (defense in depth — git push is in our risky-action
list).

**Acceptance:**
- `mythic-vibe release --bump patch` previews the version
  change + tag name + changelog stub.
- `--apply` writes the version bump and creates the tag (still
  no push).
- Honours major/minor/patch bumps.

**Progress:** [ ] not started

---

## Slice 12.4 — Rollback helper

**Goal:** `mythic-vibe rollback --since <ref>` summarises commits
+ files-touched between `<ref>` and HEAD so operators know what
to revert if a release misbehaves.

**Files:**
- `mythic_vibe_cli/cicd/rollback.py` (new).
- `mythic_vibe_cli/commands.py` — `cmd_rollback`.
- argparse + tests.

**Read-only:** the helper never reverts anything itself; it just
reports what would be in scope. Operator runs the actual revert
manually.

**Progress:** [ ] not started

---

## Phase finale

After all 4 slices ship:

- `PHASE12_FINALE_CLOSEOUT.md` — summary memo.
- Update memory + status file.
- Push.

---

## Operational notes

- ME laws apply: stdlib-first, optional deps via try-import,
  default-off feature gates, cross-platform.
- Generated artefacts go where convention dictates
  (`.github/workflows/ci.yml`, `Dockerfile`, etc) — no project
  config files moved or renamed.
- All scaffold commands honour `--force` (overwrite) and
  `--dry-run` (preview only).
- After each slice: update memory + status file immediately.
