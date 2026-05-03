# Quickstart

This guide gets Mythic Vibe CLI v1.0.0 running and walks you through one clean, end-to-end workflow cycle with artifact continuity. It assumes **zero prior knowledge** of Mythic Engineering.

For the full install matrix (PyPI / Homebrew / Scoop / wheelhouse / contributor / pre-release), see [`docs/INSTALL.md`](INSTALL.md).

---

## 1) Prerequisites

### Required

- Python 3.10, 3.11, or 3.12
- A shell (`bash`, `zsh`, `fish`, PowerShell, etc.)

### Recommended

- A virtual environment (`venv`, `uv`, or `conda`) — or use `pipx` for the cleanest user install
- An editor with Python linting/formatting

---

## 2) Install

The fastest path for end users is `pipx` from PyPI:

```bash
pipx install mythic-vibe-cli
```

Or with the optional Textual TUI + AI provider extras:

```bash
pipx install "mythic-vibe-cli[tui,ai]"
```

For Homebrew, Scoop, offline wheelhouse, or editable installs, see [`docs/INSTALL.md`](INSTALL.md).

---

## 3) Verify the install

```bash
mythic-vibe --version       # prints "mythic-vibe 1.0.0"
mythic-vibe --help          # full command list
```

The package exposes two entry points: `mythic-vibe` (canonical) and `mythic` (short alias).

---

## 4) Initialize a project

You need only one thing: an **empty folder**. It can be brand new (`mkdir my-first-app`) or an existing repo where you want Mythic to live alongside your code.

### Default (non-interactive)

```bash
cd my-first-app
mythic-vibe init --goal "Build a beginner-friendly TODO app" --noob
```

### Interactive wizard (v1.0 opt-in)

If you'd rather answer prompts than type flags:

```bash
mythic-vibe init --interactive
```

The wizard asks for project name, goal, default AI provider, operator name, and whether to scaffold sample ADR / oath / constraint files. Answers are persisted to `mythic/project_settings.json`.

> **Tip — `--dry-run`** is supported by every state-changing command. Append it to scout before you swing.

What just got created (default scaffold):

| Path | Edit by hand? | Why |
|---|---|---|
| `SYSTEM_VISION.md`, `tasks/current_GOALS.md` | **Yes** | Your two human files — keep them current |
| `MYTHIC_ENGINEERING.md` | No | The method headline copied locally |
| `docs/PHILOSOPHY.md`, `ARCHITECTURE.md`, `DOMAIN_MAP.md`, `DATA_FLOW.md`, `INDEX.md`, `COMMAND_CONTRACTS.md` | When the system changes | Treat doc drift as a functional bug |
| `docs/DEVLOG.md` | Append-only via `checkin` | The CLI maintains chronological order |
| `mythic/plan.md`, `mythic/loop.md` | No | Workflow scaffolding |
| `mythic/status.json` | **No** | Owned by the CLI; let `checkin` / `next` manage it |

---

## 5) Run your first loop

The canonical sequence:

`intent → constraints → architecture → plan → build → verify → reflect`

At each step:

1. Decide and document.
2. Execute one narrow action.
3. Verify before moving forward.
4. Preserve rationale in artifacts.

Ask the CLI where to go next at any point:

```bash
mythic-vibe next
```

You'll get something like:

```
Next recommended action
- What happened: Resolved the next phase as `intent`.
- What should I do next: Run `mythic-vibe checkin --phase intent --update "Goal and user clarified"`.
- How do I verify it: Check that SYSTEM_VISION.md and tasks/current_GOALS.md tell the same story.
```

Three pieces of information, every time: **what phase**, **what command**, **how you'll know it worked**. That is the loop.

---

## 6) Record a check-in

Tell the CLI you completed the intent phase:

```bash
mythic-vibe checkin --phase intent --update "Captured the goal and the first user we want to help"
```

This writes one line to `docs/DEVLOG.md`, bumps `mythic/status.json`, and prints a short summary. The seven phases are `intent → constraints → architecture → plan → build → verify → reflect`.

---

## 7) See where you stand

```bash
mythic-vibe status
```

It reads `mythic/status.json`, the latest verification record, the most recent handoff, and your plugin counts, then prints a concise summary. There is no hidden state.

For a richer interactive view: `mythic-vibe tui` (requires the `[tui]` extra). It opens a four-panel grid plus an event feed, with `/` opening a slash-command picker.

---

## 8) Bridge to an AI assistant

When you start touching code, ask Mythic Vibe to **scan your project context** and **package it into a prompt** ready to send to ChatGPT, Codex, Claude, Aider, Goose, Gemini, or Roo:

```bash
# 1) Build a local index of your project
mythic-vibe scan

# 2) Generate a packet for the assistant of your choice
mythic-vibe packet create \
  --task "Implement the first TODO list view" \
  --phase build \
  --role "Forge Worker"

# 3) (v1.0) Lint the packet before sending — catches vague intent,
#    weak architecture anchors, missing acceptance criteria
mythic-vibe packet lint
```

