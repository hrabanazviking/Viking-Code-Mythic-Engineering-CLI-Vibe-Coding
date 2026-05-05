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
- **`pipx` install with extras fails** — make sure you're using the PEP 508 form: `pipx install "mythic-vibe-cli[ai] @ git+URL@branch"` for VCS installs, or just `pipx install "mythic-vibe-cli[ai]"` for PyPI.
- **`mythic-vibe tui` says Textual is missing** — install the `[tui]` extra: `python -m pip install "mythic-vibe-cli[tui]"`.

For the full distribution-channel reference (PyPI publishing, Homebrew tap, Scoop bucket, release-pipeline secrets), see [`packaging/README.md`](../packaging/README.md).
