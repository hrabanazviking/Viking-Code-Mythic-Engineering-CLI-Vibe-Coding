# Install Guide

This guide covers installing the active Mythic Vibe CLI product from this repository.

## Requirements

- Python 3.10 or newer
- Git
- A shell: Windows PowerShell, bash, zsh, or similar

## Windows PowerShell

```powershell
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --help
```

If script execution is blocked, run PowerShell as your normal user and set:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Linux

```bash
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --help
```

## macOS

```bash
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --help
```

## uv

```bash
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
uv venv
uv pip install -e ".[dev]"
uv run mythic-vibe --help
```

## pipx

Use `pipx` when you want an isolated CLI install without activating a project venv:

```bash
pipx install "git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
mythic-vibe --help
```

For local development with `pipx`:

```bash
pipx install --editable .
mythic-vibe --help
```

## Verification

Run these before trusting an install:

```bash
python -m mythic_vibe_cli --help
mythic-vibe --version
pytest -q
```

For release-quality local checks:

```bash
ruff check mythic_vibe_cli tests scripts
mypy mythic_vibe_cli
python -m build
twine check dist/*
```

## Optional Rich Output

Plain terminal output is the default. To try richer rendering:

```bash
python -m pip install -e ".[ux]"
```

Windows PowerShell:

```powershell
$env:MYTHIC_RICH = "1"
mythic-vibe guide
```

Linux/macOS:

```bash
MYTHIC_RICH=1 mythic-vibe guide
```

## Shell Completion

Windows PowerShell:

```powershell
mythic-vibe completion --shell powershell | Invoke-Expression
```

Bash:

```bash
eval "$(mythic-vibe completion --shell bash)"
```

Zsh:

```bash
mythic-vibe completion --shell zsh > "${fpath[1]}/_mythic-vibe"
autoload -Uz compinit
compinit
```
