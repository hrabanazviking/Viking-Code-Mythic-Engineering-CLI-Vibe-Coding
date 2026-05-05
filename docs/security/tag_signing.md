# Tag signing (maintainer guide)

This guide is for **maintainers** cutting a release. End-users verifying a release should read [`verifying_artifacts.md`](verifying_artifacts.md) instead.

Mythic Vibe CLI release tags are signed using [`gitsign`](https://docs.sigstore.dev/cosign/signing/gitsign/) — Sigstore's keyless equivalent of GPG-signed commits and tags. The signing pattern matches the rest of the project's PH-21.5 + PH-21.6 cryptographic surface: short-lived Fulcio cert via OIDC, Rekor transparency log entry, no long-lived signing key on the maintainer's machine.

> **PH-21.6 (2026-05-05):** This guide formalizes the tag-signing path that complements the per-artifact signatures. A signed tag closes the supply-chain loop: the workflow's per-artifact attestations prove the artifact came from a specific commit; a signed tag proves which commit was *intended* to be the release. Without a signed tag a malicious push could swap commits silently.

---

## One-time setup

```bash
# Install gitsign:
# Linux/macOS via Homebrew:
brew install gitsign

# Or via Go (any platform):
go install github.com/sigstore/gitsign@latest

# Configure git to use gitsign for tag signing:
git config --local gpg.x509.program gitsign
git config --local gpg.format x509
git config --local tag.gpgSign true        # auto-sign every tag
git config --local commit.gpgSign true     # optional: also sign commits
```

These settings are local to the repo (the `--local` flag), so the project doesn't impose gitsign on contributors who only push code.

---

## Cutting a signed release tag

```bash
# Make sure you're on the right branch + commit:
git checkout main
git pull

# Create the signed tag — gitsign opens a browser for OIDC auth.
git tag -s v1.1.0 -m "Release v1.1.0"

# Verify the tag's signature locally before pushing:
git verify-tag v1.1.0
# Should print: "Good signature ... certificate identity: <your GitHub email>"

# Push the tag to trigger the release pipeline:
git push origin v1.1.0
```

The `-s` flag tells git to sign with the configured X.509 program — gitsign in this case. gitsign:

1. Opens a browser window for GitHub / Google / Microsoft OIDC sign-in (one-click if already signed in).
2. Requests a short-lived Fulcio cert bound to the OIDC identity.
3. Signs the tag object with that cert.
4. Logs the signing event in Rekor.
5. Embeds the signature + cert + Rekor entry in the tag itself, just like a GPG-signed tag.

The cert expires in ~10 minutes, so even if it leaked it can't be reused. Re-signing for a future tag triggers a fresh OIDC flow and a fresh cert.

---

## Verifying a tag

End-users (or other maintainers) can verify a tag's signature without installing gitsign — `git verify-tag` works against any X.509-signed tag once the Sigstore root CA is trusted:

```bash
# One-time: trust Sigstore's Fulcio CA bundle (in the system trust store).
# On macOS / Linux this is usually a one-line install:
curl -fsSL https://raw.githubusercontent.com/sigstore/cosign/main/release/cosign.pub > /tmp/sigstore-root.pub
# (full chain-of-trust setup varies per OS; see https://docs.sigstore.dev/)

# Verify:
git verify-tag v1.1.0
```

For richer verification including the Rekor transparency log entry:

```bash
gitsign verify --certificate-identity "$MAINTAINER_EMAIL" \
               --certificate-oidc-issuer https://github.com/login/oauth \
               $(git rev-parse v1.1.0)
```

---

## What the tag signature does NOT prove

A signed tag tells you "this commit was tagged by an authorized maintainer." It does NOT tell you:

- That the source tree at the tag is reproducible (use the build attestations from PH-21.6 for that — see `verifying_artifacts.md`).
- That the published artifacts (wheel, sdist, OCI image, binaries) match the tagged source (also build attestations).
- That the maintainer's OIDC account itself is uncompromised (out-of-scope for cryptography; rely on 2FA and account-recovery hygiene).

The supply-chain trust chain is:

1. **Tag signature** — proves which commit was intended as the release.
2. **Build provenance attestations** (PH-21.6) — prove which artifact bytes came from which commit + workflow.
3. **Sigstore artifact signatures** (PH-21.5) — prove which artifact bytes were signed by which workflow run.
4. **Operator verification** — combines all three to verify the artifact you have is the one the project intended to ship from a specific reviewable source tree.

---

## Fallback: GPG signing

If gitsign is unavailable on the maintainer's platform (e.g. an air-gapped release machine), GPG signing remains supported:

```bash
# One-time: configure git to use GPG with your key.
git config --local user.signingkey <GPG_KEY_ID>
git config --local commit.gpgSign true
git config --local tag.gpgSign true

# Cut the tag:
git tag -s v1.1.0 -m "Release v1.1.0"
```

The maintainer's GPG public key must be uploaded to a public keyserver and recorded in this directory at `docs/security/maintainer_keys.asc` (placeholder — file lands when a maintainer first uses the GPG path). Operators verify with `git verify-tag` against the keyring.

GPG is the older / less convenient option but interoperates with every git host and tool. gitsign is preferred for new releases because it doesn't require key management.

---

## Releases tagged via the GitHub web UI

Tags created via the GitHub Releases web UI are NOT signed — there's no gitsign or GPG hook in that flow. **Releases must be tagged from the maintainer's CLI** to get a signed tag. This is documented in `docs/RELEASE_CHECKLIST.md` as part of the pre-tag manual gate.

If a release is accidentally tagged via the web UI, the recovery path is:

1. Delete the unsigned tag (`git push origin :refs/tags/vX.Y.Z`).
2. Re-create it locally with a signed tag (`git tag -s vX.Y.Z`).
3. Push the signed tag.

The release workflow re-runs against the new tag (same commit, same artifacts, fresh signatures + attestations).
