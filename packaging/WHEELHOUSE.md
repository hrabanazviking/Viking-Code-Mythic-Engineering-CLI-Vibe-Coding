# Offline install via the wheelhouse

Every Mythic Vibe CLI release ships a pre-built wheelhouse —
the project wheel plus every wheel for the `[ai]`, `[otel]`,
`[ux]`, and `[tui]` extras' transitive dependencies — packaged
as `mythic-vibe-cli-<VERSION>-wheelhouse.tar.gz` on the
GitHub Releases page.

This is the supported path for installing Mythic Vibe CLI on:

- Air-gapped workstations with no PyPI access.
- Hardened CI runners that block egress to `files.pythonhosted.org`.
- Pi tier hardware (Pi Zero / Pi 5) where `pip install` over a
  thin link is too slow or repeatedly times out.
- Compliance environments that require all dependencies to be
  vendored and reviewed before installation.

## Verifying the artifact

Each release attaches a `SHA256SUMS` file. Verify before
extracting:

```bash
# Adjust VERSION to the release you're installing.
VERSION=1.0.0

# Download the artifact and the checksum file from the release
# page. (The exact URL depends on your tooling — gh, curl, browser.)
gh release download "v${VERSION}" \
    --repo hrabanazviking/Viking-Code-Mythic-Engineering-CLI-Vibe-Coding \
    --pattern "mythic-vibe-cli-${VERSION}-wheelhouse.tar.gz" \
    --pattern "SHA256SUMS"

sha256sum --check --ignore-missing SHA256SUMS
```

A clean run prints the line ending in `OK`. Any other output
(or non-zero exit) means the artifact was tampered with or
corrupted in transit — do **not** install.

## Installing from the wheelhouse

Once verified:

```bash
tar -xzf "mythic-vibe-cli-${VERSION}-wheelhouse.tar.gz"
python -m venv ~/mythic-venv
source ~/mythic-venv/bin/activate     # POSIX
# .\mythic-venv\Scripts\Activate.ps1  # Windows PowerShell

# --no-index defends against accidental egress to PyPI; --find-links
# is the only source pip is allowed to look at.
python -m pip install \
    --no-index \
    --find-links wheelhouse \
    "mythic-vibe-cli[ai,otel,ux,tui]"
```

Verify the install:

```bash
mythic-vibe --help
mythic-vibe doctor --json
```

## Pi tier notes

The Pi Zero / Pi 5 hardware profiles (see
`docs/hardware_profiles.md`) are explicitly supported as install
targets. The wheelhouse is the recommended path on those devices
because:

- Resolving + downloading transitive deps over a Pi Zero's
  network stack can take 10x longer than copying a
  pre-built tarball off a USB drive.
- The aarch64 row in `.github/workflows/ci.yml` exercises the
  same install path the wheelhouse uses, so we have CI evidence
  the wheelhouse works on aarch64.

The wheelhouse contains pure-Python wheels for everything in the
`[ai,otel,ux,tui]` extras (no native compilation needed), which
is why the install path works without a build toolchain on the
target.

## Reproducibility

The wheelhouse is built inside `release.yml` with `pip wheel`
against a freshly-built sdist from the same release commit. The
release artifact's SHA256 is reproducible bit-for-bit between
two runs of the workflow on the same tag (provided no upstream
dependency yanked or re-uploaded a wheel between runs).
