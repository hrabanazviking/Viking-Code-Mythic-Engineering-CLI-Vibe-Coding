#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "==> Norse Saga Engine: Installing dependencies..."

# Install core project dependencies
pip install -r "$CLAUDE_PROJECT_DIR/requirements.txt" --quiet

# Install dev tools (pytest, black, flake8)
pip install pytest black flake8 --quiet

echo "==> Norse Saga Engine: Dependencies installed successfully."
