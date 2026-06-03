# Mythic Vibe CLI

**Beginner-friendly CLI that enforces the Mythic Engineering vibe-coding workflow.**

Mythic Vibe is an opinionated developer-workflow tool. It gives operators a structured surface for capturing intent, verifying changes against architecture rules, and handing off work between sessions — all while staying out of the way for the routine cases.

> **Reforge direction:** Mythic is being corrected into a terminal-based coding companion CLI. The primary entrypoint is `mythic`, which should open an interactive shell where the user talks naturally to the model. See [Product Intent](PRODUCT_INTENT.md).

```bash
# Install:
pipx install mythic-vibe-cli

# Initialize a project:
mythic-vibe init

# Capture intent for a slice of work:
mythic-vibe imbue "Add OAuth login flow"

# Run pre-flight checks:
mythic-vibe doctor --json

# Verify a finished slice:
mythic-vibe verify
```

---

## Where to start

<div class="grid cards" markdown>

-   :material-rocket-launch: **Quickstart**

    ---

    Run the first command, capture an intent packet, and finish a slice with verify in under five minutes.

    [:octicons-arrow-right-24: Quickstart](quickstart.md)

-   :material-download: **Install Guide**

    ---

    Pick the install channel that matches your situation — PyPI / Homebrew / Scoop / AUR / OCI / standalone binaries / Termux / Android / WASI.

    [:octicons-arrow-right-24: Install Guide](INSTALL.md)

-   :material-robot-outline: **Hermes Agent**

    ---

    The TCL + HTTP API control plane that lets external AI agents drive the CLI surface end-to-end.

    [:octicons-arrow-right-24: Hermes Agent](HERMES_AGENT.md)

-   :material-shield-check: **Verifying Artifacts**

    ---

    Verify a release with Sigstore signatures + SLSA build provenance attestations. Per-channel recipes for PyPI, OCI, and standalone binaries.

    [:octicons-arrow-right-24: Verifying Artifacts](security/verifying_artifacts.md)

</div>

---

## Companion Shell

Mythic operates primarily as an interactive coding companion. Read the following documentation to understand the shell workflow:

- [Product Intent](PRODUCT_INTENT.md) — the reforge direction: coding companion CLI first, command catalog second.
- [Interactive Shell](INTERACTIVE_SHELL.md) — the primary conversational loop.
- [Slash Commands](SLASH_COMMANDS.md) — secondary explicit controls.
- [Daily Workflow](DAILY_WORKFLOW.md) — a standard day using the companion.
- [Project Memory](MEMORY.md) — how Mythic retains session context.
- [Private Knowledge](KNOWLEDGE.md) — integrating external documents.
- [GitHub Workspace](GITHUB_WORKSPACE.md) — conversational branch and PR management.
- [Cockpit TUI](TUI.md) — the visual interface for the shell.
- [Internal Tools](INTERNAL_TOOLS.md) — how legacy commands power the shell machinery.

---

## Project shape

The CLI is **architecture-first**: every command operates against a `mythic/` directory under your project that captures intent, decisions, verification results, and architectural anchors. The base CLI is **stdlib-only** — every external dependency is opt-in via an extras (`ai`, `tui`, `ux`, `otel`).

For the full design rationale see:

- [Philosophy](PHILOSOPHY.md) — why the workflow looks the way it does.
- [Architecture](ARCHITECTURE.md) — module boundaries, data flow, runtime invariants.
- [System Vision](SYSTEM_VISION.md) — where the project is heading.

---

## Reference & operations

- [Command Contracts](COMMAND_CONTRACTS.md) — the canonical surface; every command, flag, and exit code.
- [Compatibility Policy](compatibility_policy.md) — what's stable, what's experimental, what can change between releases.
- [Plugin Authoring Guide](PLUGIN_AUTHORING_GUIDE.md) — how to extend the CLI with operator-supplied plugins.
- [Troubleshooting](TROUBLESHOOTING.md) — common issues, organised by symptom: install / doctor / AI provider / plugins / TUI / chat-bridge / Hermes / cross-platform / tests / release verification.
- [Security Policy](../SECURITY.md) — how to report vulnerabilities, supported versions, response timeline, in-scope vs out-of-scope.
- [Contributor Index](contributor_index.md) — the deep contributor-orientation hub linking every doc in the project.

---

## Distribution channels

The CLI ships through **eleven channels** as of v1.x, plus three v2.0 foundations:

| Channel | Use when |
|---|---|
| **PyPI** (`pipx install`) | Default — works everywhere Python does |
| **Homebrew tap** | macOS / Linuxbrew operators |
| **Scoop bucket** | Windows operators who prefer Scoop |
| **AUR** | Arch Linux operators |
| **winget** | Windows operators who prefer winget |
| **Container** (GHCR + opt-in Docker Hub) | Docker / Podman / Kubernetes |
| **Standalone PyInstaller binaries** | No-Python-on-host scenarios; offline-friendly first run |
| **Nuitka alternative binaries** | Smaller binary + faster cold start than PyInstaller |
| **Termux** (Android) | Linux-style CLI on Android phones / tablets |
| **Offline wheelhouse** | Air-gapped install (Pi Zero, hardened CI) |
| **Launcher binary** (PH-22.1, foundation) | ~3-5 MB static binary; downloads python-build-standalone + the wheel on first run; supports installing extras via pip |

Plus three v2.0 foundations:

| Channel | Status | Best for |
|---|---|---|
| **Native Android app** (Chaquopy) | foundation | One-tap Android install with a Material 3 UI; complementary to Termux |
| **WASI runtime** (`.wasm` + `.pyz` zipapp sidecar) | foundation | Run the CLI under Wasmtime / wasmer / browsers |
| **WASI browser playground** | foundation | Static HTML+JS preview hosted next to the docs site |

Every release artifact across every channel is Sigstore-signed + SLSA-attested. Verification recipes per channel: [Verifying Artifacts](security/verifying_artifacts.md).

---

## Project values

Mythic Vibe carries explicit operator-sovereignty guarantees:

- **Stdlib-only base.** The runtime imports zero external packages by default. Every extra is opt-in.
- **Open-source-only deps.** Apache-2.0 (project) + a small set of permissively-licensed libraries.
- **No telemetry.** The CLI calls home only when an operator configures an AI provider.
- **Cryptographic provenance.** Every release artifact ships with Sigstore keyless signatures + SLSA L3 build provenance attestations.
- **Cross-platform invariant.** CI exercises Linux × macOS × Windows × py3.10/3.11/3.12 × x86_64/arm64 on every PR.
