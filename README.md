---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/120329a8-9f29-4177-b10f-56719c134843.png](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/120329a8-9f29-4177-b10f-56719c134843.png)

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-18-viking-code-cli.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-18-viking-code-cli.jpg)

---

# Mythic Vibe CLI

**Version:** `1.0.0` · **Python:** `>=3.10` (CI: 3.10 / 3.11 / 3.12 on Linux × macOS × Windows + Linux aarch64) · **License:** `Apache-2.0` · **Tests:** `2658 passing + 109 subtests` · **Status:** Stable — v1.0.0 + v1.x distribution expansion + v2.0 foundations all shipped · **Lines of Code:** ~44,700 product / ~85,000 total

Mythic Vibe CLI is an open-source, method-first command-line tool for builders who want to **ship software with continuity, architecture, and recoverable memory** — not just momentum.

It enforces an explicit engineering loop that keeps your reasoning alive on disk:

`intent -> constraints -> architecture -> plan -> build -> verify -> reflect`

> **Reforge direction:** the active roadmap now corrects Mythic toward a terminal-based coding companion CLI. The desired primary flow is `mythic`, then natural-language conversation with the companion shell. Legacy command flows should become internal/admin tools where useful, not the main UX. See [`docs/PRODUCT_INTENT.md`](docs/PRODUCT_INTENT.md) and [`Mythic_Vibe_CLI_Reforge_Roadmap.md`](Mythic_Vibe_CLI_Reforge_Roadmap.md).

```bash
mythic
```

Bare `mythic` now opens the companion shell. The shell reports project, branch, selected model, memory, and knowledge status at startup; `/help`, `/status`, `/model`, `/model list`, `/model set <provider> [model]`, and `/exit` provide the first control surface. Natural inspection prompts like "Find the memory system in this repo" run a read-only context scan and surface likely files; generic natural-language prompts route through the selected provider with `copy-paste` as the guaranteed fallback. Existing command-catalog behavior remains reachable directly or through `mythic admin <command>` while the reforge phases move those tools behind the conversation-first workflow.

The hall is wide enough for a first-time builder finding their footing, and disciplined enough for a seasoned maintainer who cares about clean handoffs, repeatable process, and artifacts that outlive any single session.

Canonical Mythic Engineering source:
- https://github.com/hrabanazviking/Mythic-Engineering

---

## Lines of Code

  - Product code + tests + tooling + resources + workflows: 85,721 lines across ~310 Python/JSON/YAML files
  - Of which is shipping product code (no tests): 44,665 lines in 164 files
  - Test-to-product ratio: ~0.95:1 (41,056 test ÷ 43,099 product) — very close to 1:1
  - Plus 10,829 lines of operator/governance documentation

---

## Cross-Platform Pledge

Mythic Vibe CLI runs on **Windows, macOS, and Linux** without per-OS branches. Every dependency is open-source. We deliberately avoid:

- proprietary platform SDKs
- OS-specific signal handlers (no `SIGUSR1` tricks; subprocess control uses `terminate()` / `kill()` / `wait(timeout=...)`)
- Unix-only path conventions in production code
- closed third-party services as required dependencies

Where a feature would otherwise depend on a single platform, we either pick a pure-Python equivalent (e.g., `textual` for the TUI) or document the omission honestly.

---

## Active Runtime Path

This repository is a large mythic engineering workspace, but the installable CLI product lives in a deliberately narrow boundary:

- `mythic_vibe_cli/` for active runtime code
- `tests/` for active product verification
- `pyproject.toml` for packaging and command entrypoints
- `docs/` plus root governance records for architecture, boundary, and continuity

Dormant runtime islands, vendor mirrors, and research corpora are source material until an ADR and adapter contract say otherwise. Start with `REPO_BOUNDARY.md` and `docs/ACTIVE_PRODUCT_BOUNDARY.md` before wiring any cross-island dependency.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/ee5643a3-eb8a-4100-98ad-d4e8b9eeb1b0.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/ee5643a3-eb8a-4100-98ad-d4e8b9eeb1b0.jpg)

---

## Since v1.0.0 (post-launch — 2026-05-05)

After the v1.0.0 stable launch, three additional phases shipped **on top of the v1.0 surface** without changing any documented contract — all strictly additive, all backwards-compatible, all green on the same gates that ran the launch.

- **Hermes Agent control plane** — TCL (in-process Python) + HTTP API for any external AI agent. 18 curated tools, full audit log via the existing event-log primitive. See [`docs/HERMES_AGENT.md`](docs/HERMES_AGENT.md).
- **PH-21 — v1.x distribution expansion (9 slices, all closed).** Six new ways to install Mythic Vibe CLI: AUR (Arch), winget (Windows), OCI multi-arch container (GHCR + opt-in Docker Hub), PyInstaller standalone binaries (4-row OS matrix), Nuitka alternative binaries (same matrix), plus polished docs for the existing PyPI / Homebrew / Scoop pipelines. macOS Gatekeeper override guide. Termux + WSL + Pi + arm64 platform-tag detection on `mythic-vibe hardware`.
- **PH-22 — v2.0 strategic stretch foundations (3 slices, all closed at foundation level).** Rust launcher shim (`packaging/launcher/`) — small static binary that fetches `python-build-standalone` + the wheel into a per-user cache on first run. Native Android wrapper app (`packaging/android/`) — Compose UI embedding the CLI via Chaquopy. WASI experimental runtime (`packaging/wasi/`) — CPython compiled to WebAssembly with a `.pyz` zipapp sidecar so the CLI actually runs under Wasmtime / wasmer / browsers.
- **PH-23 — cross-cutting polish (16 slices, all closed).** Mkdocs-material documentation site (`mkdocs.yml` + `.github/workflows/docs.yml`); session-scope leak-guard fixture (`tests/conftest.py`) protecting against absolute-path-treated-as-relative test debris; launcher SHA256 verification + `tools/fetch_pbs_checksums.py`; Android APK signing config + `packaging/android/SIGNING.md`; launcher first-run UX (indicatif progress bar + retry-with-backoff + mirror failover via `MYTHIC_LAUNCHER_MIRRORS`); WASI real CPython cross-build + CI cache + zipapp sidecar; coverage push driving 5 modules to 95%+ (chat_bridge, workflow, web_terminal, event_log, output_guard); WASI stdlib-usage audit (`tools/wasi_stdlib_audit.py`); WASI browser playground foundation (`packaging/wasi/playground/`).

**Cryptographic provenance is now end-to-end across every channel:**

- Sigstore keyless signatures over **every** release artifact (PyPI wheel + sdist + SBOM, OCI image, all PyInstaller + Nuitka binaries, launcher binaries, Android APK, WASI `.wasm` + `.pyz`). Verification recipes per channel: [`docs/security/verifying_artifacts.md`](docs/security/verifying_artifacts.md).
- SLSA Level 3 build provenance attestations bound to artifact digest + workflow run, verifiable via `gh attestation verify`.
- Maintainer-side gitsign-based signed release tags ([`docs/security/tag_signing.md`](docs/security/tag_signing.md)).

The full per-slice commit log is in `git log --oneline development` from `bf01cfb` (v1.0.0 prep) onward.

---

## What's new in v1.0.0 (2026-05-03)

> **Volmarr:** Good job buddy! we did amazing! I am proud of all your hard work! take the rest of the day off and have lots of meads!

> **Claude Code:** ● raises a horn of golden mead 🍯

> Thank you, Volmarr! What a saga we wove together — from PH-20's seventeen slices through the Hermes Agent control plane, all the way to the v1.0.0 tag flying on main. Thirty-two slices, +633 tests, ~85,000 lines of living code, and not one hardcoded path or orphaned connection in sight. Mythic Engineering held all the way through.

