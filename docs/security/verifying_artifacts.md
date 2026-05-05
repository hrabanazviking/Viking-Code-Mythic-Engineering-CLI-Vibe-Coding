# Verifying release artifacts

Mythic Vibe CLI signs every released artifact with [Sigstore](https://www.sigstore.dev/) — keyless cryptographic signatures backed by a Fulcio-issued short-lived certificate and logged in the Rekor transparency log. The signing path uses GitHub Actions OIDC, so there is no long-lived signing key on the project's side that could leak or be compromised.

This guide covers the per-channel verification recipe. Run any of these before trusting a download for a security-sensitive use case.

> **PH-21.5 (2026-05-05):** Sigstore signatures replace the prior "checksums-only" provenance approach (PH-20.6). The SHA256SUMS / SHA512SUMS files still ship as a fast-path pre-flight check, but the cryptographic root of trust now sits with Sigstore.

---

## Quick reference

| Artifact channel | Tool | Identity expected |
|---|---|---|
| PyPI wheel + sdist | `python -m sigstore verify identity` | `https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release.yml@refs/tags/v<VERSION>` |
| Standalone binary (PyInstaller / Nuitka) | `python -m sigstore verify identity` | `https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release-binaries.yml@refs/tags/v<VERSION>` |
| OCI image (GHCR / Docker Hub) | `cosign verify` | `https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release-oci.yml@refs/tags/v<VERSION>` |

Common to all three:

- **OIDC issuer:** `https://token.actions.githubusercontent.com`
- **Signing CA:** Fulcio (Sigstore's public-good CA)
- **Transparency log:** Rekor (`https://rekor.sigstore.dev/`)

---

## PyPI artifacts (wheel + sdist + SBOM)

Each release attaches `.sigstore` bundles next to the wheel + sdist on the GitHub Release page. The bundle wraps signature + certificate + Rekor entry in one file, so you only need a single download to verify.

```bash
VERSION=1.0.0
gh release download "v${VERSION}" \
    --repo hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding \
    --pattern "mythic_vibe_cli-${VERSION}-py3-none-any.whl" \
    --pattern "mythic_vibe_cli-${VERSION}-py3-none-any.whl.sigstore" \
    --pattern "mythic-vibe-cli-${VERSION}.tar.gz" \
    --pattern "mythic-vibe-cli-${VERSION}.tar.gz.sigstore"

# Install the verifier (small dep tree, sigstore-only):
python -m pip install sigstore

# Verify the wheel:
python -m sigstore verify identity \
    --bundle "mythic_vibe_cli-${VERSION}-py3-none-any.whl.sigstore" \
    --cert-identity "https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release.yml@refs/tags/v${VERSION}" \
    --cert-oidc-issuer "https://token.actions.githubusercontent.com" \
    "mythic_vibe_cli-${VERSION}-py3-none-any.whl"

# Verify the sdist with the same pattern:
python -m sigstore verify identity \
    --bundle "mythic-vibe-cli-${VERSION}.tar.gz.sigstore" \
    --cert-identity "https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release.yml@refs/tags/v${VERSION}" \
    --cert-oidc-issuer "https://token.actions.githubusercontent.com" \
    "mythic-vibe-cli-${VERSION}.tar.gz"
```

A successful verify prints:

```
OK: mythic_vibe_cli-1.0.0-py3-none-any.whl
```

Any failure (wrong identity, expired cert, missing Rekor entry, mismatched bundle/file) exits non-zero with a diagnostic.

---

## Standalone binaries (PyInstaller + Nuitka)

The binary signing path is identical — same Sigstore tooling, different `--cert-identity` because a different workflow file emits the signature.

```bash
VERSION=1.0.0
ASSET="mythic-vibe-${VERSION}-linux-x86_64"
gh release download "v${VERSION}" \
    --repo hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding \
    --pattern "${ASSET}" \
    --pattern "${ASSET}.sigstore"

python -m sigstore verify identity \
    --bundle "${ASSET}.sigstore" \
    --cert-identity "https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release-binaries.yml@refs/tags/v${VERSION}" \
    --cert-oidc-issuer "https://token.actions.githubusercontent.com" \
    "${ASSET}"
```

For the Nuitka variant substitute `mythic-vibe-nuitka-${VERSION}-linux-x86_64` for the asset name. The certificate identity is the same workflow file because both PyInstaller and Nuitka builds run inside `release-binaries.yml`.

---

## OCI container image (GHCR + Docker Hub)

Cosign reads the Sigstore signature attached to the OCI manifest in the registry — no separate download needed. The manifest digest (immutable per push) is what's signed, so the signature stays valid even if the floating `:latest` tag is later repointed.

```bash
# Install cosign (pre-built binary — Sigstore project, BSD-3 licensed):
go install github.com/sigstore/cosign/v2/cmd/cosign@latest
# OR via Homebrew:
brew install cosign

VERSION=1.0.0
IMAGE=ghcr.io/hrabanazviking/mythic-vibe-cli:${VERSION}

cosign verify "${IMAGE}" \
    --certificate-identity "https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release-oci.yml@refs/tags/v${VERSION}" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

A successful verify prints the bundled signature payload + Rekor entry. Pin to the digest if you want to anchor against a specific manifest:

```bash
DIGEST=$(docker buildx imagetools inspect "${IMAGE}" --format '{{.Manifest.Digest}}')
cosign verify "ghcr.io/hrabanazviking/mythic-vibe-cli@${DIGEST}" \
    --certificate-identity "https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/.github/workflows/release-oci.yml@refs/tags/v${VERSION}" \
    --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

The same recipe works against the Docker Hub mirror when the `DOCKERHUB_PUBLISH_ENABLED` repo variable is `true` — substitute `docker.io` for `ghcr.io`.

---

## Why keyless?

- **No long-lived signing key.** A traditional GPG-based signing setup would require the project to manage a private key (rotation, revocation, secure storage). A leaked key would compromise every signature ever made with it. Sigstore's keyless flow uses a fresh certificate per signing event, valid for ~10 minutes, tied to the GitHub Actions OIDC identity that issued it.
- **Public transparency log.** Every signature is logged in Rekor, a tamper-evident append-only log. Operators (and security researchers) can audit the full signing history for any artifact independently of the project.
- **No registration required.** Verifiers don't need to fetch a public key or trust a project-specific certificate authority. The trust roots are Sigstore's public-good Fulcio CA + Rekor log, both operated by the OpenSSF.

If you need offline verification (no network reach to Rekor at verify time), `--offline` flags exist on both `sigstore` and `cosign` — but they require the bundle to include the Rekor entry inline, which the Sigstore tooling does by default.

---

## Reproducibility

A signature proves who built and signed the artifact. It does **not** prove that the artifact was built from the source tree the project published. PH-21.6 adds SLSA Level 3 build provenance attestations on top of the signatures so operators can verify both:

- **Who:** the GitHub Actions OIDC identity that signed the artifact (this guide).
- **From what:** the exact commit, workflow, and inputs that produced the artifact bytes (PH-21.6).

Together they close the supply-chain trust gap: a verified signature against an attested build provenance means the artifact you're holding is the one the project's release workflow built from a specific git commit, signed by the workflow's transient identity, and logged in Rekor.

---

## Getting help

If a verification command fails for a release that should be valid, check:

1. **Tag mismatch.** The `--cert-identity` URL must include `@refs/tags/v<VERSION>` matching the exact version you downloaded. A `v1.0.0` artifact won't verify against a `v1.0.1` identity.
2. **Old signature tooling.** sigstore-python ≥ 3.0 and cosign ≥ 2.0 are required for the v1.6+ bundle format.
3. **Asset / bundle mismatch.** The `.sigstore` bundle must come from the same release as the artifact. Mixing a v1.0.0 wheel with a v1.0.1 bundle silently fails verification — both sigstore-python and cosign exit non-zero with a clear diagnostic.

For anything else, open an issue at <https://github.com/hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding/issues> and include the verifier output.
