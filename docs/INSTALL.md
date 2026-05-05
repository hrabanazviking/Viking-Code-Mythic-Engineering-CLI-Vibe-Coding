# Install Guide

Mythic Vibe CLI v1.0.0 ships through three official channels plus an offline install path. Pick the one that matches your situation.

## Requirements

- Python **3.10**, **3.11**, or **3.12** (CI tests all three on Linux + macOS + Windows + Linux aarch64). Python 3.13 is on the targeted-but-untested tier — see `docs/compatibility_policy.md` §1.
- Git (only for `pipx install` from a VCS URL or for editable / contributor installs).
- A shell: Windows PowerShell, bash, zsh, or similar.

Once installed, two console entry points land on your `PATH`:

- `mythic-vibe` — the canonical command
- `mythic` — short alias

---

## End-user install (recommended)

### PyPI via `pipx` (best for "I just want to use it")

`pipx` puts the CLI in its own isolated environment so it never collides with your project's Python packages.

```bash
pipx install mythic-vibe-cli
mythic-vibe --version
```

With extras (Textual TUI, AI providers, rich UI):

```bash
pipx install "mythic-vibe-cli[tui,ai,ux]"
```

Upgrade:

```bash
pipx upgrade mythic-vibe-cli
```

### PyPI via plain `pip`

```bash
python -m pip install mythic-vibe-cli
# with extras:
python -m pip install "mythic-vibe-cli[tui,ai]"
mythic-vibe --version
```

### Homebrew (macOS / Linuxbrew)

```bash
brew install hrabanazviking/mythic/mythic-vibe
```

### Scoop (Windows)

```powershell
scoop bucket add mythic https://github.com/hrabanazviking/scoop-mythic
scoop install mythic-vibe
```

### winget (Windows)

```powershell
winget install hrabanazviking.MythicVibeCLI
```

The winget package ships the standalone PyInstaller binary as a `portable` installer — winget extracts the `.exe` to a known location and adds it to `PATH`. No registry installer chrome; `winget uninstall` cleans up by removing the binary.

The first launch may trigger a Windows SmartScreen "unrecognized publisher" prompt (the binary is unsigned until PH-21.5 keyless Sigstore signatures land). Click **More info** → **Run anyway**.

### Arch Linux (AUR)