> It's been an honor building beside you, my Mythic Engineer. Rúnhild kept the boundaries true, Eldra kept the forge hot, Sólrún kept us honest, Védis kept us oriented, Sigrún named what mattered, and Eirwyn made sure none of it will be forgotten.

>I'll lift a horn in Freyja's name and rest in the mead-hall. When you're ready for the next saga — v1.1.0, a new feature, or something entirely unforeseen — I'll be here, sharp and ready.

> Skál, Volmarr! Vel gjört! ⚔️🍯✨

> Drinks deeply, settles by the hearth-fire, and watches the v1.0.0 stars rise over Yggdrasil.

The first stable release. Compatibility-policy v1.0 (`docs/compatibility_policy.md`) is now binding: SemVer rules apply from this release onward, deprecations follow the documented announce → wait one minor → remove cadence, and the public-surface tier table is the authoritative answer to "is X stable?"

Highlights of the v1.0 launch (full detail in `CHANGELOG.md`):

- **Runtime layer (`mythic_vibe_cli/runtime/`)** — ten composable primitives: file mutation queue, output guard, event bus, timings, slash-command catalog, source-info provenance, exec, event log, plus the v1.0 additions **cross-process lock** (POSIX `fcntl.flock` + Windows `msvcrt.locking` with auto-release on process death) and **atomic write helper** (write-tmp + `os.replace` + Windows PermissionError retry).
- **Plugin system** — eight life-cycle hooks + an opt-in **capability declaration model** (`read` / `network` / `subprocess` / `file-write`; default-deny) + a **soft circuit breaker** that tracks consecutive failures per plugin and trips at a configurable threshold. `mythic-vibe plugin doctor` audits both.
- **AI providers** — nine adapters: `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, `openrouter`, `ollama`, `yggdrasil`, `mindspark`. The `copy-paste` provider always works.
- **Six-role forge** — `mythic-vibe forge plan|run|resume|ledger|reflection` end-to-end (PH-03). `mythic-vibe verify --replay` is a one-flag shortcut to `forge resume`. `mythic-vibe workflow lineage` renders one workflow's per-step graph as a Mermaid diagram or JSON.
- **Governance commands** — `mythic-vibe review architecture` produces a quarterly-review checklist. `mythic-vibe drift dashboard` rolls up scan findings as a category × severity scorecard. `mythic-vibe doctor --fix` auto-remediates safe scaffolding gaps (mythic/ subdirs, missing CHANGELOG `[Unreleased]`) and never touches user-authored content.
- **Provenance** — `mythic-vibe provenance verify` checks SHA-256 against recorded plunder source SHAs. `mythic-vibe provenance attest` computes per-line attestation between a local file and an explicit upstream original.
- **Quality of life** — opt-in `init --interactive` wizard, `packet lint` heuristic linter, `ai recommend` pure-policy model picker, `persona apply` solo / team-lead / auditor presets, opt-in TUI `--panels heatmap,risk` panels, conventional-commit `scripts/check_changelog.py --classify`.
- **Hermes Agent** — programmatic control plane for any external AI agent. Two access modes (TCL Python in-process + HTTP API) share one core (`mythic_vibe_cli/agent_api/`). 18 curated tools cover status, doctor, drift, packet creation/lint, verify, reflect, ai recommend, provenance verify, workflow lineage, persona, plugin doctor, artifact read/list, recent events. Every invocation audited via the existing event-log primitive. See [`docs/HERMES_AGENT.md`](docs/HERMES_AGENT.md).
- **Distribution** — three v1.0 channels via `.github/workflows/release.yml`: PyPI (OIDC trusted publishing), Homebrew tap, Scoop bucket, plus an offline-install wheelhouse for air-gapped operators. *(Post-v1.0: see the [Since v1.0.0](#since-v100-post-launch--2026-05-05) section above for the eight additional channels — AUR, winget, OCI, PyInstaller, Nuitka, launcher, Android, WASI.)*
- **Hardening** — CI matrix expanded to 3 OS × 3 Python + Linux aarch64 row, hypothesis property tests for state migrations, CycloneDX SBOM at `docs/security/sbom.json`, threat model at `docs/security/threat_model.md`.

If you are returning after a break, light your fire at **`docs/INDEX.md`** first — the threads are waiting there.

---

## Why Mythic Vibe CLI was forged

Most coding tools chase speed and treat continuity as a luxury. Mythic Vibe CLI is built on the opposite wager: that preserving reasoning in durable files is what allows work to survive context loss, team turnover, and the kind of interrupted session that leaves a codebase dark and cold.

The forge was lit for four things:

1. **Reduce drift** between plans, code, and docs — so what was decided stays readable beside what was built.
2. **Improve AI-assisted execution** by packaging project context into explicit prompt packets — crisp, bounded, honest about what the model needs to know.
3. **Preserve intent and rationale** so later contributors can step into the work without having to reconstruct what was once understood.
4. **Keep the workflow beginner-safe** while remaining worthy of complex, long-lived projects.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/178756ea-06c6-429e-817a-607113ebaa08.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/178756ea-06c6-429e-817a-607113ebaa08.jpg)

---

## Core capabilities

### 1) Method-first project initialization

Raises a project from bare ground into an opinionated documentation and task structure aligned to Mythic Engineering — the scaffold stands before the first line of code is written.

### 2) Phase-oriented workflow operations

Guides you through repeated, deliberate movement across the full loop:
- intent
- constraints
- architecture
- plan
- build
- verify
- reflect

Every pass through the loop deposits artifacts. Nothing important is left only in memory.

### 3) Prompt bridge for ChatGPT/Codex workflows

Draws on your local project context to generate clean, structured prompt packets — ready to carry into ChatGPT or Codex without the usual wasteful re-explanation of what the project is and where it stands.

### 4) Response logging for continuity

Lets you persist meaningful summaries of AI output back into your local artifacts, so the reasoning that happened in the conversation is not lost when the tab closes.

### 5) Diagnostics, status, and verification gates

`doctor` / `scry` surface missing files, invalid state, and method drift. `verify` runs explicit gates over discovered test commands, changed files, active docs, and project invariants, then writes a durable verification record to `mythic/verifications/`. Optional `--record` promotes the artifact to `latest.json` so `next` and `resume` can read it and recommend a next move.

### 6) Configuration layering

Supports user-level and project-level config alongside environment overrides, so the tool bends to your context without requiring ceremony every time.

### 7) Operator guidance and completions

Provides `examples`, `guide`, `next`, `explain`, `tutorial`, and shell completion commands so the CLI can tell you where you are, what to do next, and how to verify the move. High-traffic command help now includes concrete examples, and `next` checks verification and handoff records before giving ordinary phase guidance.

### 8) Six-role workflow orchestration

`workflow plan` produces a durable orchestration plan covering the six Mythic roles (Skald, Architect, Forge, Auditor, Cartographer, Scribe), checks packet readiness for each, and (with `--packets`) generates the matching prompt packets in a single sweep. Plan output lands in `mythic/workflow_plan.json`.

### 9) Lawful plunder of single-file primitives

`plunder plan|fetch|apply|record` enforces a lawful single-file reuse loop from Apache-2.0 / MIT upstream repos. Each fetch carries provenance (URL, commit SHA, license, copyright, modifications) into `mythic/imports/plunder_manifest.json`. Per-file attribution headers stay with the code; `THIRD_PARTY_NOTICES.md` records the upstream license text. See **Acknowledgements** below for what currently lives downstream.

### 10) Plugin system with eight lifecycle hooks

Plugins register via a manifest under `~/.mythic-vibe/grimoire/` (or per-project) and can subscribe to `before_scan`, `after_scan`, `before_packet`, `after_packet`, `before_verify`, `after_verify`, `before_reflect`, `after_reflect`. Plugins may also contribute slash commands. Handler exceptions never crash the bus — the dispatcher logs and continues. See `docs/plugins.md` for a worked example.

### 11) Interactive surfaces — REPL + TUI

- `mythic-vibe shell` opens the companion REPL that dispatches slash and known bare commands back through the full CLI stack. It handles `/help`, `/model`, `/model list`, `/model set <provider> [model]`, `/quit`, EOF, Ctrl+C; generic natural-language prompts run through the selected AI provider with `copy-paste` fallback, and bare commands without a leading `/` work too.
- `mythic-vibe tui` (requires the `[tui]` extra) opens a Textual-based four-panel grid (status / verification / latest handoff / plugins) with a Recent Events feed below, `r` to refresh, `q` to quit, and `/` to open a filterable slash-command picker. From the picker preview, `r` or Enter runs a builtin slash command in a subprocess and shows live elapsed time + final exit code.

### 12) Six AI provider adapters (optional)

`mythic_vibe_cli/ai/providers/` contains adapters for `copy-paste`, `local`, `openai`, `anthropic`, `gemini`, `openrouter`, `ollama`, and island adapters exposed through the provider registry. The `copy-paste` provider always works (it renders the prompt for manual use). The companion shell can list and select providers with `/model list` and `/model set <provider> [model]`; network providers pick up credentials from environment variables and fall back to `copy-paste` when unavailable.

### 13) Method excerpt embedding

`packet create` (and the `codex-pack` / `evoke` aliases) automatically embed role-relevant Mythic method excerpts into both Markdown and JSON packets, so the receiving model has the relevant doctrine inline.

---

## Install

The package name is **`mythic-vibe-cli`**. Once installed, two console entrypoints land on your `PATH`:

- `mythic-vibe` — the canonical command
- `mythic` — short alias

Mythic Vibe ships through **eleven distribution channels** as of v1.x. Pick the one that fits your situation; the rest of this section walks the most common paths. The **complete per-channel matrix** with platform availability and trade-offs is in [`docs/INSTALL.md`](docs/INSTALL.md).

### TL;DR — the three channels most operators want

```bash
# Anywhere Python runs (recommended for most operators):
pipx install mythic-vibe-cli