The packet lands as a Markdown file under `mythic/packets/` and a matching JSON record. Open it, paste into your assistant, do the work, then come back and check in.

For an end-to-end six-role pass against a real AI provider, see `mythic-vibe forge --help` (PH-03).

---

## 9) Verify before you reflect

Mythic Engineering's unbreakable rule: *do not reflect on work that has not been verified.*

```bash
mythic-vibe verify --commands --docs --invariants --record
```

Runs your discovered test commands, checks docs reachability, evaluates project invariants, and writes a durable verification record to `mythic/verifications/`. The `--record` flag promotes the artifact to `latest.json`.

Need to re-run the last forge cycle from where it failed? `mythic-vibe verify --replay` is a one-flag shortcut to `forge resume` (v1.0 addition).

---

## 10) Close with a reflection handoff

```bash
mythic-vibe reflect \
  --summary "Implemented the first TODO list view and got tests passing" \
  --next-step "Wire up persistence in the next session"
```

Writes a permanent handoff record to `mythic/handoffs/`. That record is the bridge to your future self.

---

## 11) Pick the thread back up next time

When you sit down at the keyboard again — tomorrow, next week, six months from now:

```bash
mythic-vibe resume
```

It reads the most recent handoff and tells you exactly what you said you'd do next, plus a suggested prompt packet to brief an assistant if you want one.

---

## 12) Three commands you should know exist

```bash
mythic-vibe examples   # Copy-paste examples for the most common moves
mythic-vibe guide      # The compact operator guide (the seven phases at a glance)
mythic-vibe tutorial   # The full first-session walkthrough, in CLI form
mythic-vibe doctor     # Validate project structure and surface drift findings + AI-catalog freshness
```

Run them whenever you forget what's possible. The CLI is designed to teach you itself.

---

## 13) Daily operating ritual (recommended)

1. **Status:** `mythic-vibe status` before edits.
2. **Decide:** choose one phase objective.
3. **Execute:** make the smallest meaningful change.
4. **Verify:** `mythic-vibe verify --record` (or per-task subset).
5. **Record:** `mythic-vibe checkin --phase <name> --update "..."`.
6. **Reflect:** `mythic-vibe reflect --summary "..." --next-step "..."` at session end.

This rhythm minimizes drift and protects continuity across sessions.

---

## 14) Common first-day situations

- **"I made a mess. How do I undo?"** — Mythic Vibe writes append-only records. You can manually delete files under `mythic/` if you really want to start over, but more often you just `checkin` again with a corrected `--update`. The DEVLOG keeps the trail honest.
- **"I want to try the loop without committing real work."** — Append `--dry-run` to any state-changing command. It will print what it would do and write nothing.
- **"I'm not sure which phase I'm in."** — `mythic-vibe status`. The CLI is the source of truth.
- **"My CHANGELOG `[Unreleased]` block disappeared / `mythic/` subdirs are missing."** — `mythic-vibe doctor --fix` (v1.0). Auto-remediates safe scaffolding gaps without touching user-authored content.
- **"I want a visual instead of text."** — `mythic-vibe tui` (after installing the `[tui]` extra). v1.0 opt-in panels: `--panels heatmap,risk`.
- **"My plunder-imported file diverged from upstream."** — `mythic-vibe provenance verify` (SHA-256 check) or `mythic-vibe provenance attest --destination X --original Y` (per-line attestation).

---

## 15) Troubleshooting

### CLI command not found

- Ensure your virtual environment is active (or use `pipx install mythic-vibe-cli` for an isolated install).
- Use module mode as a fallback: `python -m mythic_vibe_cli --help`.

### Status or phase mismatch

- Inspect generated `mythic/`, `docs/`, and `tasks/` artifacts.
- Run `mythic-vibe status` and `mythic-vibe doctor` before additional edits.

### Configuration confusion

```bash
mythic-vibe config --path .
```

Check the env-var overrides too. The full list lives in `README.md` "Configuration model" section.

### Architecture boundary uncertainty

- Read `docs/ARCHITECTURE.md` and `docs/DOMAIN_MAP.md`.
- Keep runtime edits in `mythic_vibe_cli/` unless explicitly approved by an ADR.

---

## 16) Next docs

- [`docs/INSTALL.md`](INSTALL.md) — full install matrix
- [`docs/api.md`](api.md) — command/API reference
- [`docs/COMMAND_CONTRACTS.md`](COMMAND_CONTRACTS.md) — the durable contract surface
- [`docs/runtime.md`](runtime.md) — runtime-primitive composition guide
- [`docs/plugins.md`](plugins.md) — plugin authoring (v1.0: capability declarations + circuit breaker)
- [`docs/compatibility_policy.md`](compatibility_policy.md) — v1.0 SemVer + deprecation contract
- [`MYTHIC_ENGINEERING.md`](../MYTHIC_ENGINEERING.md) — the method itself
