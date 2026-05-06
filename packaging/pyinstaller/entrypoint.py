"""PyInstaller entrypoint shim (PH-21.2).

PyInstaller's spec needs an importable script as the analysis root.
The CLI's installed ``mythic-vibe`` console-script entry point goes
through ``mythic_vibe_cli.cli:main``; this shim forwards to the same
function so the standalone binary behaves identically to a
``pip install``-ed CLI.

Kept tiny on purpose: any logic added here would diverge from the
pip path and make the standalone binary subtly different. The
shim's only responsibility is to invoke main() and propagate its
exit code through ``sys.exit``.
"""

from __future__ import annotations

import sys

from mythic_vibe_cli.cli import main


if __name__ == "__main__":
    sys.exit(main())
