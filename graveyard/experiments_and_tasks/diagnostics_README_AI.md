# diagnostics.py — README_AI.md

> **Scope note (v1.0.0 / 2026-05-03).** This file (and the eleven sibling
> `diagnostics_*.md` files at the repo root) document a `diagnostics.py`
> module that is **NOT part of the active Mythic Vibe CLI v1.0.0
> product** (`mythic_vibe_cli/` does not contain a `diagnostics.py`).
> These are auto-generated documentation templates from a different
> project surveyed during research, kept here as reference patterns.
>
> The Mythic Vibe CLI's diagnostic surface is `mythic-vibe doctor`
> (with the v1.0 `--fix` and `--fix-dry-run` flags) and `mythic-vibe
> drift` (with the v1.0 `dashboard` subcommand). For their actual
> behavior see [`docs/api.md`](docs/api.md) and
> [`docs/COMMAND_CONTRACTS.md`](docs/COMMAND_CONTRACTS.md).
>
> See [`ROOT_DOC_INDEX.md`](ROOT_DOC_INDEX.md) Tier 5 for the broader
> root-level auxiliary-content classification.

## Purpose
Diagnostic System v3.0 - Debug and Troubleshooting Tools
=========================================================

Run this to check system health, find issues, and generate debug reports.
Usage: python diagnostics.py [--full] [--fix]

## Technical Architecture
- **Classes**: 1 main classes
  - `DiagnosticSystem`: Comprehensive diagnostic and troubleshooting tools.
- **Functions**: 1 module-level functions

## Key Components
### `DiagnosticSystem`
Comprehensive diagnostic and troubleshooting tools.
**Methods**: __init__, run_all_checks, check_python, check_dependencies, check_config

## Dependencies
```
import sys
import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any
```

---
**Last Updated**: February 18, 2026 | v8.0.0
