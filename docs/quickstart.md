# Quickstart

Get Mythic Vibe CLI running quickly and complete your first structured workflow loop.

---

## 1) Prerequisites

- Python 3.10+
- Git
- A shell environment (bash, zsh, PowerShell, or equivalent)

Optional but useful:
- A virtual environment tool (`venv`, `uv`, or `conda`)
- An editor with Python linting and formatting support

---

## 2) Clone and set up

```bash
git clone <your-fork-or-repo-url>
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e .
```

If editable install is not configured in your environment, install dependencies from the project’s packaging files and run the module directly.

---

## 3) Verify the CLI is available

Run one of the following (depending on your setup):

```bash
mythic --help
# or
python -m mythic_vibe_cli.cli --help
```

You should see command help text and available workflow operations.

---

## 4) Initialize a working loop

Use the CLI to initialize/adopt a project and enter the method loop:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

At each phase, capture outputs in project artifacts (for example, docs and task notes) so the next session starts with context.

---

## 5) Daily operating pattern (recommended)

1. **Check current status** (what phase, what’s blocked, what’s next).
2. **Run the next phase command**.
3. **Record decisions and rationale** in artifacts.
4. **Verify outcomes** with tests/checks.
5. **Log reflection** so future sessions resume cleanly.

This operating pattern is the fastest way to avoid drift and repeated rework.

---

## 6) Troubleshooting

### CLI not found

- Confirm virtual environment is active.
- Re-run `pip install -e .`.
- Fall back to `python -m mythic_vibe_cli.cli --help`.

### Phase confusion or state mismatch

- Inspect generated artifacts in `docs/`, `tasks/`, and `mythic/`.
- Re-run the status/check command before making edits.

### Import/boundary errors

- Review [Architecture](ARCHITECTURE.md) and [Domain Map](DOMAIN_MAP.md).
- Ensure runtime code changes stay in `mythic_vibe_cli/` unless an explicit architecture decision says otherwise.

---

## 7) Next reads

- [System Vision](SYSTEM_VISION.md)
- [Architecture](ARCHITECTURE.md)
- [Domain Map](DOMAIN_MAP.md)
- [API Reference](api.md)