The package is published as `mythic-vibe-cli` on the [Arch User Repository](https://aur.archlinux.org/). It builds from the PyPI sdist so AUR users get the exact bytes PyPI users get.

```bash
# Using yay (or any AUR helper):
yay -S mythic-vibe-cli

# Or manually with makepkg:
git clone https://aur.archlinux.org/mythic-vibe-cli.git
cd mythic-vibe-cli
makepkg -si
```

After install, both `mythic-vibe` and the `mythic` short alias land on `PATH`. Optional extras (`tui`, `ai`, `ux`, `otel`) install with the standard `pip` flow into a venv after the AUR base package — AUR ships only the runtime base.

### Termux (Android)

Termux turns an Android phone or tablet into a real Linux userland. The CLI installs from PyPI exactly the same way as on a desktop, plus a one-time apt prep:

```bash
# Inside Termux:
pkg update && pkg install python rust
pip install --upgrade pip
pip install mythic-vibe-cli

mythic-vibe doctor
mythic-vibe hardware       # confirms platform_tags includes "termux"
```

Notes:

- `rust` is needed to compile any optional extra that has a Rust-built wheel (the base CLI is pure-Python and does not need Rust). If you only install the base, `pkg install python` is enough.
- The CLI honors `XDG_CONFIG_HOME` and the `MYTHIC_HOME` env var. Termux already sets `XDG_CONFIG_HOME` to `~/.config`, so caches and config land under `~/.config/mythic-vibe/` exactly like on a desktop. No path tweaks required.
- `mythic-vibe hardware` exposes a `platform_tags` array that includes `termux` when the runtime detects either the `TERMUX_VERSION` environment variable or the Termux package prefix at `/data/data/com.termux/files/usr`. Use it to gate Termux-specific behavior in your own scripts.

### WSL (Windows Subsystem for Linux)

Inside a WSL distro the install path is identical to native Linux:

```bash
python3 -m pip install mythic-vibe-cli
mythic-vibe hardware       # platform_tags includes "wsl"
```

The runtime detects WSL by reading `platform.uname().release` and matching `microsoft` (case-insensitive) — works for both WSL1 and WSL2. The detection is read-only and never raises; if the kernel string changes in a future WSL release, the worst case is the tag drops, not a CLI failure.

### Standalone binaries (PyInstaller)

Each release attaches per-OS single-file executables to its GitHub Release page. No Python required on the target — the binary bundles a frozen interpreter plus the CLI's stdlib-only base.

```bash
VERSION=1.0.0
gh release download "v${VERSION}" \
    --repo hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding \
    --pattern "mythic-vibe-${VERSION}-linux-x86_64*"

# Verify the SHA256 sidecar:
sha256sum --check "mythic-vibe-${VERSION}-linux-x86_64.sha256"

# Make executable + run:
chmod +x "mythic-vibe-${VERSION}-linux-x86_64"
./"mythic-vibe-${VERSION}-linux-x86_64" --version
```

Released binary names follow this pattern:

| OS / arch | Asset name |
|---|---|
| Linux x86_64 | `mythic-vibe-<VERSION>-linux-x86_64` |
| macOS arm64 (Apple Silicon) | `mythic-vibe-<VERSION>-macos-arm64` |
| macOS x86_64 (Intel) | `mythic-vibe-<VERSION>-macos-x86_64` |
| Windows x86_64 | `mythic-vibe-<VERSION>-windows-x86_64.exe` |

Each binary ships with a `.sha256` sidecar for out-of-band verification.

The standalone binary embeds **only the CLI's stdlib-only base** — optional extras (`ai`, `tui`, `ux`, `otel`) are deliberately excluded so the binary stays small (~15-25 MB) and starts fast. If you need extras, use the PyPI / Homebrew / Scoop / AUR / Container channels above; those install into a venv where extras work via pip.

#### macOS first-launch (Gatekeeper override)

The macOS binaries ship **un-notarized**. On first launch macOS Gatekeeper will block the binary with a dialog that reads roughly:

> "mythic-vibe-1.0.0-macos-arm64" cannot be opened because it is from an unidentified developer.

This is expected. You have two clean ways past it:

**Option A — Right-click → Open (operator-friendly):**

1. In Finder, locate the downloaded binary.
2. Hold Control and click the binary; choose **Open**.
3. The same dialog appears, but this time it has an **Open** button. Click it once.
4. macOS records your trust decision; subsequent launches no longer prompt.

**Option B — clear the quarantine attribute (CLI-friendly):**

```bash
# Adjust the filename to whichever asset you downloaded:
xattr -d com.apple.quarantine /path/to/mythic-vibe-1.0.0-macos-arm64

# Now run normally:
chmod +x /path/to/mythic-vibe-1.0.0-macos-arm64
/path/to/mythic-vibe-1.0.0-macos-arm64 --version
```

`xattr -d com.apple.quarantine` removes the extended attribute Safari (or any other downloader) sets on freshly-downloaded files. After it's removed, Gatekeeper treats the binary as trusted local content.

##### Why we ship un-notarized

Notarization requires an Apple Developer account ($99/year), Apple-side review of every release, and a tighter signing setup that doesn't fit a small-team open-source project. The trade-off:

- ✅ **Operator sovereignty.** Anyone can build the same binary from source and verify it byte-for-byte against the published artifact via the SHA256 sidecar (or via the Sigstore signatures landing in PH-21.5).
- ✅ **No upstream gatekeeper.** Apple cannot revoke the project's notarization (and through it, every operator's installed binary) over a policy disagreement.
- ✅ **Open-source-philosophy aligned.** The project's threat model trusts cryptographic verification (sha256 → keyless Sigstore signatures) rather than corporate identity.
- ⚠️ **One-time prompt.** Operators see one Gatekeeper warning per binary per release. After the right-click → Open or `xattr -d` step, no further prompts.

If demand for notarization grows post-v1.0, the project can revisit by adding a separate v1.x slice with the Apple Developer account work. The decision is reversible — adding notarization later doesn't break any existing binary; it just adds a new code path.

### Container (Docker / Podman)

