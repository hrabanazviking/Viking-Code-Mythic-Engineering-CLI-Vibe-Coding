"""Regenerate ``docs/security/sbom.json`` (Phase 19.5, audit
remediation 2026-05-02).

Builds a CycloneDX v1.6 SBOM from a freshly-isolated virtualenv
that contains only the project plus the runtime-relevant extras
(``ai``, ``otel``, ``ux``, ``tui``). This avoids polluting the
SBOM with unrelated dev-environment packages.

Usage::

    python scripts/regenerate_sbom.py

The release workflow (PH-19.7) calls this after building the
wheel so the SBOM committed to ``docs/security/`` always
reflects the published artifact.

Cross-platform: pure stdlib for the orchestration; relies on
``cyclonedx-bom`` (installed into the temporary venv).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from mythic_vibe_cli.runtime.script_guard import guarded_main

DEFAULT_OUTPUT = REPO_ROOT / "docs" / "security" / "sbom.json"
EXTRAS = "ai,otel,ux,tui"


def _venv_python(venv_root: Path) -> Path:
    """Return the python executable inside a freshly-created
    venv, accounting for POSIX vs Windows layout."""
    if os.name == "nt":
        return venv_root / "Scripts" / "python.exe"
    return venv_root / "bin" / "python"


def _run(cmd: list[str | Path], **kwargs: object) -> None:
    """Echo + run with check=True. Streams output so a failed
    pip install isn't a silent black-box."""
    printable = " ".join(str(part) for part in cmd)
    print(f"+ {printable}", flush=True)
    subprocess.run([str(part) for part in cmd], check=True, **kwargs)  # type: ignore[arg-type]


def regenerate(output_path: Path = DEFAULT_OUTPUT) -> Path:
    """Build a clean venv, install project + extras + cyclonedx,
    and emit the SBOM to ``output_path``. Returns the path
    written. Raises ``subprocess.CalledProcessError`` on any
    upstream failure."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mvcli-sbom-") as tmp:
        venv_root = Path(tmp) / "venv"
        _run([sys.executable, "-m", "venv", str(venv_root)])
        py = _venv_python(venv_root)
        _run([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
        _run([
            py, "-m", "pip", "install", "--quiet",
            f".[{EXTRAS}]", "cyclonedx-bom",
        ])
        _run([
            py, "-m", "cyclonedx_py", "environment",
            "--pyproject", str(REPO_ROOT / "pyproject.toml"),
            "--output-reproducible",
            "--of", "JSON",
            "-o", str(output_path),
        ])
    return output_path


def _summarise(path: Path) -> None:
    """Print a short component-count summary so CI logs / local
    runs can spot wildly-wrong outputs at a glance."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    components = payload.get("components", [])
    print(
        f"SBOM written: {path} "
        f"(format={payload.get('bomFormat')} "
        f"spec={payload.get('specVersion')} "
        f"components={len(components)})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate the project SBOM from a clean venv.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where to write the SBOM (default: docs/security/sbom.json).",
    )
    args = parser.parse_args(argv)
    if shutil.which(sys.executable) is None:
        print(f"python interpreter not found: {sys.executable}", file=sys.stderr)
        return 2
    regenerate(args.output)
    _summarise(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(
        guarded_main(
            lambda: main(),
            script_name=Path(__file__).name,
            json_mode="--json" in sys.argv,
        )
    )