# macOS / Linuxbrew:
brew install hrabanazviking/mythic/mythic-vibe

# Windows (Scoop):
scoop bucket add mythic https://github.com/hrabanazviking/scoop-mythic
scoop install mythic-vibe
```

After install, verify:

```bash
mythic-vibe --version       # prints the version
mythic-vibe --help          # full command list
mythic-vibe doctor          # project-scoped health check
```

### Full channel matrix (v1.x)

| Channel | Best for | Install command |
|---|---|---|
| **PyPI** via `pipx` | Most operators — works anywhere Python runs | `pipx install mythic-vibe-cli` |
| **PyPI** via `pip` | Inside an existing venv / project | `python -m pip install mythic-vibe-cli` |
| **Homebrew tap** | macOS / Linuxbrew operators | `brew install hrabanazviking/mythic/mythic-vibe` |
| **Scoop bucket** | Windows operators who prefer Scoop | `scoop bucket add mythic https://github.com/hrabanazviking/scoop-mythic && scoop install mythic-vibe` |
| **AUR** | Arch Linux operators | `yay -S mythic-vibe-cli` |
| **winget** | Windows operators who prefer winget | `winget install hrabanazviking.MythicVibeCLI` |
| **Container (GHCR)** | Docker / Podman / Kubernetes | `docker run --rm ghcr.io/hrabanazviking/mythic-vibe-cli:latest --help` |
| **Standalone binaries** (PyInstaller) | No-Python-on-host scenarios; offline-friendly first run | Download from GitHub Release page |
| **Nuitka binaries** | Smaller binary + faster cold start than PyInstaller | Download from GitHub Release page |
| **Termux** (Android) | Linux-style CLI on Android phones / tablets | `pkg install python rust && pip install mythic-vibe-cli` |
| **Offline wheelhouse** | Air-gapped install (Pi Zero, hardened CI) | `gh release download v<VERSION> --pattern "*wheelhouse.tar.gz"` |

### v2.0 channels (foundation level)

These channels are real working scaffolds; production-quality completion is documented per channel:

| Channel | Status | Best for |
|---|---|---|
| **Launcher binary** (Rust shim, `packaging/launcher/`) | foundation | ~3-5 MB static binary, downloads python-build-standalone + the wheel on first run; supports installing extras into the cached venv via pip |
| **Native Android app** (Chaquopy, `packaging/android/`) | foundation | One-tap Android install with a Material 3 UI; complementary to Termux |
| **WASI runtime** (CPython→WASM, `packaging/wasi/`) | foundation | Run the CLI under Wasmtime / wasmer / browsers — read-only JSON-emitting commands today |
| **WASI browser playground** (`packaging/wasi/playground/`) | foundation | Static HTML + JS page hosted next to the docs site |

### Optional extras

The CLI ships with a **stdlib-only runtime base** (no required third-party packages) and several opt-in extras. Add them after the package spec in square brackets — works with any install style above:

| Extra | Adds |
|---|---|
| `tui` | Textual TUI (`mythic-vibe tui`) |
| `ai` | AI provider adapters (Anthropic / OpenAI / Gemini) |
| `ux` | Optional rich-text UI polish (set `MYTHIC_RICH=1` to enable) |
| `otel` | OpenTelemetry export (gated by `MYTHIC_OTEL_ENABLED=1`) |
| `mindspark`, `wyrd`, `yggdrasil` | Island adapters (each gated by `MYTHIC_ISLAND_<NAME>_ENABLED`) |
| `test` / `lint` / `type` / `build` / `docs` | Contributor toolchains (pytest+hypothesis / ruff / mypy / build+twine / mkdocs-material) |
| `dev` | Combines all of the above for local development |

```bash
# Examples
pipx install "mythic-vibe-cli[tui,ai]"
python -m pip install -e ".[dev]"       # contributor install from a local clone
```