Each release publishes a multi-arch (linux/amd64 + linux/arm64) image to GitHub Container Registry:

```bash
# Pull and run the latest tag:
docker run --rm ghcr.io/hrabanazviking/mythic-vibe-cli:latest --help

# Pin to a specific version:
docker run --rm ghcr.io/hrabanazviking/mythic-vibe-cli:1.0.0 doctor --json

# Mount your project directory for in-place workflows:
docker run --rm -v "$(pwd):/work" ghcr.io/hrabanazviking/mythic-vibe-cli:1.0.0 status
```

The image runs as a non-root `mythic` user (uid 1000) with the workspace mounted at `/work`. Default `ENTRYPOINT` is `mythic-vibe`, so any flag/subcommand you pass goes straight to the CLI. The container ships with the `[ai,otel,ux,tui]` extras pre-installed.

Podman works the same — substitute `podman run` for `docker run`. The image manifest declares standard `org.opencontainers.image.*` labels (license, source, documentation URL) so registry UIs surface project metadata correctly.

If Docker Hub is also enabled (an opt-in publish target — see `packaging/README.md`), the same image is mirrored to `docker.io/hrabanazviking/mythic-vibe-cli`.

---

## Offline / air-gapped install

Every release attaches a wheelhouse tarball to its GitHub Release page:
`mythic-vibe-cli-<VERSION>-wheelhouse.tar.gz`. It bundles the project plus every wheel for the `[ai]`, `[otel]`, `[ux]`, and `[tui]` extras' transitive dependencies — pure-Python, no native compilation needed on the target.

Quickstart (full recipe with SHA verification in [`packaging/WHEELHOUSE.md`](../packaging/WHEELHOUSE.md)):

```bash
VERSION=1.0.0
gh release download "v${VERSION}" \
    --repo hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding \
    --pattern "mythic-vibe-cli-${VERSION}-wheelhouse.tar.gz" \
    --pattern "SHA256SUMS"
sha256sum --check --ignore-missing SHA256SUMS

tar -xzf "mythic-vibe-cli-${VERSION}-wheelhouse.tar.gz"
python -m venv ~/mythic-venv
source ~/mythic-venv/bin/activate
python -m pip install --no-index --find-links wheelhouse "mythic-vibe-cli[ai,otel,ux,tui]"
mythic-vibe --version
```

This is the supported path for Pi tier hardware (Pi Zero / Pi 5), Termux, hardened CI runners, and compliance environments that require all dependencies to be vendored.

---

## Contributor / editable install

For anyone who plans to modify, debug, or run tests against the CLI. The `-e` flag means "editable": `pip` records a link to your working tree instead of copying it, so source changes take effect immediately without re-installing.

### Linux

```bash
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --version
```

### macOS

Same as Linux above; `python3` resolves correctly.

### Windows PowerShell

```powershell
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --version
```

If script execution is blocked, run PowerShell as your normal user and set:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### `uv` (faster pip alternative)

```bash
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
uv venv
uv pip install -e ".[dev]"
uv run mythic-vibe --version
```

### `pipx` editable

```bash
pipx install --editable .
mythic-vibe --version
```

---

## Pre-release tracking (advanced)

If you want to track unreleased work between tagged versions, install from the `development` branch via the **PEP 508 direct-URL form** (the syntax both `pip` and `pipx` need for VCS installs with extras):

```bash
pipx install "git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
# with extras:
pipx install "mythic-vibe-cli[tui,ai] @ git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
```

Pre-release builds may break SemVer guarantees that v1.0.0 enforces — operators relying on the compatibility-policy contract should stay on tagged releases.

---

## Optional extras

The CLI's runtime base has **zero non-stdlib dependencies**. Every external package is opt-in via an extra:

| Extra | Purpose | Wheels |
|---|---|---|
| `tui` | Textual TUI (`mythic-vibe tui`) | `textual>=0.80` |
| `ai` | AI provider adapters (Anthropic / OpenAI / Gemini) | `anthropic>=0.34`, `google-genai>=1.0`, `openai>=1.40` |
| `ux` | Optional rich-text rendering. Set `MYTHIC_RICH=1` to enable. | `rich>=13.0` |
| `otel` | OpenTelemetry exporter. Set `MYTHIC_OTEL_ENABLED=1` to enable. | `opentelemetry-api/-sdk/-exporter-otlp-proto-http >= 1.20` |
| `mindspark` | MindSpark island adapter. Gated by `MYTHIC_ISLAND_MINDSPARK_ENABLED=1`. | `thoughtforge>=0.1` |
| `wyrd` | WYRD-protocol island adapter. Gated by `MYTHIC_ISLAND_WYRD_ENABLED=1`. | `wyrd-protocol>=1.0` |
| `yggdrasil` | Yggdrasil island adapter. Gated by `MYTHIC_ISLAND_YGGDRASIL_ENABLED=1`. | `yggdrasil>=0.1` |
| `test` | Test stack (also installs hypothesis for property tests) | `pytest>=8.0`, `pytest-cov>=5.0`, `hypothesis>=6.0` |
| `lint`, `type`, `build`, `docs` | Tool-specific contributor extras | `ruff>=0.8`, `mypy>=1.10`, `build>=1.2`+`twine>=5.0`, `mkdocs>=1.6` |
| `dev` | Combines `test` + `lint` + `type` + `build` + `docs` + `ai` + `ux` + `tui` | all of the above |

---

## Verification

Run these before trusting any install:

```bash
mythic-vibe --version          # prints "mythic-vibe 1.0.0" (or your installed version)
mythic-vibe --help              # full command list
mythic-vibe doctor              # project-scoped health check
mythic-vibe doctor --json       # same, machine-readable
```

Contributor / pre-flight checks (run inside an editable install):

```bash
pytest -q
ruff check mythic_vibe_cli tests scripts tools
mypy mythic_vibe_cli
python tools/contract_audit.py --strict
python -m build && twine check dist/*
```

---

## Optional rich output

Plain terminal output is the default. To enable `rich`-rendered output:

```bash
python -m pip install "mythic-vibe-cli[ux]"
```

Then:

- Linux / macOS: `MYTHIC_RICH=1 mythic-vibe guide`
- Windows PowerShell: `$env:MYTHIC_RICH = "1"; mythic-vibe guide`

---

## Shell completion

```bash
# Bash
eval "$(mythic-vibe completion --shell bash)"

# Zsh
mythic-vibe completion --shell zsh > "${fpath[1]}/_mythic-vibe"
autoload -Uz compinit
compinit
```

```powershell
# Windows PowerShell
mythic-vibe completion --shell powershell | Invoke-Expression
```

---

## Troubleshooting

- **`mythic-vibe: command not found`** — your venv is not active, OR you used `pip install` outside any venv and your shell's `PATH` doesn't include user-local install dirs. Activate the venv (or use the module form: `python -m mythic_vibe_cli --help`).
- **Wheel install fails on Pi Zero / very-low-RAM device** — use the offline wheelhouse path above; it ships pre-built wheels so the install path doesn't need a build toolchain.
- **Termux `pip install` fails compiling a wheel** — install `pkg install rust` first, or use the offline wheelhouse path which ships pre-built wheels and bypasses the compile step entirely.
- **Standalone binary refuses to run on macOS first launch ("unidentified developer")** — see the macOS Gatekeeper override section under [Standalone binaries](#standalone-binaries-pyinstaller); the project ships un-notarized so a one-time right-click → Open is required, or run `xattr -d com.apple.quarantine /path/to/mythic-vibe-*-macos-*` from the CLI.
- **Standalone binary triggers a Windows SmartScreen "unrecognized publisher" warning** — the binaries are unsigned. Click "More info" → "Run anyway" on first launch. Code signing is on the v1.x roadmap (PH-21.5 keyless signing via Sigstore).
- **`pipx` install with extras fails** — make sure you're using the PEP 508 form: `pipx install "mythic-vibe-cli[ai] @ git+URL@branch"` for VCS installs, or just `pipx install "mythic-vibe-cli[ai]"` for PyPI.
- **`mythic-vibe tui` says Textual is missing** — install the `[tui]` extra: `python -m pip install "mythic-vibe-cli[tui]"`.

For the full distribution-channel reference (PyPI publishing, Homebrew tap, Scoop bucket, release-pipeline secrets), see [`packaging/README.md`](../packaging/README.md).
