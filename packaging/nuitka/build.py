"""Nuitka build driver for mythic-vibe-cli (PH-21.3).

Nuitka compiles Python to C and links a real native executable.
Compared to PyInstaller's bundle-the-interpreter approach, Nuitka
produces:

- **Smaller** binaries (~8-15 MB vs PyInstaller's ~15-25 MB).
- **Faster** startup (~80-150 ms vs PyInstaller's ~250-500 ms).
- **Slower** to build (~3-8 minutes vs PyInstaller's ~30-90 s).

Operators get both options on the GitHub Release page; pick by
preference. The Nuitka asset name embeds "nuitka" so the two are
distinguishable.

Invoked by .github/workflows/release-binaries.yml in a parallel
matrix to the PyInstaller build:

    python packaging/nuitka/build.py --output-dir dist-nuitka

This wrapper exists so the flag set lives in version control as
real Python (lintable, type-checkable, testable) instead of a
brittle shell-quoted invocation in the workflow YAML. The flags
themselves are stable across operating systems — Nuitka handles
platform-specific concerns internally.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mythic_vibe_cli.runtime.script_guard import guarded_main


# Source directory for the project. The Nuitka command runs from
# the repo root so paths in --include-package + --include-data-dir
# resolve correctly.
PROJECT_PACKAGE = "mythic_vibe_cli"

# Resource directory shipped in the package. Bundled into the
# compiled binary so any future schema-loading path keeps working.
RESOURCE_PACKAGE_PATH = "mythic_vibe_cli/resources"

# Entry-point shim. Same file PyInstaller uses (PH-21.2) — keeping
# both build paths pointed at one entrypoint avoids per-builder
# behavioral drift.
ENTRYPOINT = "packaging/pyinstaller/entrypoint.py"


def build_command(
    output_dir: Path,
    *,
    binary_name: str = "mythic-vibe",
) -> list[str]:
    """Return the Nuitka command line as an argv list.

    Pulled out into a pure function so tests can assert flag
    presence without invoking Nuitka itself.
    """
    return [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        # Bundle the entire package — Nuitka's static analyzer
        # otherwise tracks only direct imports from the entrypoint.
        f"--include-package={PROJECT_PACKAGE}",
        # Bundle resources/schemas/*.json so any future schema-
        # loading path keeps working post-compile. Nuitka takes
        # source=destination pairs; the destination is relative to
        # the binary's runtime extraction dir.
        f"--include-package-data={PROJECT_PACKAGE}",
        # Output configuration.
        f"--output-dir={output_dir}",
        f"--output-filename={binary_name}",
        # Always recompile from scratch so a rebuild isn't
        # contaminated by stale cached artifacts from a prior
        # source-tree state.
        "--remove-output",
        # Show progress so the workflow log is informative when
        # builds run long.
        "--show-progress",
        # Assume Yes for any interactive prompt (e.g. dependency
        # auto-install). The CI runner has no operator at the
        # keyboard.
        "--assume-yes-for-downloads",
        # Optional extras are NOT bundled — the standalone Nuitka
        # binary matches the PyInstaller binary's stdlib-only
        # contract. Operators who need extras stick with pip.
        # nofollow-import excludes named modules from the bundle.
        "--nofollow-import-to=anthropic",
        "--nofollow-import-to=openai",
        "--nofollow-import-to=google",
        "--nofollow-import-to=textual",
        "--nofollow-import-to=rich",
        "--nofollow-import-to=opentelemetry",
        "--nofollow-import-to=hypothesis",
        "--nofollow-import-to=pytest",
        # The entrypoint shim is the same one PyInstaller uses.
        ENTRYPOINT,
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build mythic-vibe-cli with Nuitka (PH-21.3)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dist-nuitka"),
        help="Where to drop the compiled binary (default: dist-nuitka)",
    )
    parser.add_argument(
        "--binary-name",
        default="mythic-vibe",
        help="Output binary basename without extension (default: mythic-vibe)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the Nuitka command without executing it",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent.parent
    if not (repo_root / "pyproject.toml").is_file():
        print(
            f"ERROR: pyproject.toml missing at {repo_root}; run from repo root",
            file=sys.stderr,
        )
        return 2

    # Ensure Nuitka is present before kicking off a long build.
    if shutil.which("python") is None:
        print("ERROR: python not on PATH", file=sys.stderr)
        return 2

    # Wipe stale output so a partial/aborted prior build can't
    # leave a half-built binary that confuses the smoke tests.
    if args.output_dir.exists() and not args.dry_run:
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    cmd = build_command(args.output_dir, binary_name=args.binary_name)
    print("nuitka invocation:", " ".join(cmd))

    if args.dry_run:
        return 0

    # Run from the repo root so package + entrypoint paths resolve.
    result = subprocess.run(cmd, cwd=repo_root, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(
        guarded_main(
            lambda: main(),
            script_name="packaging/nuitka/build.py",
            json_mode=False,
        )
    )