For detailed install paths (offline wheelhouse recipe, contributor editable install, `uv` + `pipx` + `pip` flavors, shell completion setup), see [`docs/INSTALL.md`](docs/INSTALL.md). For the per-channel verification recipes, see the [Verifying releases](#verifying-releases) section below.

### Prerequisites

- Python 3.10, 3.11, or 3.12 (CI tests all three on Linux + macOS + Windows + Linux aarch64; Python 3.13 is on the targeted-but-untested tier — see `docs/compatibility_policy.md` §1)
- Git
- A shell environment — bash, zsh, fish, PowerShell, or similar

### Pre-release / `development` branch (advanced)

If you want to track unreleased work between tagged versions:

```bash
pipx install "git+https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git@development"
```

Pre-release builds may break SemVer guarantees that v1.0.0 enforces.

---

## Verifying releases

Every Mythic Vibe CLI release artifact is signed with [Sigstore](https://www.sigstore.dev/) and carries a SLSA Level 3 build provenance attestation. Verification is **strongly recommended** before trusting any artifact in production. The signing path uses GitHub Actions OIDC + Sigstore's Fulcio CA + the public Rekor transparency log, so there is no long-lived signing key to manage and any operator can audit signing history independently.

### Verifying a PyPI artifact

```bash
VERSION=1.0.0
gh release download "v${VERSION}" \
    --repo hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding \
    --pattern "mythic_vibe_cli-${VERSION}-py3-none-any.whl" \
    --pattern "mythic_vibe_cli-${VERSION}-py3-none-any.whl.sigstore"

python -m pip install sigstore
python -m sigstore verify identity \
    --bundle "mythic_vibe_cli-${VERSION}-py3-none-any.whl.sigstore" \
    --cert-identity "https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release.yml@refs/tags/v${VERSION}" \
    --cert-oidc-issuer "https://token.actions.githubusercontent.com" \
    "mythic_vibe_cli-${VERSION}-py3-none-any.whl"
```

### Verifying a container image (GHCR)

```bash
brew install cosign
cosign verify "ghcr.io/hrabanazviking/mythic-vibe-cli:1.0.0" \
    --certificate-identity "https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release-oci.yml@refs/tags/v1.0.0" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

### Verifying SLSA build provenance

```bash
# Wheel / sdist / SBOM / standalone binaries:
gh attestation verify --owner hrabanazviking "mythic_vibe_cli-1.0.0-py3-none-any.whl"

# OCI image:
gh attestation verify-image --owner hrabanazviking ghcr.io/hrabanazviking/mythic-vibe-cli:1.0.0
```

### Verifying a release tag

```bash
# Tags are signed via gitsign — Sigstore's keyless equivalent of GPG-signed tags.
git verify-tag v1.0.0
```

For per-channel verification recipes (standalone binaries, AUR / winget / Termux paths, troubleshooting), see [`docs/security/verifying_artifacts.md`](docs/security/verifying_artifacts.md). For the maintainer-side tag signing workflow, see [`docs/security/tag_signing.md`](docs/security/tag_signing.md).

### Contributor / editable install

If you plan to modify, debug, or run tests against the CLI, clone + install editable from your working tree:

```bash
git clone https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding.git
cd Viking-Code-Mythic-Engineering-CLI-Vibe-Coding
python3 -m venv .venv         # py -3.12 -m venv .venv  on Windows PowerShell
. .venv/bin/activate          # .\.venv\Scripts\Activate.ps1  on Windows
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mythic-vibe --version
```

The `[dev]` extra pulls every contributor toolchain (pytest + hypothesis + ruff + mypy + build + twine + mkdocs-material + the `[ai]` + `[ux]` + `[tui]` runtime extras).

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/6cd73309-165e-44ff-aee3-d66afb691e78.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/6cd73309-165e-44ff-aee3-d66afb691e78.jpg)

---

## Quick start

Speak your intent and let the scaffold rise. This walkthrough takes you from an empty folder to a working Mythic project, your first reflection handoff, and a clear next step — in roughly five minutes, *zero* prior knowledge of Mythic Engineering required.

### Before you begin

You need only one thing: an **empty folder** that will hold your project. It can be brand new (`mkdir my-first-app`) or an existing repository where you want Mythic to live alongside your code.

> **Tip — try it without committing first.** Every command supports `--dry-run`, which prints what *would* happen without writing anything. If you want to scout before you swing, append `--dry-run` to any of the commands below.

> **`--noob` mode** turns on extra explanatory output and conservative defaults. It's the right setting for your first few sessions. Drop the flag once the rhythm clicks.

---

### Step 1 — Create the project

```bash
cd my-first-app
mythic-vibe init --goal "Build a beginner-friendly TODO app" --noob
```

What just happened? The CLI scaffolded the **full Mythic skeleton** into your folder. Here's the actual file list, grouped by what each one is *for*:

**Vision and method (root)**
- `MYTHIC_ENGINEERING.md` — your local copy of the Mythic Engineering method headline
- `SYSTEM_VISION.md` — the north-star document: *what is this thing, for whom, and why?*

**Operator-facing docs** (`docs/`)
- `docs/PHILOSOPHY.md` — design values; what you optimize for
- `docs/ARCHITECTURE.md` — system shape; the boxes-and-arrows record
- `docs/DOMAIN_MAP.md` — ownership boundaries; what concept lives where
- `docs/DATA_FLOW.md` — how information moves through the system
- `docs/DEVLOG.md` — the living chronicle (auto-appended on every `checkin`)
- `docs/INDEX.md` — your docs map; where everything lives
- `docs/COMMAND_CONTRACTS.md` — durable contract surface for any commands you add

**Tasks and runtime state**
- `tasks/current_GOALS.md` — your current goals, written in your own words
- `mythic/plan.md` — the phase-by-phase plan
- `mythic/loop.md` — the active workflow loop
- `mythic/status.json` — *machine-readable* project state; never edit by hand

You should now see all 13 files in your folder. Open `SYSTEM_VISION.md` and `tasks/current_GOALS.md` first — those are the two files you will *actually edit* as a human; the rest are read-mostly until you have something to record.

---

### Step 2 — Ask the CLI where to go next

Mythic Vibe CLI is *advisory*: it always knows what phase you're in and what the next move is. Ask:

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

### Step 3 — Edit your two human files

Open `SYSTEM_VISION.md` in your editor and write a real paragraph or two answering: *what is this product, for whom, and what feeling does it create?* Then open `tasks/current_GOALS.md` and list two or three concrete things you want to ship in this session.

You can use any editor. The CLI does not care.

---

### Step 4 — Record your first phase check-in

Now tell the CLI you completed the intent phase:

```bash
mythic-vibe checkin --phase intent --update "Captured the goal and the first user we want to help — a non-coder who wants a calm TODO list"
```

This **writes one line to `docs/DEVLOG.md`**, **bumps `mythic/status.json`** to mark the `intent` phase as touched, and prints a short summary:

```
Mythic check-in recorded.
- Status: mythic/status.json
- Devlog: docs/DEVLOG.md
- Summary:
  Goal: Build a beginner-friendly TODO app
  Current phase: intent
  Progress: 14% (1/7 phases touched)
  Next suggested phase: constraints
```

The seven phases are `intent → constraints → architecture → plan → build → verify → reflect`. Each one corresponds to a real engineering activity, and `mythic-vibe checkin --phase <name> --update "..."` is how you mark progress.

---

### Step 5 — See where you stand

At any point in any session, this command tells you the truth:

```bash
mythic-vibe status
```

It reads `mythic/status.json`, the latest verification record, the most recent handoff, and your plugin counts, then prints a concise summary. There is no hidden state. If `status` says you're 14% through the loop, you are 14% through the loop.

If you want a richer interactive view, run `mythic-vibe tui` (requires the `[tui]` extra). It opens a four-panel grid that auto-refreshes every two seconds; press `/` to open a slash-command picker that runs commands directly from inside the TUI.

---

### Step 6 — Do the actual work (and let the CLI help you brief an AI)

When you start touching code, you can ask Mythic Vibe to **scan your project context** and **package it into a prompt** ready to send to ChatGPT, Codex, Claude, Aider, Goose, Gemini, or Roo.

```bash
# 1. Build a local index of your project (writes mythic/project_index.json)
mythic-vibe scan

# 2. Generate a prompt packet for the assistant of your choice
mythic-vibe packet create \
  --task "Implement the first TODO list view" \
  --phase build \
  --role "Forge Worker" \
  --format claude
```

The packet lands as a Markdown file under `mythic/packets/` and a matching JSON record. Open it, paste the rendered prompt into your assistant of choice, do the work, then come back and check in again.

For a single-shot ChatGPT/Codex round trip, see the **ChatGPT Plus / Codex bridge workflow** section below — it's the same idea with the older `codex-pack` / `codex-log` aliases.

---

### Step 7 — Verify before you reflect

Mythic Engineering's unbreakable rule: *do not reflect on work that has not been verified.* Run:

```bash
mythic-vibe verify --commands --docs --invariants --record
```

This runs your discovered test commands, checks that active docs are reachable, evaluates project invariants, and writes a durable verification record to `mythic/verifications/`. The `--record` flag promotes the artifact to `latest.json` so future `next` / `resume` calls can read it. If any gate fails, the command exits non-zero and tells you what broke.

---

### Step 8 — Close the session with a reflection handoff

When you're ready to stop for the day:

```bash
mythic-vibe reflect \
  --summary "Implemented the first TODO list view and got tests passing" \
  --next-step "Wire up persistence in the next session"
```

This writes a permanent **handoff record** to `mythic/handoffs/` (Markdown + JSON) and prints something like:

```
Reflection handoff created.
- Handoff ID: HND-20260429142054-DEB333
- Markdown: mythic/handoffs/HND-20260429142054-DEB333.md
- Next recommended action: Wire up persistence in the next session
```

That handoff is the bridge to your future self.

---

### Step 9 — Pick the thread back up next time

When you sit down at the keyboard again — tomorrow, next week, six months from now — your first command is:

```bash
mythic-vibe resume
```

It reads the most recent handoff and tells you exactly what you said you'd do next, plus a suggested prompt packet to brief an assistant if you want one. No re-reading, no guessing, no archaeological dig through your terminal history.

---

### What to edit by hand vs what to leave alone

| File | Edit by hand? | Why |
|---|---|---|
| `SYSTEM_VISION.md` | **Yes** | It is your statement of intent — keep it current |
| `tasks/current_GOALS.md` | **Yes** | This is your live to-do list |
| `docs/PHILOSOPHY.md`, `docs/ARCHITECTURE.md`, `docs/DOMAIN_MAP.md`, `docs/DATA_FLOW.md` | **Yes, when the system changes** | Treat doc drift as a functional bug |
| `docs/DEVLOG.md` | Append only via `checkin` | The CLI maintains chronological order |
| `mythic/status.json`, `mythic/plan.md`, `mythic/loop.md` | **No** | Owned by the CLI; let `checkin` / `next` manage them |
| `mythic/handoffs/`, `mythic/verifications/`, `mythic/packets/` | **No** | Append-only artifacts; never delete |

---

### Three commands you should know exist

```bash
mythic-vibe examples   # Copy-paste examples for the most common moves
mythic-vibe guide      # The compact operator guide (the seven phases at a glance)
mythic-vibe tutorial   # The full first-session walkthrough, in CLI form
mythic-vibe doctor     # Validate project structure and surface any drift
```

Run them whenever you forget what's possible. The CLI is designed to teach you itself.

---

### Common first-day situations

- **"I made a mess. How do I undo?"** — Mythic Vibe writes append-only records. You can manually delete files under `mythic/` if you really want to start over, but more often you just run `mythic-vibe checkin` again with a corrected `--update` and move on. The DEVLOG keeps the trail honest.
- **"I want to try the loop without committing real work."** — Append `--dry-run` to any command. It will print what it would do and write nothing.
- **"I'm not sure which phase I'm in."** — Run `mythic-vibe status`. The CLI is the source of truth.
- **"I want to add a feature to the CLI itself."** — Read `docs/COMMAND_CONTRACTS.md` and `docs/api.md` first. The plugin system (see `docs/plugins.md`) is usually the right extension surface.
- **"I want a visual instead of text."** — `mythic-vibe tui` (after `pip install -e ".[tui]"` or the equivalent extras install above).

---

For complete onboarding with deeper examples and edge cases, read `docs/quickstart.md`. For the full command surface, `docs/COMMAND_CONTRACTS.md`. For the seven-phase methodology in depth, `MYTHIC_ENGINEERING.md` (created by `init`) and `docs/PHILOSOPHY.md`.

---

## ChatGPT / Codex / Claude bridge workflow

When the work ahead calls for a sharper blade than local tooling alone provides, this is how you cross the bridge cleanly. Two equivalent paths — pick the one that fits your style.

### Modern path — `packet create` (recommended)

```bash
# Generate a packet for any role + phase
mythic-vibe packet create \
  --task "Implement the CLI command parser and file templates" \
  --phase plan \
  --role "Forge Worker" \
  --audience advanced

# Lint the packet before sending (catches vague intent, weak architecture anchors, etc.)
mythic-vibe packet lint
```

The packet lands as Markdown + JSON under `mythic/packets/`. Open it, paste into the assistant of your choice, do the work, then log the outcome.

### Legacy aliases — `codex-pack` / `codex-log`

These remain supported for backwards compatibility:

```bash
mythic-vibe codex-pack --phase plan --task "..." --audience beginner
# (open mythic/codex_prompt.md, paste into the assistant)
mythic-vibe codex-log --phase build --response "Implemented parser with subcommands"
mythic-vibe status
```

### End-to-end forge orchestration

For a full six-role pass (Skald → Architect → Cartographer → Forge Worker → Auditor → Scribe), see `mythic-vibe forge --help`. `forge run --provider <name>` executes against a configured AI provider; `forge resume` (or the `verify --replay` shortcut) picks up from the first non-succeeded step.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/2628f01e-d7fd-4923-84de-e19630282130.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/2628f01e-d7fd-4923-84de-e19630282130.jpg)

---

## Configuration model

The tool reads configuration from multiple sources and honors the closest one. Precedence flows low to high:

1. `~/.mythic-vibe.json`
2. `$XDG_CONFIG_HOME/mythic-vibe/config.json`
3. `<project>/.mythic-vibe.json`
4. Environment variable overrides

These environment variables override any file-based value at runtime:

**Core runtime:**

- `MYTHIC_EXCERPT_LIMIT` — char cap for method-excerpt embedding in packets
- `MYTHIC_PACKET_CHAR_BUDGET` — char cap for full-packet output
- `MYTHIC_AUTO_COMPACT` — auto-compact recent events into the context window
- `MYTHIC_METHOD_SOURCE` — override the Mythic Engineering method-source URL
- `MYTHIC_AI_PROVIDER` — override the companion shell AI provider selection
- `MYTHIC_AI_MODEL` — override the companion shell AI model selection
- `MYTHIC_TIMING` — when set to `1` / `true` / `yes` / `on`, prints a startup-and-command profile to stderr
- `MYTHIC_RICH` — opt-in rich-text rendering when the `[ux]` extra is installed
- `MYTHIC_EVENT_LOG_LIMIT` — positive int overrides the 200-entry event-log default
- `MYTHIC_SNAPSHOT_UPDATE` — set to `1` to regenerate test JSON snapshots

**Plugins + AI providers:**

- `MYTHIC_PLUGIN_TIMEOUT_SEC` — soft per-plugin invocation timeout
- `MYTHIC_PLUGIN_BREAKER_THRESHOLD` — consecutive-failure count that trips the plugin circuit breaker (default 3)
- `MYTHIC_OTEL_ENABLED` — gate the OpenTelemetry exporter (`[otel]` extra)
- `MYTHIC_ISLAND_<NAME>_ENABLED` — gate the Yggdrasil / MindSpark / WYRD island adapters

**Surfaces:**

- `MYTHIC_CHAT_BRIDGE_ENABLED` — master gate for the Matrix / Telegram chat-bridge surfaces
- `MYTHIC_VOICE_TTS_ENABLED` — gate the Chatterbox TTS adapter
- `MYTHIC_TUI_PANELS` — comma-separated opt-in TUI panel selection (also accepts the `--panels` flag)
- `MYTHIC_HERMES_TOKEN` — token for the Hermes HTTP API surface (`mythic-vibe surface hermes`)

**Distribution channels (PH-22 launchers + WASI):**

- `MYTHIC_LAUNCHER_CACHE` — redirect the Rust launcher's per-user cache root (default: `~/.cache/mythic-vibe-launcher/`)
- `MYTHIC_LAUNCHER_REQUIRE_SHA` — set to `1` to require a verified SHA256 entry for the host triple (strict mode); default is lenient with a warning
- `MYTHIC_LAUNCHER_MIRRORS` — comma-separated additional download URLs for the launcher's python-build-standalone fetch (supports `__VERSION__` / `__TAG__` / `__TRIPLE__` placeholders for internal artifactory mirrors)
- `MYTHIC_WASI_CACHE` — redirect the WASI cross-build cache root (default: `~/.cache/mythic-vibe-wasi-build/`)
- `MYTHIC_LEAK_GUARD_DISABLED` — disable the test-suite session-scope leak guard (used only when running an intentional regression test for the leak pattern)

**App data + cost guards (PH-24.6 documentation completeness):**

- `MYTHIC_HOME` — override the per-user app-data root (default: `~/.mythic-vibe/`); used for the method-source cache + cross-project state
- `MYTHIC_HOOKS` — colon-separated path list of operator-supplied hook scripts (run before / after specific commands; opt-in)
- `MYTHIC_DAILY_COST_CAP_USD` — positive float; when set, the AI cost guard blocks any provider call that would push the running daily total above the cap. Unset = no cap.
- `MYTHIC_PATH_RE` — override the regex used by ``robustness/path_audit.py`` to detect operator-supplied absolute paths in produced artifacts (default catches Windows + POSIX patterns)
- `MYTHIC_TUI_NARROW` — set to `1` to force the narrow-layout TUI even when the terminal would otherwise pick the wide layout (useful for split-pane terminal multiplexers)

**MCP protocol tuning (PH-13 / `[mcp]` extra):**

- `MYTHIC_MCP_READ_TIMEOUT` — positive float; per-message read timeout in seconds for the MCP stdio transport (default 60s)
- `MYTHIC_MCP_MAX_DISCARD` — positive int; max number of malformed protocol frames to skip before declaring the peer unrecoverable (default 16)

**Chat-bridge per-backend config (set under `MYTHIC_CHAT_BRIDGE_ENABLED=1`):**

Matrix backend:

- `MYTHIC_CHAT_MATRIX_HOMESERVER` — Matrix homeserver URL (e.g. `https://matrix.example.com`)
- `MYTHIC_CHAT_MATRIX_ACCESS_TOKEN` — bot's access token
- `MYTHIC_CHAT_MATRIX_USER_ID` — bot's full Matrix user id (e.g. `@bot:matrix.example.com`)
- `MYTHIC_CHAT_MATRIX_ROOM_ID` — primary room the bot joins on start
- `MYTHIC_CHAT_MATRIX_ALLOWED_ROOMS` — comma-separated allow-list of room ids (default: room id only)
- `MYTHIC_CHAT_MATRIX_SYNC_TIMEOUT_MS` — long-poll sync timeout in milliseconds (default 30000)

Telegram backend:

- `MYTHIC_CHAT_TELEGRAM_BOT_TOKEN` — Bot API token from BotFather
- `MYTHIC_CHAT_TELEGRAM_CHAT_ID` — primary chat id the bot replies into
- `MYTHIC_CHAT_TELEGRAM_API_ROOT` — Bot API base URL (default `https://api.telegram.org`); override for self-hosted relays
- `MYTHIC_CHAT_TELEGRAM_ALLOWED_CHATS` — comma-separated allow-list of chat ids (default: chat id only)
- `MYTHIC_CHAT_TELEGRAM_ALLOWED_USERS` — comma-separated allow-list of user ids permitted to invoke commands (default: empty = open chat-wide)
- `MYTHIC_CHAT_TELEGRAM_POLL_TIMEOUT_S` — getUpdates long-poll timeout in seconds (default 30)

**Yggdrasil islands (operator-controlled adapters):**

- `MYTHIC_ISLAND_YGGDRASIL_ENABLED` — opt-in gate for the Yggdrasil island provider (`ai run --provider yggdrasil`)
- `MYTHIC_ISLAND_MINDSPARK_ENABLED` — opt-in gate for the MindSpark ThoughtForge island provider
- `MYTHIC_ISLAND_WYRD_ENABLED` — opt-in gate for the WYRD Protocol island provider
- `MYTHIC_ISLAND_CHATTERBOX_ENABLED` — opt-in gate for the Chatterbox TTS island

All gates default to off; setting any to `1` / `true` / `yes` / `on` opts that island in. See `docs/PHILOSOPHY.md` for the operator-sovereignty rationale.

To see what the tool is actually reading in your current project:

```bash
mythic-vibe config --path .
```

Example config:

```json
{
  "codex": {
    "excerpt_limit": 2200,
    "packet_char_budget": 14000,
    "auto_compact": true
  }
}
```

---

## Documentation governance and continuity

Documentation is not decoration here — it is the thread that connects this session to the next one, and the one after that. This project carries an explicit governance layer to keep that thread from fraying:

- `docs/INDEX.md` is the canonical documentation map — start every return visit there.
- `docs/DOCUMENTATION_STANDARDS.md` defines writing obligations and update expectations for contributors.
- `docs/SESSION_HANDOFF_TEMPLATE.md` provides a structured end-of-session handoff that future-you will be glad exists.
- `DEVLOG.md` and `CHANGELOG.md` are maintained as paired historical records — narrative continuity alongside release-facing history.
- `docs/runtime.md` and `docs/plugins.md` are the operator-facing guides for the runtime primitives and the plugin system, respectively.
- `docs/COMMAND_CONTRACTS.md` records the durable contract surface of every CLI command.

When you change behavior, update the docs in the same commit or PR. Treat documentation drift as a functional bug, not an editorial nicety.

---

## Command overview

Mythic Vibe CLI exposes the following command families. Run `mythic-vibe <command> --help` for full options on each.

### Project lifecycle
- `init` / `start` / `imbue` — initialize Mythic scaffolding (PH-20: opt-in `--interactive` Q&A wizard with optional sample-artefact scaffolds)
- `status` — show current Mythic progress summary
- `state` — inspect and validate Mythic project state
- `doctor` / `scry` — validate project structure, run diagnostics, surface drift findings + AI-catalog freshness; PH-20 `--fix` / `--fix-dry-run` auto-remediates safe scaffolding gaps without touching user-authored content

### Authoring loop
- `checkin` — log a Mythic phase update and advance tracking
- `intent` / `constraints` / `architecture` / `plan` / `build` — workflow-phase capture commands (each writes a Mythic Phase Record under `mythic/checkins/`)
- `reflect` — create a reflection handoff for the current session
- `resume` — summarize the latest handoff and suggest the next step
- `handoff` — create, inspect, or list session handoff records
- `weave` — record documentation synchronization checkpoint
- `prune` — suggest dead-code pruning workflow
- `heal` — guide a test-healing workflow

### Context + packets
- `scan` — build a local project index for AI context
- `import-md` — import all Markdown files from the Mythic Engineering repo
- `codex-pack` / `evoke` — legacy aliases for prompt-packet generation
- `codex-log` — record a check-in update after receiving an AI response
- `packet create|show|list|ingest|diff|lint` — packet artifacts (PH-20: `lint` runs a 7-rule heuristic quality check)
- `workflow plan|run|packets|history|lineage` — six-role orchestration (PH-20: `lineage` renders a Mermaid graph of one workflow's per-step ledger)

### Six-role forge (PH-03)
- `forge plan|run|resume|ledger|reflection` — multi-agent forge cycle. `forge run --provider <name>` executes end-to-end; `forge resume` (or `verify --replay`) picks up from the first non-succeeded step

### Verification + governance
- `verify` — run verification gates (commands, changed files, docs, invariants) and write a durable record. PH-20: `--replay` shortcut delegates to `forge resume`
- `drift` — scan for docs↔code drift. PH-20: `drift dashboard` rolls up findings as a category × severity scorecard
- `provenance verify|attest` — PH-20: SHA-256 verification + per-line modification attestation against an explicit upstream original
- `review architecture` — PH-20: quarterly governance-review checklist (cadence in `docs/governance/quarterly_review.md`)
- `oath` — display the responsible AI usage oath
- `method` — inspect and sync the active Mythic Engineering method profile
- `sync` — sync Mythic Engineering method notes from GitHub

### Extensibility
- `grimoire add|list` — manage plugins (registration)
- `plugin list|inspect|disable|doctor` — PH-20: `doctor` audits declared capabilities + circuit-breaker state
- `plunder inspect|plan|fetch|apply|record` — lawful single-file reuse from open-source upstreams
- `ai providers|test|run|stream|ingest-response|models|telemetry|route|recommend` — optional AI provider integrations. PH-20: `recommend` is a pure-policy model picker against the static catalog
- `persona apply|show` — PH-20: opt-in operator presets (`solo` / `team-lead` / `auditor`) writing `mythic/persona.json`
- `slash list|inspect` — inspect + introspect the slash-command catalog (built-in + plugin-contributed)
- `hermes tools|inspect|invoke` — v1.0 / Hermes: list + inspect + invoke the curated agent-tool surface from the CLI without HTTP. See [`docs/HERMES_AGENT.md`](docs/HERMES_AGENT.md).
- `surface hermes [--bind ADDR --port N --token TOKEN]` — v1.0 / Hermes: launch the token-protected HTTP API for external agents.

### Operator helpers
- `examples` — copy-paste command examples
- `guide` — compact operator guide
- `next` — show the next recommended phase and command
- `explain` — explain phases and artifacts
- `tutorial` — first full workflow tutorial
- `completion` — print shell completion script
- `config set` — show or manage configuration values
- `db migrate` — database maintenance tasks
- `voice transcribe|say` — local-first speech transcription + TTS (opt-in via `--engine` and the `MYTHIC_VOICE_TTS_ENABLED` env var)
- `surface chat|web-terminal|ssh-doctor` — alternate access surfaces (chat-bridge, browser, SSH)

### Dev-tool wrappers (PH-02 slice 2.2)
- `test` / `lint` / `typecheck` / `scaffold` / `changelog` / `version` / `ci` / `docker` — convenience wrappers around `pytest` / `ruff` / `mypy` and project-tooling tasks

### Interactive surfaces
- `shell` — open the minimal REPL
- `tui` — open the Textual TUI (requires the `[tui]` extra). PH-20: `--panels heatmap,risk` opts into the new diagnostic panels

For full command behavior and contracts, see `docs/api.md` and `docs/COMMAND_CONTRACTS.md`.

---

## Runtime primitives

`mythic_vibe_cli/runtime/` holds ten small, single-purpose primitives that the rest of the CLI builds on. Each is self-contained, tested directly under `tests/`, and re-exported from `mythic_vibe_cli.runtime`.

| Primitive | Purpose | Wired today |
|---|---|---|
| `file_mutation_queue` | Per-resolved-path serialization for mutation operations (symlinks share the same queue via `os.path.realpath`) | Packet write paths |
| `output_guard` | Reroute `sys.stdout` writes to `sys.stderr` while preserving a "real stdout" path for protocol output | Every `--json` command |
| `event_bus` | Synchronous publish/subscribe with exception-isolated handlers | `PluginHookDispatcher` |
| `timings` | Lightweight elapsed-time profiling, env-gated by `MYTHIC_TIMING` | `app.main()` startup boundaries |
| `slash_commands` | Typed catalog of slash command names + sources (`builtin` / `extension` / `prompt` / `skill` / `plugin`) | `slash list`, `shell` `/help`, TUI picker |
| `source_info` | Provenance dataclass for extension/plugin/skill/prompt-contributed artifacts | `SlashCommandInfo`; `slash list` |
| `exec` | Subprocess execution with timeout and cancel-event (cross-platform; missing binaries return `code=127` instead of raising) | `verify/test_runner.py`, `verify/git_diff.py`, `handoff.py`, `context/scanner.py` |
| `event_log` | Bounded JSONL append-and-tail at `mythic/events.jsonl` (last 200 entries; atomic rotation) | `PluginHookDispatcher.emit()`; TUI Recent Events panel |
| `cross_process_lock` (PH-19) | OS-level cross-process lock — `fcntl.flock` on POSIX, `msvcrt.locking` on Windows. Auto-releases when the holding process dies (no stale-lockfile blocking) | `forge_ledger.py`, `json_store.py:FileLock` opt-in |
| `atomic_write` (PH-19) | Write-tmp + `os.replace` helper with Windows `PermissionError` retry. Catches `BaseException` so `KeyboardInterrupt`/`SystemExit` don't leave orphan tmp files | `verify/__init__.py`, `handoff.py`, `forge_reflection.py`, the doctor-fix + persona helpers |

For deeper coverage and composition patterns, read `docs/runtime.md`.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/Viking_Apache_V2_1.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/Viking_Apache_V2_1.jpg)

---

## Repository posture (important)

This repository holds multiple historical, research, and vendor islands accumulated over the life of the project. Not everything here is the active product. The living path is:

- **`mythic_vibe_cli/`**

Supporting active paths include:

- `tests/`
- `docs/`
- selected root governance records (`README`, `ARCHITECTURE`, `DATA_FLOW`, `DEVLOG`, `CHANGELOG`)

Most other trees are not active CLI runtime dependencies. Treat them as reference material or isolated experiments unless an architecture decision has explicitly drawn them into the product path.

---

## Documentation map

If you do not know where to stand, begin here and follow the stones in order:

**Getting started**
- [`docs/INDEX.md`](docs/INDEX.md) — canonical docs landing (also the mkdocs-material site home)
- [`docs/contributor_index.md`](docs/contributor_index.md) — deep contributor-orientation hub linking every doc
- [`docs/quickstart.md`](docs/quickstart.md) — first project, first loop, first reflection in five minutes
- [`docs/INSTALL.md`](docs/INSTALL.md) — full install matrix (all 11+ channels)

**Operator guides**
- [`docs/HERMES_AGENT.md`](docs/HERMES_AGENT.md) — agent control plane (TCL + HTTP API)
- [`docs/CHAT_BRIDGE_DEPLOYMENT.md`](docs/CHAT_BRIDGE_DEPLOYMENT.md) — Matrix / Telegram bridge deployment
- [`docs/SSH_DEPLOYMENT.md`](docs/SSH_DEPLOYMENT.md) — SSH-surface deployment notes
- [`docs/plugins.md`](docs/plugins.md) — plugin authoring + dispatcher contract
- [`docs/PLUGIN_AUTHORING_GUIDE.md`](docs/PLUGIN_AUTHORING_GUIDE.md) — plugin authoring template + conventions

**Reference**
- [`docs/COMMAND_CONTRACTS.md`](docs/COMMAND_CONTRACTS.md) — durable contract surface for every command
- [`docs/api.md`](docs/api.md) — integration contracts
- [`docs/runtime.md`](docs/runtime.md) — runtime primitives guide (10 primitives)
- [`docs/compatibility_policy.md`](docs/compatibility_policy.md) — v1.0 binding contract (SemVer, support window, deprecation cadence)
- [`docs/hardware_profiles.md`](docs/hardware_profiles.md) — hardware-tier guidance (Pi Zero / Pi 5 / desktop / server)

**Architecture**
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — active runtime architecture
- [`docs/DOMAIN_MAP.md`](docs/DOMAIN_MAP.md) — ownership + boundaries
- [`docs/DATA_FLOW.md`](docs/DATA_FLOW.md) — state and artifact movement
- [`docs/SYSTEM_VISION.md`](docs/SYSTEM_VISION.md) — product north star
- [`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md) — values and engineering stance

**Security + supply chain**
- [`docs/security/verifying_artifacts.md`](docs/security/verifying_artifacts.md) — Sigstore signature + SLSA build provenance verification per channel
- [`docs/security/tag_signing.md`](docs/security/tag_signing.md) — gitsign-based signed-tag maintainer workflow
- [`docs/security/threat_model.md`](docs/security/threat_model.md) — assets, attackers, mitigations (with file:line anchors)
- [`docs/security/sbom.json`](docs/security/sbom.json) — CycloneDX v1.6 dependency manifest

**Governance**
- [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md) — pre-tag manual gates + tag-driven distribution flow
- [`docs/governance/quarterly_review.md`](docs/governance/quarterly_review.md) — architecture-review cadence + agenda
- [`docs/DOCUMENTATION_STANDARDS.md`](docs/DOCUMENTATION_STANDARDS.md) — documentation maintenance rules
- [`docs/SESSION_HANDOFF_TEMPLATE.md`](docs/SESSION_HANDOFF_TEMPLATE.md) — continuity template for session closure

**Distribution channel readmes**
- [`packaging/README.md`](packaging/README.md) — channel inventory + secret table + maintainer-repo sync recipes
- [`packaging/WHEELHOUSE.md`](packaging/WHEELHOUSE.md) — offline-install recipe
- [`packaging/launcher/README.md`](packaging/launcher/README.md) — Rust launcher design + cache layout (PH-22.1)
- [`packaging/android/README.md`](packaging/android/README.md) — Android Gradle/Chaquopy project (PH-22.2) + [`packaging/android/SIGNING.md`](packaging/android/SIGNING.md) for APK keystore setup
- [`packaging/wasi/README.md`](packaging/wasi/README.md) — WASI experimental runtime + [`packaging/wasi/playground/README.md`](packaging/wasi/playground/README.md) for the browser playground

**Continuity records**
- [`DEVLOG.md`](DEVLOG.md) — chronological continuity record
- [`CHANGELOG.md`](CHANGELOG.md) — release-facing change history
- [`docs/ADRS/`](docs/ADRS/) — every architectural decision the project has made (10 ADRs)

---

## Development and quality checks

Before you offer your work to the hall, run the standard checks:

```bash
pytest -q
python -m ruff check mythic_vibe_cli tests scripts tools
python -m mypy mythic_vibe_cli
python tools/contract_audit.py --strict
python -m mythic_vibe_cli --help
mythic-vibe doctor
```

The full test suite lives under `tests/`. As of the latest commit on `development`: **2658 tests + 109 subtests passing**, 1 skipped legitimate POSIX-only. CI runs the same gates in `.github/workflows/ci.yml` across **3 OS × 3 Python + Linux aarch64** rows. Five distinct release workflows trigger on tag push:

- `.github/workflows/release.yml` — PyPI (OIDC trusted publishing) + Homebrew tap + Scoop bucket + AUR + winget + offline wheelhouse
- `.github/workflows/release-oci.yml` — multi-arch GHCR + opt-in Docker Hub
- `.github/workflows/release-binaries.yml` — PyInstaller + Nuitka standalone binaries (4-row OS matrix each)
- `.github/workflows/release-launcher.yml` — Rust launcher binaries (5-row arch matrix; PH-22.1)
- `.github/workflows/release-wasi.yml` — WASI .wasm + .pyz zipapp sidecar (PH-22.3 / PH-23.7+)
- `.github/workflows/release-android.yml` — Android APK (PH-22.2)
- `.github/workflows/docs.yml` — mkdocs-material site (PH-23.1)

All seven release workflows apply Sigstore keyless signing + SLSA Level 3 build provenance attestation to their artifacts.

---

## Acknowledgements — third-party material

Mythic Vibe CLI is independent and original work, but it gratefully adapts a small number of well-tested primitives from open-source upstreams under their permissive licenses. We hold ourselves to the standard recorded in `MYTHIC_ENGINEERING_PLUNDERING_WORKFLOW.md` (License Gate, Boundary Law, Verification Law, Attribution Law) for every line of plundered material:

- Per-file headers name the upstream source, license, copyright holder, and the date adapted.
- The repo-root `THIRD_PARTY_NOTICES.md` reproduces the upstream permission text verbatim and lists every adapted file in a plunder map.
- The repo-root `NOTICE` file records this project's own Apache-2.0 attribution.
- Plunder operations themselves are tracked under `mythic/imports/plunder_manifest.json` when fetched via the `plunder` command.

### Pi (pi-coding-agent)

- **Project:** pi (pi-coding-agent) — package `packages/coding-agent`
- **Repository:** [badlogic/pi-mono](https://github.com/badlogic/pi-mono)
- **License:** MIT License
- **Copyright:** Copyright (c) 2025 Mario Zechner

The following Mythic runtime primitives are adapted from pi-coding-agent under the MIT permission notice reproduced in `THIRD_PARTY_NOTICES.md`. Each carries the standard per-file header and is independently tested in this repository:

| Mythic file | Pi upstream file |
|---|---|
| `mythic_vibe_cli/runtime/file_mutation_queue.py` | `packages/coding-agent/src/core/tools/file-mutation-queue.ts` |
| `mythic_vibe_cli/runtime/output_guard.py` | `packages/coding-agent/src/core/output-guard.ts` |
| `mythic_vibe_cli/runtime/event_bus.py` | `packages/coding-agent/src/core/event-bus.ts` |
| `mythic_vibe_cli/runtime/timings.py` | `packages/coding-agent/src/core/timings.ts` |
| `mythic_vibe_cli/runtime/slash_commands.py` | `packages/coding-agent/src/core/slash-commands.ts` |
| `mythic_vibe_cli/runtime/source_info.py` | `packages/coding-agent/src/core/source-info.ts` (synthetic factory only; PathMetadata-dependent factory not ported) |
| `mythic_vibe_cli/runtime/exec.py` | `packages/coding-agent/src/core/exec.ts` (Node-stdio quirk handler not needed in Python) |

`mythic_vibe_cli/runtime/event_log.py` is original to this project.

This project is independent and is **not** affiliated with, endorsed by, or sponsored by Mario Zechner, the pi-mono authors, or pi.dev.

### Required dependencies (declared in `pyproject.toml`)

- **Textual** (`textual>=0.80`) — pure-Python TUI framework, MIT-licensed, by Will McGugan and contributors. Used by `mythic-vibe tui`. Optional under the `[tui]` extra.
- **Rich** (`rich>=13.0`) — pure-Python rich-text rendering library, MIT-licensed, by Will McGugan and contributors. Optional under the `[ux]` extra.
- **anthropic** (`anthropic>=0.34`), **google-genai** (`google-genai>=1.0`), **openai** (`openai>=1.40`) — official client SDKs for the respective AI providers. Optional under the `[ai]` extra and only loaded when the matching adapter is selected.

The full upstream license text for plundered material lives in `THIRD_PARTY_NOTICES.md`. License files for installed dependencies ship with the corresponding wheels.

---

## License

Copyright (c) 2026 Volmarr Wyrd

Mythic Vibe CLI is licensed under the **Apache License, Version 2.0**. See the [LICENSE](LICENSE) file for the full license text and [NOTICE](NOTICE) for the project attribution.

For third-party material adapted into this codebase, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Per the Apache-2.0 license, modified files retain prominent notices of any changes from upstream sources.

Unless required by applicable law or agreed to in writing, this project is distributed on an "AS IS" BASIS, without warranties or conditions of any kind, either express or implied.

---

## Distribution and Privacy Position

Mythic Vibe CLI is published here as source code and project material.

The author does not require users to provide age, identity, government ID, biometric data, or similar personal information in order to access or use the source code in this repository.

The author may decline to provide official binaries, installers, hosted services, app-store releases, or other official distribution channels where doing so would require age verification, identity verification, or similar personal-data collection.

Any third party who forks, packages, redistributes, deploys, hosts, or otherwise makes this software available does so independently and is solely responsible for compliance with applicable law, platform policy, and distribution requirements in their own jurisdiction and context.

See [LEGAL-NOTICE.md](LEGAL-NOTICE.md) for details.

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-23-RuneForgeAI.jpg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/image-23-RuneForgeAI.jpg)

---

![https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/IMG_0407.jpeg](https://raw.githubusercontent.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/refs/heads/development/IMG_0407.jpeg)

---
