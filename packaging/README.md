# Packaging

This directory holds everything the release pipeline needs to
publish Mythic Vibe CLI to its three distribution channels:

| Channel | Files | Workflow integration |
|---------|-------|---------------------|
| PyPI | (built from `pyproject.toml` directly) | OIDC trusted publishing — see `.github/workflows/release.yml` `publish-pypi` job |
| Homebrew tap (`homebrew-mythic`) | [`homebrew/mythic-vibe.rb.template`](homebrew/mythic-vibe.rb.template) | `update-homebrew` job in the release workflow opens a PR against the tap with `__VERSION__` + `__SDIST_SHA256__` substituted |
| Scoop bucket (`scoop-mythic`) | [`scoop/mythic-vibe.json.template`](scoop/mythic-vibe.json.template) | `update-scoop` job opens a PR against the bucket with `__VERSION__` + `__WHEEL_SHA256__` substituted |

Plus an **offline-install wheelhouse** built into every release
(`mythic-vibe-cli-<VERSION>-wheelhouse.tar.gz`) for air-gapped
operators — see [WHEELHOUSE.md](WHEELHOUSE.md).

## Trigger semantics

The release workflow runs on:

- `push` of any `v*.*.*` tag → full release (build → publish to
  PyPI → GitHub Release → Homebrew + Scoop PRs).
- `workflow_dispatch` from the Actions UI → build-only rehearsal
  (no publish steps run).

Manual rehearsal mode is the safe way to verify a packaging
change without consuming a version number.

## Required repo secrets

| Secret | Purpose |
|--------|---------|
| `TAP_BUMP_TOKEN` | PAT with `contents:write` on `homebrew-mythic` repo for the auto-update PR |
| `BUCKET_BUMP_TOKEN` | PAT with `contents:write` on `scoop-mythic` repo for the auto-update PR |
| (none for PyPI) | Trusted publishing uses OIDC — no long-lived token needed; configured per-repo at https://pypi.org/manage/account/publishing/ |

## Defer / future channels

The compatibility policy (`docs/compatibility_policy.md`) lists
PyPI + Homebrew + Scoop as v1.0 channels. Two more channels are
**deferred to v1.x**:

- **AUR** (Arch User Repository) — needs a maintainer with an AUR
  account and PKGBUILD experience. Tracked as a v1.x stretch.
- **winget** — needs Microsoft Store / winget-pkgs PR flow.
  Tracked as a v1.x stretch.

When either lands, add a new template under
`packaging/<channel>/` and a corresponding job to
`.github/workflows/release.yml`.
