# Quickstart

This guide gets Mythic Vibe CLI running and walks you through one clean, end-to-end workflow cycle with artifact continuity.

---

## 1) Prerequisites

### Required

- Python 3.10+
- Git
- A shell (`bash`, `zsh`, `fish`, PowerShell, etc.)

### Recommended

- A virtual environment (`venv`, `uv`, or `conda`)
- An editor with Python linting/formatting
- `pytest` for local verification loops

---

## 2) Clone and set up

```bash
git clone <your-fork-or-repo-url>
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
python -m venv .venv
source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -e .
```

If editable install is unavailable in your environment, run the CLI via module mode:

```bash
python -m mythic_vibe_cli.cli --help
```

---

## 3) Verify installation

Run one of:

```bash
mythic --help
# or
mythic-vibe --help
# or
python -m mythic_vibe_cli.cli --help
```

Expected result: command list and option help text.

---

## 4) Initialize a project scaffold

Example:

```bash
mythic-vibe init --goal "Build a beginner-friendly TODO app" --noob
```

This initializes a method-aligned project skeleton with core artifacts in `docs/`, `tasks/`, and `mythic/`.

---

## 5) Run your first loop

The canonical sequence is:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

At each step:

1. Decide and document.
2. Execute a narrow action.
3. Verify before moving forward.
4. Preserve rationale in artifacts.

This keeps AI interactions useful without losing your own design intent.

---

## 6) Bridge workflow for ChatGPT/Codex

Generate a prompt packet:

```bash
mythic-vibe codex-pack \
  --phase plan \
  --task "Implement parser and template generation" \
  --audience beginner
```

Then:

1. Open `mythic/codex_prompt.md`.
2. Paste the packet into ChatGPT/Codex.
3. Execute/curate resulting changes.
4. Log outcomes:

```bash
mythic-vibe codex-log --phase build --response "Implemented parser and tests"
```

---

## 7) Daily operating ritual (recommended)

1. **Status:** run status command before edits.
2. **Decide:** choose one phase objective.
3. **Execute:** make the smallest meaningful change.
4. **Verify:** run checks/tests.
5. **Record:** update task/docs/devlog.

This rhythm minimizes drift and protects continuity across sessions.

---

## 8) Common commands

```bash
mythic-vibe status
mythic-vibe checkin --phase intent --update "Defined target users and anti-goals"
mythic-vibe doctor
mythic-vibe sync
mythic-vibe method
```

Ritual aliases may also be available (`mythic imbue`, `mythic evoke`, `mythic scry`, etc.).

---

## 9) Troubleshooting

### CLI command not found

- Ensure virtual environment is active.
- Re-run `pip install -e .`.
- Use module mode: `python -m mythic_vibe_cli.cli --help`.

### Status or phase mismatch

- Inspect generated `mythic/`, `docs/`, and `tasks/` artifacts.
- Run status/doctor commands before additional edits.

### Configuration confusion

- Inspect resolved config:

```bash
mythic-vibe config --path .
```

- Check environment variables overriding config files.

### Architecture boundary uncertainty

- Read `ARCHITECTURE.md` and `DOMAIN_MAP.md`.
- Keep runtime edits in `mythic_vibe_cli/` unless explicitly approved by architecture change.

---

## 10) Next documents

- `SYSTEM_VISION.md`
- `ARCHITECTURE.md`
- `DOMAIN_MAP.md`
- `api.md`
- `INDEX.md`
