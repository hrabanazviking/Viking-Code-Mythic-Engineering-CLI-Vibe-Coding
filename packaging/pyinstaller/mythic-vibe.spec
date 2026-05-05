# PyInstaller spec for mythic-vibe-cli (PH-21.2).
# -*- mode: python ; coding: utf-8 -*-
#
# Build a standalone single-file executable from the CLI's
# stdlib-only base. Optional extras (anthropic / openai / google-
# genai / textual / rich / opentelemetry-* / hypothesis) are
# deliberately excluded — operators who need them stick with
# `pip install mythic-vibe-cli[ai,tui,...]`. The standalone binary
# is for "drop a single file on a sandboxed box and run" use cases
# where pip isn't an option.
#
# Invoked by .github/workflows/release-binaries.yml on tag push:
#
#     pyinstaller packaging/pyinstaller/mythic-vibe.spec --clean
#
# Resulting binary: dist/mythic-vibe (Linux/macOS) or
# dist/mythic-vibe.exe (Windows). Filename adjusts per OS via the
# workflow's rename step.

from PyInstaller.utils.hooks import collect_data_files


# Collect resources/schemas/*.json so any future code path that
# loads schemas via importlib.resources still works after freeze.
# collect_data_files walks the package tree and emits the (src,
# dest) tuples PyInstaller's datas parameter expects.
datas = collect_data_files(
    "mythic_vibe_cli",
    includes=["resources/schemas/*.json", "resources/**/*.json"],
)


# Hidden imports — modules PyInstaller's static analyzer might miss.
# The dispatcher / loader use importlib.import_module on operator-
# supplied plugin module names, so plugin code is never bundled
# (operators install plugins separately into their own venv against
# a pip install of mythic-vibe-cli, not against the standalone
# binary).
#
# The base CLI is stdlib-only, so the visible-import set is small.
# We list the imports that are conditionally imported inside
# functions (PyInstaller's static analyzer can miss those when the
# function isn't called at module import time).
hiddenimports = [
    # Catalog freshness check imports model_catalog at runtime.
    "mythic_vibe_cli.ai.providers.model_catalog",
    # Doctor --fix path imports doctor_fix lazily.
    "mythic_vibe_cli.doctor_fix",
    # AI route table loaded on demand in cmd_ai_route.
    "mythic_vibe_cli.ai.route",
    # Hardware detection imports psutil if installed; binary
    # ships without psutil so the ImportError path is the active
    # one. No hidden import needed for psutil.
    # tomllib is stdlib in 3.11+; tomli is the 3.10 fallback —
    # we list both so the binary works on any Python ≥3.10.
    "tomllib",
    "tomli",
]


# Modules to exclude from the binary so it stays small. Any module
# whose import would pull in a heavy optional dep is listed here;
# the runtime import paths inside mythic-vibe-cli already wrap
# these in try/except ImportError, so excluding them is safe.
excludes = [
    "anthropic",
    "openai",
    "google",          # google-genai
    "textual",         # TUI extra
    "rich",            # ux extra
    "opentelemetry",   # otel extra
    "hypothesis",      # test-only
    "pytest",          # test-only
    "pytest_cov",      # test-only
    "mypy",            # type-only
    "ruff",            # lint-only
    "tkinter",         # never used; PyInstaller bundles it by default on some platforms
    "matplotlib",      # never used
    "numpy",           # never used; some indirect imports reference it
]


a = Analysis(
    ["entrypoint.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="mythic-vibe",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # UPX compression breaks signing on macOS; skip
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,              # CLI tool — keep stdio attached
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,          # picks up the host arch from the runner
    codesign_identity=None,    # macOS signing handled separately in PH-21.5
    entitlements_file=None,
)
