# Packaging

This directory holds everything the release pipeline needs to
publish Mythic Vibe CLI to its three distribution channels:

| Channel | Files | Workflow integration |
|---------|-------|---------------------|
| PyPI | (built from `pyproject.toml` directly) | OIDC trusted publishing — see `.github/workflows/release.yml` `publish-pypi` job |
| Homebrew tap (`homebrew-mythic`) | [`homebrew/mythic-vibe.rb.template`](homebrew/mythic-vibe.rb.template) | `update-homebrew` job in the release workflow opens a PR against the tap with `__VERSION__` + `__SDIST_SHA256__` substituted |
| Scoop bucket (`scoop-mythic`) | [`scoop/mythic-vibe.json.template`](scoop/mythic-vibe.json.template) | `update-scoop` job opens a PR against the bucket with `__VERSION__` + `__WHEEL_SHA256__` substituted |
| AUR maintainer repo (`aur-mythic`) | [`aur/PKGBUILD.template`](aur/PKGBUILD.template), [`aur/.SRCINFO.template`](aur/.SRCINFO.template) | `update-aur` job opens a PR against the maintainer repo with `__VERSION__` + `__SDIST_SHA256__` substituted; a human maintainer syncs to AUR proper (PH-21.7) |
| GHCR (always) + Docker Hub (opt-in) | [`Dockerfile`](../Dockerfile), [`.dockerignore`](../.dockerignore) | `release-oci.yml` workflow builds a multi-arch (linux/amd64 + linux/arm64) image via buildx + QEMU on tag push; pushes to `ghcr.io/<owner>/mythic-vibe-cli:<VERSION>` + `:latest`; mirrors to Docker Hub when the `DOCKERHUB_PUBLISH_ENABLED` repo variable is `true` (PH-21.1) |
| GitHub Release binaries (PyInstaller) | [`pyinstaller/mythic-vibe.spec`](pyinstaller/mythic-vibe.spec), [`pyinstaller/entrypoint.py`](pyinstaller/entrypoint.py) | `release-binaries.yml` workflow runs a per-OS matrix (Linux × Windows × macOS arm64 × macOS x86_64), invokes `pyinstaller mythic-vibe.spec`, smoke-tests each binary, attaches all four assets + their `.sha256` sidecars to the GitHub Release for the tag (PH-21.2) |
| GitHub Release binaries (Nuitka) | [`nuitka/build.py`](nuitka/build.py) | `release-binaries.yml` `build-nuitka` job runs the same 4-row OS matrix in parallel to the PyInstaller build, invokes `python packaging/nuitka/build.py`, smoke-tests each binary; assets named `mythic-vibe-nuitka-<VERSION>-<os>-<arch>` so operators distinguish the two binary flavors on the Release page (PH-21.3) |
| GitHub Release launcher (Rust) | [`launcher/Cargo.toml`](launcher/Cargo.toml), [`launcher/src/main.rs`](launcher/src/main.rs), [`launcher/README.md`](launcher/README.md) | `release-launcher.yml` workflow runs a 5-row arch matrix (Linux x86_64 + Linux aarch64 + macOS arm64 + macOS x86_64 + Windows x86_64), builds the Rust launcher with `cargo build --release`, runs `cargo test`, applies Sigstore + SLSA attestations, attaches binaries to the GitHub Release. The launcher is a small (~3-5 MB) shim that downloads python-build-standalone + the wheel on first run; subsequent runs short-circuit to the cached venv (PH-22.1, foundation level) |
| Android APK (Chaquopy) | [`android/`](android/) Gradle project + [`android/app/src/main/python/mythic_vibe_cli_android_runner.py`](android/app/src/main/python/mythic_vibe_cli_android_runner.py) | `release-android.yml` workflow runs `./gradlew assembleRelease` to produce an APK with CPython 3.12 + the mythic-vibe-cli wheel baked in via Chaquopy's `pip install` at build time. Compose-based single-activity UI invokes the CLI via JNI on Dispatchers.IO. Sigstore + SLSA attestation applied; min-SDK 26 (Android 8.0+); 4 ABIs covered (PH-22.2, foundation level) |
| WebAssembly (WASI) | [`wasi/build.py`](wasi/build.py), [`wasi/README.md`](wasi/README.md) | `release-wasi.yml` workflow runs `python packaging/wasi/build.py` to produce a `.wasm` artifact (foundation-level: emits a placeholder until the wasi-sdk + CPython WASI cross-build is wired in a future session); applies Sigstore + SLSA attestation; attaches to the GitHub Release. Reduced functional scope (subprocess-based commands disabled) documented in `wasi/README.md` (PH-22.3, foundation level) |
| winget maintainer repo (`winget-mythic`) | [`winget/mythic-vibe.installer.yaml.template`](winget/mythic-vibe.installer.yaml.template), [`winget/mythic-vibe.locale.en-US.yaml.template`](winget/mythic-vibe.locale.en-US.yaml.template), [`winget/mythic-vibe.yaml.template`](winget/mythic-vibe.yaml.template) | `update-winget` job resolves the PH-21.2 Windows binary URL + sha256 from the GitHub Release, renders the three winget v1.6 manifests with `__VERSION__` / `__WINDOWS_BINARY_URL__` / `__WINDOWS_BINARY_SHA256__` / `__RELEASE_DATE__` / `__RELEASE_NOTES_URL__` substituted, opens a PR against the maintainer repo; a human syncs to `microsoft/winget-pkgs` via wingetcreate or a manual fork PR (PH-21.8) |

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
| `AUR_BUMP_TOKEN` | PAT with `contents:write` on `aur-mythic` repo for the auto-update PR (PH-21.7) |
| `WINGET_BUMP_TOKEN` | PAT with `contents:write` on `winget-mythic` repo for the auto-update PR (PH-21.8) |
| (none for GHCR) | Workflow `GITHUB_TOKEN` is auto-provisioned with `packages:write`; no extra secret needed (PH-21.1) |
| `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` | **optional** — only needed when `DOCKERHUB_PUBLISH_ENABLED` repo variable is set to `true` to mirror images to Docker Hub (PH-21.1) |
| (none for PyPI) | Trusted publishing uses OIDC — no long-lived token needed; configured per-repo at https://pypi.org/manage/account/publishing/ |

