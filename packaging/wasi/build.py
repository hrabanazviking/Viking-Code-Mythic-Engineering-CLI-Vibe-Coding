"""WASI build driver for mythic-vibe-cli.

Cross-compiles CPython for the ``wasm32-wasi`` target and emits
a single ``.wasm`` artifact runnable under any WASI host
(Wasmtime, wasmer, Node-with-WASI shim).

History:
    PH-22.3 (2026-05-05) — foundation level: contract + workflow
        scaffolding; ``--really-build`` was a guarded TODO.
    PH-23.7 (2026-05-05) — real cross-build wired up: wasi-sdk
        download + CPython source resolution + the four
        ``./Tools/wasm/wasi.py`` orchestrator steps now run when
        ``--really-build`` is passed.

The real build still has caveats:

- Subprocess-based CLI commands (git checks in `doctor`, plugin
  sandbox in `verify`) won't work in WASI. The supported v2.0
  scope is read-only JSON-emitting commands. See
  ``packaging/wasi/README.md`` for the full compatibility matrix.
- Most C extensions don't WASI-compile. The base CLI is
  stdlib-only, so this is acceptable; operators needing extras
  (anthropic, openai, textual, rich) stay with the pip channels.

Usage:

    # Foundation placeholder (no wasi-sdk needed):
    python packaging/wasi/build.py --output dist/mythic-vibe.wasm

    # Real cross-build (requires ~1-2 GB disk + ~10-20 min):
    python packaging/wasi/build.py --output dist/mythic-vibe.wasm \\
        --really-build

The cross-build caches wasi-sdk + the CPython source under
``~/.cache/mythic-vibe-wasi-build/`` so a subsequent
``--really-build`` only re-runs the make step.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Sequence


# Pinned CPython version. Matches the launcher's pin
# (PYTHON_VERSION in packaging/launcher/src/main.rs) so the WASI
# runtime's Python matches the launcher-installed venv's Python.
CPYTHON_VERSION = "3.12.7"

# Pinned wasi-sdk version. Bumping invalidates the per-CPython
# build artifact cache.
WASI_SDK_VERSION = "24"

# Sub-revision of the wasi-sdk release. Upstream tags releases
# as wasi-sdk-{MAJOR}.{MINOR} — at the time of writing the 24.x
# line is current. Sub-bumps are tracked here so the future
# session updates one constant when bumping.
WASI_SDK_RELEASE = "wasi-sdk-24.0"

# Cache root the build driver creates under the user's cache dir.
CACHE_SUBDIR = "mythic-vibe-wasi-build"

# CPython source archive — fetched as a tarball from python.org
# rather than git-cloned, to avoid pulling the full git history.
CPYTHON_SOURCE_URL_TEMPLATE = (
    "https://www.python.org/ftp/python/{version}/Python-{version}.tar.xz"
)

# wasi-sdk download URL pattern. Per-OS asset names follow the
# pattern wasi-sdk-{tag}-{os}.tar.gz on the upstream releases page.
WASI_SDK_URL_TEMPLATE = (
    "https://github.com/WebAssembly/wasi-sdk/releases/download/"
    "{release}/{release}-{os_suffix}.tar.gz"
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build mythic-vibe-cli for WASI (PH-22.3 foundation + "
            "PH-23.7 real cross-build)"
        ),
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
            "Run the actual CPython WASI cross-build (downloads "
            "wasi-sdk + CPython source on first run; ~1-2 GB disk "
            "and ~10-20 minutes per fresh build). Without this "
            "flag, emits a placeholder marker file."
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
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help=(
            "Override the per-user build cache "
            "(default: ~/.cache/mythic-vibe-wasi-build/)"
        ),
    )
    parser.add_argument(
        "--build-zipapp",
        action="store_true",
        default=True,
        help=(
            "Also build a zipapp sidecar (mythic-vibe.pyz) "
            "alongside the .wasm, so WASI hosts can run "
            "`wasmtime --dir=. mythic-vibe.wasm -- "
            "mythic-vibe.pyz doctor --json`. ON by default; "
            "use --no-build-zipapp to skip (placeholder builds "
            "skip automatically)."
        ),
    )
    parser.add_argument(
        "--no-build-zipapp",
        dest="build_zipapp",
        action="store_false",
        help="Skip the zipapp sidecar build.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent.parent
    if not (repo_root / "pyproject.toml").is_file():
        print(
            f"ERROR: pyproject.toml missing at {repo_root}; run from repo root",
            file=sys.stderr,
        )
        return 2

    print("WASI build target:")
    print(f"  CPython:  {args.cpython_version}")
    print(f"  wasi-sdk: {args.wasi_sdk_version} ({WASI_SDK_RELEASE})")
    print(f"  output:   {args.output}")
    if args.build_zipapp:
        print(f"  zipapp:   {args.output.with_suffix('.pyz')}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    if not args.really_build:
        return _emit_foundation_placeholder(args.output)

    rc = _run_full_wasi_build(repo_root, args)
    if rc != 0:
        return rc

    # PH-23.11 — build the zipapp sidecar after the .wasm is in
    # place. The sidecar is a .pyz containing mythic_vibe_cli/
    # source that a WASI runtime can execute directly via the
    # python.wasm. Building it last means a failed wasm build
    # short-circuits before we waste time on the zipapp.
    if args.build_zipapp:
        try:
            _build_zipapp_sidecar(repo_root, args.output)
        except BuildStepFailed as exc:
            print(f"FATAL: zipapp build failed: {exc}", file=sys.stderr)
            return 14

    return 0


# ---- Foundation placeholder path -----------------------------------


def _emit_foundation_placeholder(output: Path) -> int:
    """Write a non-executable placeholder marker file.

    Used by the workflow's tag-rehearsal path when the operator
    hasn't opted into ``--really-build``. The file is
    deliberately NOT a valid .wasm so any host that tries to
    execute it fails loudly with a clear "magic bytes wrong"
    error rather than running the placeholder as if it were a
    real artifact.
    """
    output.write_bytes(
        b"# mythic-vibe-cli WASI placeholder (PH-22.3 foundation)\n"
        b"# This file is NOT a valid .wasm. Pass --really-build to\n"
        b"# build the real artifact (PH-23.7 wires up the cross-\n"
        b"# build; requires wasi-sdk + CPython source download).\n"
    )
    print(f"\nfoundation-placeholder: wrote marker at {output}")
    print("Pass --really-build to produce a real .wasm artifact.")
    return 0


# ---- Real cross-build path -----------------------------------------


def _run_full_wasi_build(
    repo_root: Path, args: argparse.Namespace,
) -> int:
    """Orchestrate the real CPython WASI cross-build.

    Pipeline (each step bails out on its own error):

    1. Resolve the build cache directory.
    2. Ensure wasi-sdk is unpacked into the cache.
    3. Ensure CPython source is unpacked into the cache.
    4. Run ``./Tools/wasm/wasi.py configure-build-python`` to
       build the host CPython needed for cross-bootstrap.
    5. Run ``./Tools/wasm/wasi.py make-build-python``.
    6. Run ``./Tools/wasm/wasi.py configure-host`` to configure
       the WASI cross-target.
    7. Run ``./Tools/wasm/wasi.py make-host``.
    8. Copy the resulting ``cross-build/wasi/python.wasm`` to
       ``args.output``.

    Returns 0 on success, non-zero exit code on any step
    failure. A failed make step surfaces with a clear "step N
    failed" message + the underlying tool's exit code so
    operators can see where in the pipeline the failure
    happened.
    """
    cache_dir = _resolve_cache_dir(args.cache_dir)
    print(f"  cache:    {cache_dir}")

    # Step 2: wasi-sdk
    print("\n[wasi] step 1/7: ensure wasi-sdk available")
    try:
        wasi_sdk_root = _ensure_wasi_sdk(
            cache_dir, args.wasi_sdk_version,
        )
    except BuildStepFailed as exc:
        print(f"FATAL: wasi-sdk install failed: {exc}", file=sys.stderr)
        return 10
    print(f"  wasi-sdk root: {wasi_sdk_root}")

    # Step 3: CPython source
    print("\n[wasi] step 2/7: ensure CPython source available")
    try:
        cpython_dir = _ensure_cpython_source(
            cache_dir, args.cpython_version,
        )
    except BuildStepFailed as exc:
        print(f"FATAL: CPython source resolution failed: {exc}", file=sys.stderr)
        return 11
    print(f"  cpython source: {cpython_dir}")

    # Steps 4-7: the wasi.py orchestrator (four invocations)
    print("\n[wasi] steps 3-6/7: CPython WASI cross-build via Tools/wasm/wasi.py")
    rc = _run_wasi_orchestrator(cpython_dir, wasi_sdk_root)
    if rc != 0:
        print(f"FATAL: wasi.py orchestrator exited with code {rc}", file=sys.stderr)
        return 12

    # Step 8: copy the produced artifact to args.output
    print("\n[wasi] step 7/7: copy artifact to output path")
    produced = cpython_dir / "cross-build" / "wasi" / "python.wasm"
    if not produced.is_file():
        print(
            f"FATAL: expected artifact missing at {produced}",
            file=sys.stderr,
        )
        return 13
    args.output.write_bytes(produced.read_bytes())
    size_mb = args.output.stat().st_size / 1024 / 1024
    print(f"  wrote {args.output} ({size_mb:.1f} MB)")

    print("\n[wasi] cross-build complete")
    return 0


def _resolve_cache_dir(override: Path | None) -> Path:
    """Pick the per-user cache root for the WASI build."""
    if override is not None:
        override.mkdir(parents=True, exist_ok=True)
        return override
    base_str = (
        os.environ.get("XDG_CACHE_HOME")
        or os.environ.get("MYTHIC_WASI_CACHE")
        or str(Path.home() / ".cache")
    )
    base = Path(base_str) / CACHE_SUBDIR
    base.mkdir(parents=True, exist_ok=True)
    return base


def _ensure_wasi_sdk(cache_dir: Path, version: str) -> Path:
    """Download + unpack wasi-sdk into ``cache_dir`` if missing.

    Returns the unpacked SDK root (the directory containing
    ``bin/clang``, ``share/wasi-sysroot``, etc.).

    The cache layout is::

        <cache_dir>/wasi-sdk-{version}/        # unpacked tree
        <cache_dir>/wasi-sdk-{version}.tar.gz  # downloaded archive

    Idempotent: if the unpacked tree already exists, returns
    immediately without re-downloading.
    """
    sdk_root = cache_dir / WASI_SDK_RELEASE
    if (sdk_root / "bin").is_dir():
        return sdk_root

    os_suffix = _wasi_sdk_os_suffix()
    url = WASI_SDK_URL_TEMPLATE.format(
        release=WASI_SDK_RELEASE, os_suffix=os_suffix,
    )
    archive = cache_dir / f"{WASI_SDK_RELEASE}-{os_suffix}.tar.gz"

    if not archive.is_file():
        print(f"  fetching {url}")
        try:
            urllib.request.urlretrieve(url, archive)
        except urllib.error.URLError as exc:
            raise BuildStepFailed(
                f"download {url} failed: {exc}"
            ) from exc

    print(f"  extracting {archive}")
    rc = shell(
        ["tar", "-xzf", str(archive)],
        cwd=cache_dir,
    )
    if rc != 0:
        raise BuildStepFailed(f"tar -xzf {archive} exited {rc}")

    if not (sdk_root / "bin").is_dir():
        raise BuildStepFailed(
            f"wasi-sdk unpack succeeded but {sdk_root}/bin is missing"
        )
    return sdk_root


def _wasi_sdk_os_suffix() -> str:
    """Return the OS-suffix string the wasi-sdk releases use.

    Upstream publishes per-host-OS builds; we pick the right
    asset based on the runner's OS. Note that wasi-sdk only
    publishes Linux + macOS host builds today — the Windows
    cross-build is unsupported upstream, so the workflow only
    runs the WASI build on Linux runners.
    """
    if sys.platform.startswith("linux"):
        return "x86_64-linux"
    if sys.platform == "darwin":
        return "x86_64-macos"
    raise BuildStepFailed(
        f"wasi-sdk has no upstream build for sys.platform={sys.platform!r}; "
        "run the cross-build on a Linux or macOS host"
    )


def _ensure_cpython_source(cache_dir: Path, version: str) -> Path:
    """Download + unpack CPython source into ``cache_dir``.

    Returns the unpacked source tree (the directory containing
    ``Tools/wasm/wasi.py``, ``configure``, etc.).

    Cache layout mirrors :func:`_ensure_wasi_sdk`. Idempotent.
    """
    source_dir = cache_dir / f"Python-{version}"
    if (source_dir / "Tools" / "wasm" / "wasi.py").is_file():
        return source_dir

    url = CPYTHON_SOURCE_URL_TEMPLATE.format(version=version)
    archive = cache_dir / f"Python-{version}.tar.xz"

    if not archive.is_file():
        print(f"  fetching {url}")
        try:
            urllib.request.urlretrieve(url, archive)
        except urllib.error.URLError as exc:
            raise BuildStepFailed(
                f"download {url} failed: {exc}"
            ) from exc

    print(f"  extracting {archive}")
    rc = shell(["tar", "-xJf", str(archive)], cwd=cache_dir)
    if rc != 0:
        raise BuildStepFailed(f"tar -xJf {archive} exited {rc}")

    if not (source_dir / "Tools" / "wasm" / "wasi.py").is_file():
        raise BuildStepFailed(
            f"CPython unpack succeeded but {source_dir}/Tools/wasm/wasi.py "
            "is missing"
        )
    return source_dir


def _run_wasi_orchestrator(
    cpython_dir: Path, wasi_sdk_root: Path,
) -> int:
    """Run the four ``./Tools/wasm/wasi.py`` orchestrator steps
    in the CPython source dir.

    Each step is a separate ``python Tools/wasm/wasi.py <step>``
    subprocess. The four steps:

    1. ``configure-build-python`` — configures the host CPython
       used to bootstrap the cross-build.
    2. ``make-build-python`` — builds the host CPython.
    3. ``configure-host`` — configures the WASI cross-target
       (sets WASI_SDK_PATH + the cross-compile flags).
    4. ``make-host`` — runs the cross-make. Output is written
       to ``cross-build/wasi/`` under the source dir.

    The ``WASI_SDK_PATH`` env var is set before invoking; the
    wasi.py script reads it to locate the cross-compile
    toolchain.

    Returns the first non-zero exit code, or 0 on full success.
    """
    env = os.environ.copy()
    env["WASI_SDK_PATH"] = str(wasi_sdk_root)
    env["CPATH"] = (
        f"{wasi_sdk_root}/share/wasi-sysroot/include"
        + (":" + env["CPATH"] if "CPATH" in env else "")
    )

    steps = [
        "configure-build-python",
        "make-build-python",
        "configure-host",
        "make-host",
    ]
    for idx, step in enumerate(steps, start=1):
        print(f"\n  [orchestrator {idx}/{len(steps)}] {step}")
        rc = shell(
            [sys.executable, "Tools/wasm/wasi.py", step],
            cwd=cpython_dir,
            env=env,
        )
        if rc != 0:
            print(
                f"  step {step} exited with code {rc}", file=sys.stderr,
            )
            return rc
    return 0


# ---- Zipapp sidecar (PH-23.11) ------------------------------------


def _build_zipapp_sidecar(repo_root: Path, wasm_output: Path) -> None:
    """Build a ``.pyz`` zipapp containing the mythic_vibe_cli
    source tree, written next to ``wasm_output`` with the same
    basename + ``.pyz`` extension.

    The zipapp can be executed by the WASI-built CPython via:

        wasmtime --dir=. mythic-vibe.wasm -- mythic-vibe.pyz doctor --json

    We use stdlib ``zipapp.create_archive`` rather than calling
    ``pip install --target`` because the pip path drags in
    pip + setuptools metadata files we don't need; the source-
    tree-only zipapp is ~50-150 KB vs ~1-2 MB for the full
    pip-installed tree.

    Limitations (consistent with the v2.0 reduced-scope
    contract documented in packaging/wasi/README.md):

    - Only the stdlib-only base ships in the zipapp. Optional
      extras (anthropic / openai / textual / rich / opentelemetry)
      are NOT bundled — they wouldn't WASI-compile anyway.
    - subprocess-based commands (git checks in doctor, plugin
      sandbox in verify) are still broken under WASI; the
      zipapp doesn't fix that.

    Raises :class:`BuildStepFailed` if the zipapp build fails;
    the driver maps to exit code 14 so the workflow log shows
    the source of the failure.
    """
    import zipapp

    package_root = repo_root / "mythic_vibe_cli"
    if not package_root.is_dir():
        raise BuildStepFailed(
            f"package source missing at {package_root}; cannot build zipapp"
        )

    # The zipapp's "main" needs to invoke mythic_vibe_cli.cli.main
    # so command-line invocations behave the same as the pip path.
    main_target = "mythic_vibe_cli.cli:main"

    # zipapp.create_archive's source arg expects a directory
    # *containing* the package, not the package itself. We stage
    # the package into a temp dir so the .pyz packs
    # mythic_vibe_cli/<files...> as the top-level layout the
    # interpreter will import from.
    import shutil
    import tempfile

    sidecar_path = wasm_output.with_suffix(".pyz")
    print(f"  building zipapp sidecar at {sidecar_path}")

    with tempfile.TemporaryDirectory() as staging_root:
        staging = Path(staging_root)
        # Mirror the package tree, excluding test artifacts +
        # bytecode caches that bloat the zipapp without adding
        # functionality.
        shutil.copytree(
            package_root,
            staging / "mythic_vibe_cli",
            ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.pyo",
            ),
        )
        try:
            zipapp.create_archive(
                staging,
                target=str(sidecar_path),
                main=main_target,
                # Compress the zipapp — typical 5-10x size win
                # at negligible startup cost in CPython's
                # zipimport.
                compressed=True,
            )
        except Exception as exc:  # noqa: BLE001 — surface as BuildStepFailed
            raise BuildStepFailed(
                f"zipapp.create_archive failed: {exc}"
            ) from exc

    if not sidecar_path.is_file():
        raise BuildStepFailed(
            f"zipapp build reported success but {sidecar_path} is missing"
        )

    size_kb = sidecar_path.stat().st_size / 1024
    print(f"  wrote {sidecar_path} ({size_kb:.1f} KB)")


# ---- Helpers ------------------------------------------------------


class BuildStepFailed(RuntimeError):
    """Raised by the ensure-* helpers when a setup step fails.
    The driver catches it + maps to a per-step exit code so the
    workflow log shows exactly where in the pipeline the
    failure happened."""


def shell(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> int:
    """Run a subprocess with the given args + cwd + env. Returns
    the exit code. Logs the invocation to stdout so the
    workflow log shows the full command sequence."""
    print(f"+ {' '.join(cmd)}")
    return subprocess.run(
        cmd, cwd=cwd, env=env, check=False,
    ).returncode


__all__ = [
    "BuildStepFailed",
    "CACHE_SUBDIR",
    "CPYTHON_SOURCE_URL_TEMPLATE",
    "CPYTHON_VERSION",
    "WASI_SDK_RELEASE",
    "WASI_SDK_URL_TEMPLATE",
    "WASI_SDK_VERSION",
    "main",
    "shell",
]


if __name__ == "__main__":
    sys.exit(main())
