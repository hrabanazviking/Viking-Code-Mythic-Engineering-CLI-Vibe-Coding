# Security Policy

This document describes how to report vulnerabilities in the Mythic Vibe CLI and what response to expect. It is the **single source of truth** for our security disclosure process — please read it in full before filing a public issue or sending a bug report.

---

## Supported versions

We provide security fixes for the following branches:

| Version stream | Supported |
|---|---|
| **v1.x** (current stable) | yes — security fixes ship in patch releases (`v1.0.x`) |
| **`development` branch** | yes — fixes land here first, then are backported to `v1.x` if needed |
| pre-v1.0 | no — please upgrade to v1.x |

Releases follow [semantic versioning](https://semver.org/) and the [`docs/compatibility_policy.md`](docs/compatibility_policy.md). Security patches that require breaking changes to a Stable-tier surface will be coordinated with a major-version bump and a clear migration path.

---

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.** Public issues are visible immediately to anyone scraping the repository, which gives attackers a window before a patch lands.

### Preferred path: GitHub private vulnerability reporting

The repository has [GitHub private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) enabled. To report:

1. Visit the repository's **Security** tab on GitHub.
2. Click **Report a vulnerability**.
3. Fill in the form. The maintainer is notified privately; the report is invisible to the public until disclosed.

### Alternate path: encrypted email

If you cannot use the GitHub form, send an email to the maintainer with a subject prefix of `[security]`. The repository's `git log` shows the maintainer's contact email.

PGP encryption is optional but appreciated for high-severity reports.

### What to include

A useful report contains:

- **Affected version(s)** (`mythic-vibe --version` output is enough)
- **Affected channel(s)** if you tested specifically against a binary, container, or APK (PyInstaller / Nuitka / OCI / launcher / Android / WASI)
- **Reproduction steps** — the smallest script or command sequence that demonstrates the issue
- **Impact** — what an attacker could do with this (LFI / RCE / privilege escalation / data exfiltration / DoS / etc.)
- **Suggested fix** if you have one — entirely optional, but speeds resolution

If the vulnerability touches an upstream dependency (urllib3, sigstore, slsa-github-generator, etc.), please note that and we'll coordinate with the upstream maintainer.

---

## Response timeline

The maintainer is one human in their off-hours, so the timeline is reasonable rather than enterprise-grade:

| Severity | Acknowledgement | Initial assessment | Patch target |
|---|---|---|---|
| **Critical** (RCE, full auth bypass, key disclosure) | within 48 h | within 7 days | within 14 days |
| **High** (privilege escalation, sensitive-data leak) | within 7 days | within 14 days | within 30 days |
| **Medium / Low** | within 14 days | within 30 days | next scheduled patch release |

For Critical and High, we will coordinate disclosure via a [GitHub Security Advisory](https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/security/advisories) with a CVE assigned through GitHub's CNA. You'll be invited to the private advisory and credited in the published version unless you ask to remain anonymous.

---

## Scope

### In scope

- The `mythic-vibe` / `mythic` CLI binary (any channel)
- The `mythic_vibe_cli/` Python package
- The Hermes Agent HTTP API (`mythic-vibe surface hermes`)
- The chat-bridge surfaces (`MYTHIC_CHAT_BRIDGE_ENABLED=1`)
- Plugin sandbox boundary violations
- Cryptographic provenance pipeline (Sigstore + SLSA + signed tags) — anything that allows an attacker to forge or replay a signed artifact
- The Rust launcher (`packaging/launcher/`) — anything that allows execution of unverified bytes
- The Android wrapper (`packaging/android/`) — anything that breaks the Chaquopy isolation boundary
- The WASI runtime (`packaging/wasi/`) — anything that escapes the WASM sandbox

### Out of scope

- **Operator-controlled config.** If an operator sets `MYTHIC_CHAT_TELEGRAM_BOT_TOKEN=hunter2` and is surprised the token works, that's not a vulnerability. The CLI does not protect operators from their own configuration.
- **Plaintext secrets in operator-controlled files.** Mythic doesn't encrypt the operator's own files. If you `cat` your `.env`, that's expected.
- **Denial-of-service via CPU/memory exhaustion** in long-running TUI / chat-bridge surfaces with no allow-list configured. The built-in defaults are designed for trusted local use; production deployment requires a reverse proxy + rate limiting (operator's responsibility).
- **Issues in optional extras** that the operator must explicitly install (`[ai]`, `[tui]`, `[mcp]`, etc.) — please report those to the relevant upstream package.
- **Issues in dormant in-tree code paths** — `yggdrasil/`, `mindspark_thoughtform/`, vendor mirrors. These are not part of the v1.0 product surface; see `docs/DORMANT_ISLANDS.md`.

If you're unsure whether something is in scope, file the report. We'll triage.

---

## Hardening posture

Mythic Vibe CLI carries explicit security guarantees baked into the v1.0 launch:

- **Stdlib-only base.** The runtime imports zero external packages by default — supply-chain attack surface is exactly the Python standard library.
- **URL scheme guard** (PH-24.5). Every `urllib.request.urlopen` call passes through `runtime/url_guard.py:assert_safe_url`, which rejects any scheme outside `http(s)://` before the request is made. Closes the `file:///` LFI class of vulns.
- **Path-escape guards** in artifact-reading endpoints (Hermes `read_artifact`, plugin sandbox, plunder cache).
- **Constant-time token comparison** (`secrets.compare_digest`) on the Hermes HTTP API and web-terminal surfaces.
- **Loopback-only defaults** for every network surface. External exposure requires explicit operator action (`--bind 0.0.0.0` + reverse-proxy TLS).
- **Cryptographic provenance** end-to-end. Every release artifact ships with Sigstore keyless signatures (Fulcio + Rekor) + SLSA L3 build provenance attestations. Verification recipes per channel: [`docs/security/verifying_artifacts.md`](docs/security/verifying_artifacts.md).
- **Signed tags** via gitsign. `git verify-tag v1.0.0` confirms the tag was created by GitHub Actions OIDC.
- **No telemetry.** The CLI never calls home unless the operator explicitly configures an AI provider.

---

## Disclosure attribution

By default, we credit reporters in:

- The published GitHub Security Advisory
- The CHANGELOG entry for the patch release
- The `docs/SECURITY_HALL_OF_FAME.md` if the issue was Critical or High severity (planned; not yet established as of v1.0.0)

If you would prefer to remain anonymous, say so in your report and we will honor that choice.

---

## Bug bounty

There is no formal bug bounty program. The maintainer is a single human in off-hours and cannot fund payouts. We will, however:

- Send a thank-you and credit you publicly (per your preference).
- Hand-deliver a formal acknowledgement letter on request — useful for security researchers building disclosure portfolios.

---

## Related documents

- [`docs/security/verifying_artifacts.md`](docs/security/verifying_artifacts.md) — per-channel Sigstore + SLSA verification recipes
- [`docs/PLUGIN_AUTHORING_GUIDE.md`](docs/PLUGIN_AUTHORING_GUIDE.md) — plugin capability + sandbox model
- [`docs/compatibility_policy.md`](docs/compatibility_policy.md) — what's stable, deprecation policy
- [`mythic_vibe_cli/runtime/url_guard.py`](mythic_vibe_cli/runtime/url_guard.py) — URL scheme guard implementation

Last updated: 2026-05-06.
