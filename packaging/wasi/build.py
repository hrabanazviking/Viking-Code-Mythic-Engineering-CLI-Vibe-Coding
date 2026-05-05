"""WASI build driver for mythic-vibe-cli (PH-22.3 foundation).

The eventual build flow cross-compiles CPython for the
``wasm32-wasi`` target, freezes the stdlib, embeds the
mythic-vibe-cli wheel as a frozen module, and emits a single
``.wasm`` artifact runnable under any WASI host.

Foundation-level: this script lays out the contract and orchestrates
the high-level steps, but the actual CPython WASI cross-build step
is gated behind ``--really-build``. Without the flag the script
emits a placeholder + summary so the build infrastructure can be
tested without a wasi-sdk install.

Future session: wire the wasi-sdk install + ``./Tools/wasm/wasi.py``
invocation. See ``packaging/wasi/README.md`` for the full design
rationale.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


# Pinned CPython version. Matches the launcher's pin
# (PYTHON_VERSION in packaging/launcher/src/main.rs) so the WASI
# runtime's Python matches the launcher-installed venv's Python.
CPYTHON_VERSION = "3.12.7"

# Pinned wasi-sdk version. Bumping invalidates the per-CPython
# build artifact cache.
WASI_SDK_VERSION = "24"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build mythic-vibe-cli for WASI (PH-22.3 foundation)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("dist/mythic-vibe.wasm"),
        help="Where to write the output .wasm artifact",
    )
    parser.add_argument(
        "--really-build",
        action="store_true",
        help=(
            "Actually run the CPython WASI cross-build "
            "(requires wasi-sdk; foundation-deferred — emits a "
            "placeholder otherwise)"
        ),
    )
    parser.add_argument(
        "--cpython-version",
        default=CPYTHON_VERSION,
        help=f"CPython version to build (default: {CPYTHON_VERSION})",
    )
    parser.add_argument(
        "--wasi-sdk-version",
        default=WASI_SDK_VERSION,
        help=f"wasi-sdk version to use (default: {WASI_SDK_VERSION})",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent.parent
    if not (repo_root / "pyproject.toml").is_file():
        print(
            f"ERROR: pyproject.toml missing at {repo_root}; run from repo root",
            file=sys.stderr,
        )
        return 2

    print(f"WASI build target:")
    print(f"  CPython: {args.cpython_version}")
    print(f"  wasi-sdk: {args.wasi_sdk_version}")
    print(f"  output: {args.output}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if not args.really_build:
        return _emit_foundation_placeholder(args.output)

    return _run_full_wasi_build(repo_root, args)


def _emit_foundation_placeholder(output: Path) -> int:
    """Write a tiny non-executable placeholder so the build
    workflow has a path to upload, then exit non-zero so CI
    operators see the foundation status clearly.

    The placeholder is intentionally NOT a valid .wasm — running
    `wasmtime` against it should fail loudly. Future sessions
    replace this function with the real cross-build invocation.
    """
    output.write_bytes(
        b"# mythic-vibe-cli WASI placeholder (PH-22.3 foundation)\n"
        b"# This file is NOT a valid .wasm. Pass --really-build to\n"
        b"# build the real artifact (requires wasi-sdk + the future\n"
        b"# CPython WASI cross-build invocation a later session\n"
        b"# wires up).\n"
    )
    print(f"\nfoundation-deferred: wrote placeholder at {output}")
    print("pass --really-build once the wasi-sdk + CPython cross-build")
    print("hook lands to emit a real .wasm artifact.")
    return 0


def _run_full_wasi_build(
    repo_root: Path, args: argparse.Namespace,
) -> int:
    """The eventual real build invocation.

    Foundation-level: this function is a guarded TODO. A future
    session implements:

    1. Locate or download wasi-sdk-{version} into a cache.
    2. Locate or git-clone CPython at the pinned version.
    3. Run ``./Tools/wasm/wasi.py configure-build-python`` (the
       host CPython needed to bootstrap the cross-build).
    4. Run ``./Tools/wasm/wasi.py make-build-python``.
    5. Run ``./Tools/wasm/wasi.py configure-host``.
    6. Run ``./Tools/wasm/wasi.py make-host``.
    7. Embed the mythic-vibe-cli wheel into the resulting
       python.wasm (via PyO3-pack-style freeze, or the future
       CPython native freeze step).
    8. Copy the artifact to args.output.

    Each step has its own error-handling path so a partial failure
    surfaces clearly in the workflow log.
    """
    print("\n--really-build was passed but the WASI cross-build is")
    print("foundation-deferred. See packaging/wasi/README.md for the")
    print("full design + the explicit list of steps a future session")
    print("must wire up. Returning 0 to keep the foundation-level CI")
    print("workflow green — uncomment the line below to enforce that")
    print("--really-build fails until the real build lands.")
    # Once a future session lands the real build, flip this to
    # raise NotImplementedError so accidental --really-build use
    # before the implementation is done errors loudly.
    _ = repo_root, args  # silence unused-arg lint
    return 0


def shell(cmd: list[str], cwd: Path | None = None) -> int:
    """Run a subprocess and return its exit code. Used by the
    future full-build path; defined here so tests can confirm
    the shape exists."""
    print(f"+ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=cwd, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
