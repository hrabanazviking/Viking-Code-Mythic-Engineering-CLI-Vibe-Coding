# mythic-vibe-launcher

PH-22.1 — static native launcher for `mythic-vibe-cli` that requires no Python pre-installed on the host.

## What it is

A small (~3-5 MB) Rust binary that:

1. **First run:** downloads [python-build-standalone](https://github.com/indygreg/python-build-standalone) into a per-user cache (~30 MB), creates a venv, installs `mythic-vibe-cli` from PyPI, then execs the CLI.
2. **Subsequent runs:** short-circuits to the cached venv and execs the CLI directly (~50 ms overhead vs invoking the cached `mythic-vibe` binary directly).

Operators get a single static binary for environments where `pip install` isn't an option (sandboxed boxes, locked-down workstations, kiosks). Compared to the PyInstaller / Nuitka binaries from PH-21.2 / PH-21.3:

| Property | PyInstaller / Nuitka | Launcher (PH-22.1) |
|---|---|---|
| Binary size | ~15-25 MB / ~8-15 MB | ~3-5 MB |
| First-run cold start | ~250-500 ms / ~80-150 ms | ~30-60 s (interpreter download) |
| Subsequent cold start | ~250-500 ms / ~80-150 ms | ~150-250 ms |
| Optional extras (`ai`, `tui`, `ux`, `otel`) | ❌ stdlib-only | ✅ pip-installable into the cached venv |
| Network required for first run | ❌ | ✅ |

The launcher's strength is **flexibility**: operators can `pip install mythic-vibe-cli[ai]` into the cached venv to add extras. The PyInstaller / Nuitka binaries embed only the stdlib base.

## Cache layout

```
<cache_root>/
├── py-3.12.7/                # python-build-standalone interpreter
│   └── python/
│       └── bin/python3       # the cached interpreter
└── venv/                     # operator-extensible venv
    └── bin/mythic-vibe       # the actual CLI entry point
```

`<cache_root>` is platform-default per `dirs::cache_dir()`:

- **Linux:** `~/.cache/mythic-vibe-launcher/`
- **macOS:** `~/Library/Caches/mythic-vibe-launcher/`
- **Windows:** `%LOCALAPPDATA%\mythic-vibe-launcher\Cache\`

Operators can redirect via the `MYTHIC_LAUNCHER_CACHE` env var (useful for CI runners that want a workspace-local cache, or sandboxed environments where the platform cache dir isn't writable).

## Building locally

```bash
# Inside packaging/launcher/:
cargo build --release

# The binary lands at:
ls target/release/mythic-vibe-launcher

# Run it:
./target/release/mythic-vibe-launcher --version
```

The CI workflow (`.github/workflows/release-launcher.yml`) builds per OS matrix on tag push and attaches the binaries to the GitHub Release.

## Adding an extra to the cached venv

```bash
# Find the cached venv:
LAUNCHER_VENV="$(dirs --cache 2>/dev/null || echo ~/.cache)/mythic-vibe-launcher/venv"

# Activate it and install:
"$LAUNCHER_VENV/bin/pip" install "mythic-vibe-cli[ai,tui]"
```

The extras land in the same venv the launcher execs against, so they're available next run.

## Foundation-level scope (PH-22.1, this commit)

What works today:

- ✅ Crate compiles on Rust 1.74+ (the rust-version pin in Cargo.toml).
- ✅ Lifecycle stages (resolve cache → ensure interpreter → ensure venv → exec) are split into named functions for testability.
- ✅ Per-arch `python-build-standalone` URL resolution covers x86_64 + aarch64 on Linux + macOS, plus x86_64 on Windows.
- ✅ `MYTHIC_LAUNCHER_CACHE` env override.
- ✅ tar.gz + tar.zst archive extraction.
- ✅ Unix `execv` so signals + ttys + exit codes pass through cleanly.

What was shipped after the foundation level:

- ✅ **SHA256 verification of downloaded archives** (PH-23.4, 2026-05-05). The `verify_archive_sha256` function in `src/main.rs` hashes the downloaded archive bytes and compares against the per-arch table at `PBS_EXPECTED_SHA256`. Three branches: matching expected SHA → ok; mismatch → hard error; no expected SHA in table → log a warning + continue (lenient default), unless `REQUIRE_VERIFIED_CHECKSUMS = true` or `MYTHIC_LAUNCHER_REQUIRE_SHA=1` flips strict mode. The table starts with `None` for every arch — populate it by running `python tools/fetch_pbs_checksums.py` and pasting the rendered table into `src/main.rs`. Each PBS release tag bump invalidates the table; re-run the script.

What's deferred to a future session:

- ⚠️ **Populate the `PBS_EXPECTED_SHA256` table with real SHA values** (~5 min, requires network reach). The verification path exists; the SHAs are the missing piece. Run `python tools/fetch_pbs_checksums.py` and paste the output. Once every arch has a real SHA, flip `REQUIRE_VERIFIED_CHECKSUMS` to `true` so a missing row is a hard error instead of a warning.
- ⚠️ **First-run UX polish.** Today the launcher prints status to stderr; a future session adds progress bars (indicatif crate), retries with backoff, and mirror-fallback when the GitHub release host is rate-limiting.
- ⚠️ **Wheel version pinning.** Today `pip install mythic-vibe-cli` resolves the latest version on PyPI. A future session adds `--upgrade-strategy only-if-needed` defaulting + `MYTHIC_LAUNCHER_CLI_VERSION` env override for operators who want a pinned version.
- ⚠️ **Sigstore verification of the downloaded wheel.** PH-21.5 publishes Sigstore signatures for every PyPI artifact; the launcher could verify them at install time. Adds the sigstore-rs dep + ~50 lines of verification code.
- ⚠️ **Offline cache pre-population.** A `mythic-vibe-launcher --pre-populate` flag that downloads the interpreter + wheel without execing the CLI. Lets ops bake a cache into a base image.

## Why Rust over Go?

Both can produce static binaries with embedded HTTP + archive extraction. Rust was chosen because:

1. **Smaller binaries.** Rust's `opt-level = "z" + lto + strip + panic=abort` produces ~3 MB binaries; equivalent Go is ~7-9 MB after `-ldflags="-s -w"`.
2. **Cargo's dependency hygiene.** Pinned `Cargo.lock` + the `cargo audit` ecosystem give us a clean supply-chain story.
3. **`execv` first-class.** Unix exec semantics work cleanly through `std::os::unix::process::CommandExt::exec`. Go's `syscall.Exec` works but feels less idiomatic.
4. **Sigstore-rs.** Future Sigstore verification has a mature Rust client (`sigstore` crate) — Go has cosign but it's cli-shaped, not lib-shaped.

## Why a launcher at all when we have PyInstaller + Nuitka?

The PyInstaller + Nuitka binaries (PH-21.2 + PH-21.3) embed the stdlib-only base — operators who need `[ai]` or `[tui]` extras can't use them. The launcher fills that gap by giving operators a static binary today + the ability to extend it via pip into the cached venv tomorrow.

Three operator profiles:

- **Sandboxed-but-online operator (the launcher's sweet spot).** Network is available, no Python pre-installed, may or may not need extras later.
- **Air-gapped operator.** No network. Use the offline wheelhouse path documented in `docs/INSTALL.md` instead.
- **Container-friendly operator.** Use the OCI image (PH-21.1) instead — same outcome, no host filesystem cache.

The launcher is one of three strategies, not a replacement for the others.
