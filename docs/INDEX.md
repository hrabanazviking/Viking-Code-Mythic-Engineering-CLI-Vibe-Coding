# Mythic Vibe CLI

**Beginner-friendly CLI that enforces the Mythic Engineering vibe-coding workflow.**

Mythic Vibe is an opinionated developer-workflow tool. It gives operators a structured surface for capturing intent, verifying changes against architecture rules, and handing off work between sessions — all while staying out of the way for the routine cases.

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
- [Contributor Index](contributor_index.md) — the deep contributor-orientation hub linking every doc in the project.

---

## Distribution channels

The CLI ships through eight channels as of v1.x:

| Channel | Use when |
|---|---|
| **PyPI** (`pipx install`) | Default — works everywhere Python does |
| **Homebrew tap** | macOS / Linuxbrew operators |
| **Scoop bucket** | Windows operators who prefer Scoop |
| **AUR** | Arch Linux operators |
| **winget** | Windows operators who prefer winget |
| **Container** (GHCR) | Docker / Podman / Kubernetes |
| **Standalone binaries** | No-Python-on-host scenarios (PyInstaller / Nuitka) |
| **Launcher** (PH-22.1, foundation) | Tiny initial download + extras supported via cached venv |

Plus three foundation-level v2.0 channels (Android, WASI) tracked in their per-package READMEs.

---

## Project values

Mythic Vibe carries explicit operator-sovereignty guarantees:

- **Stdlib-only base.** The runtime imports zero external packages by default. Every extra is opt-in.
- **Open-source-only deps.** Apache-2.0 (project) + a small set of permissively-licensed libraries.
- **No telemetry.** The CLI calls home only when an operator configures an AI provider.
- **Cryptographic provenance.** Every release artifact ships with Sigstore keyless signatures + SLSA L3 build provenance attestations.
- **Cross-platform invariant.** CI exercises Linux × macOS × Windows × py3.10/3.11/3.12 × x86_64/arm64 on every PR.