## Defer / future channels

All v1.x distribution channels have shipped: PyPI + Homebrew + Scoop
(v1.0) plus AUR + OCI + Termux + PyInstaller binaries + Nuitka
binaries + winget (PH-21.1, PH-21.2, PH-21.3, PH-21.7, PH-21.8,
PH-21.9). The remaining PH-21 work is cross-cutting cryptographic
provenance:

- **Sigstore signing** — keyless cryptographic signatures over all
  PyPI artifacts + OCI image + standalone binaries. PH-21.5.
- **Reproducible build attestations + tag signing** — SLSA Level 3
  build provenance + signed git tags. PH-21.6.

When each lands, add a new template under
`packaging/<channel>/` and a corresponding job to
`.github/workflows/release.yml`.

## Maintainer-repo sync recipes

Each non-PyPI channel uses an automated PR against a
maintainer-owned GitHub repo, since the upstream registry (Homebrew
core, AUR, winget-pkgs) requires either credentials we don't store
in CI or a human review step. Operators sync the merged PR upstream
following the recipe in each maintainer repo's README:

- `homebrew-mythic` — PR merge auto-publishes via `brew tap`.
- `scoop-mythic` — PR merge auto-publishes via `scoop bucket add`.
- `aur-mythic` — PR merge requires a human `git push aur master`
  to `ssh://aur@aur.archlinux.org/mythic-vibe-cli.git` from a
  workstation with the maintainer's AUR SSH key. The recipe lives
  in the maintainer-repo README.
- `winget-mythic` — PR merge requires a human to either submit a
  PR to `microsoft/winget-pkgs` (the canonical repo) using
  `wingetcreate submit` against the staged manifest, or fork the
  upstream repo and open a manual PR. The recipe lives in the
  maintainer-repo README. winget's central registry requires
  Microsoft-side review; expect a 1-3 day turnaround per release.
