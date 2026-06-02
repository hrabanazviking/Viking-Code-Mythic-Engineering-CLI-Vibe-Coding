#!/bin/sh
# Mythic Vibe CLI - macOS installation script
#
# Usage:
#   sh install_macos.sh              # install editable checkout with tui extra
#   sh install_macos.sh --dev        # install editable checkout with dev extra
#   sh install_macos.sh --extras tui,ai,ux
#   sh install_macos.sh --venv /path/to/.venv
#   sh install_macos.sh --install-bin /path/to/bin

set -eu

EXTRAS="tui"
VENV_DIR=".venv"
INSTALL_BIN="${HOME}/.local/bin"

usage() {
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dev)
            EXTRAS="dev"
            shift
            ;;
        --extras)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --extras requires a comma-separated value, such as tui,ai" >&2
                exit 1
            fi
            EXTRAS="$2"
            shift 2
            ;;
        --venv)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --venv requires a directory path" >&2
                exit 1
            fi
            VENV_DIR="$2"
            shift 2
            ;;
        --install-bin)
            if [ "$#" -lt 2 ]; then
                echo "ERROR: --install-bin requires a directory path" >&2
                exit 1
            fi
            INSTALL_BIN="$2"
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

echo "================================================"
echo "  Mythic Vibe CLI - macOS Setup"
echo "================================================"
echo

if [ "$(uname -s 2>/dev/null || echo unknown)" != "Darwin" ]; then
    echo "ERROR: This installer is for macOS. Use install_linux.sh on Linux."
    exit 1
fi

PYTHON_CMD=""
for candidate in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
        if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
            PYTHON_CMD="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3.10 or newer not found."
    echo "Install it with Homebrew or the official python.org installer:"
    echo "  brew install python"
    echo "  https://www.python.org/downloads/macos/"
    exit 1
fi

PYTHON_VERSION="$($PYTHON_CMD --version 2>&1)"
echo "Found Python: $PYTHON_VERSION via $PYTHON_CMD"

if "$PYTHON_CMD" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 14) else 1)' >/dev/null 2>&1; then
    echo "WARNING: Python 3.14+ is newer than the documented tested range."
    echo "If dependency installation fails, retry with Python 3.12 or 3.13."
fi
echo

if [ ! -f "pyproject.toml" ] || [ ! -d "mythic_vibe_cli" ]; then
    echo "ERROR: Please run this script from the Mythic Vibe CLI repository root."
    exit 1
fi

echo "Creating virtual environment in $VENV_DIR..."
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi
echo

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "ERROR: Could not find $VENV_DIR/bin/activate"
    echo "Remove $VENV_DIR and rerun this script."
    exit 1
fi

# shellcheck source=/dev/null
. "$VENV_DIR/bin/activate"

echo "Upgrading pip..."
python -m pip install --upgrade pip
echo

if [ -n "$EXTRAS" ]; then
    PACKAGE_SPEC=".[${EXTRAS}]"
else
    PACKAGE_SPEC="."
fi

echo "Installing Mythic Vibe CLI from local checkout: $PACKAGE_SPEC"
python -m pip install -e "$PACKAGE_SPEC"
echo

echo "Verifying install..."
mythic-vibe --version
mythic-vibe --help >/dev/null
echo

case "$VENV_DIR" in
    /*) VENV_PATH="$VENV_DIR" ;;
    *) VENV_PATH="$(pwd -P)/$VENV_DIR" ;;
esac
REPO_PATH="$(pwd -P)"

echo "Installing user commands in $INSTALL_BIN..."
mkdir -p "$INSTALL_BIN"

for command_name in mythic mythic-vibe; do
    command_path="$INSTALL_BIN/$command_name"
    venv_command="$VENV_PATH/bin/$command_name"
    cat > "$command_path" <<EOF
#!/bin/sh
VENV_COMMAND="$venv_command"
VENV_PYTHON="$VENV_PATH/bin/python"
REPO_PATH="$REPO_PATH"
PACKAGE_SPEC="$PACKAGE_SPEC"
LOG_DIR="\${XDG_STATE_HOME:-\$HOME/.local/state}/mythic-vibe"
LOG_FILE="\$LOG_DIR/startup-wrapper.log"

log_msg() {
    mkdir -p "\$LOG_DIR" >/dev/null 2>&1 || return 0
    printf '%s %s\n' "\$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)" "\$*" >> "\$LOG_FILE" 2>/dev/null || true
}

repair_once() {
    reason="\$1"
    log_msg "repair requested for $command_name: \$reason"
    if [ ! -d "\$REPO_PATH" ] || [ ! -f "\$REPO_PATH/pyproject.toml" ]; then
        log_msg "repair skipped: repository path unavailable: \$REPO_PATH"
        return 1
    fi
    if [ ! -x "\$VENV_PYTHON" ]; then
        log_msg "repair skipped: venv python unavailable: \$VENV_PYTHON"
        return 1
    fi
    (
        cd "\$REPO_PATH" &&
        "\$VENV_PYTHON" -m pip install -e "\$PACKAGE_SPEC"
    ) >> "\$LOG_FILE" 2>&1
}

if [ ! -x "\$VENV_COMMAND" ]; then
    repair_once "missing executable" || {
        echo "ERROR: Mythic Vibe command is missing: \$VENV_COMMAND" >&2
        echo "Rerun install_macos.sh from \$REPO_PATH" >&2
        exit 127
    }
fi

"\$VENV_COMMAND" "\$@"
status=\$?

if [ "\$status" -eq 126 ] || [ "\$status" -eq 127 ] || { [ "\$status" -ne 0 ] && [ "\${MYTHIC_WRAPPER_REPAIR_ON_FAILURE:-}" = "1" ]; }; then
    repair_once "command exited with status \$status" && "\$VENV_COMMAND" "\$@"
    status=\$?
fi

exit "\$status"
EOF
    chmod +x "$command_path"
done

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'
if [ "$INSTALL_BIN" != "$HOME/.local/bin" ]; then
    PATH_LINE="export PATH=\"$INSTALL_BIN:\$PATH\""
fi

for rc_file in "$HOME/.zprofile" "$HOME/.zshrc" "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.profile"; do
    if [ -f "$rc_file" ]; then
        if ! grep -F "$PATH_LINE" "$rc_file" >/dev/null 2>&1; then
            {
                echo
                echo "# Mythic Vibe CLI user commands"
                echo "$PATH_LINE"
            } >> "$rc_file"
        fi
    fi
done

if [ ! -f "$HOME/.zprofile" ]; then
    {
        echo "# Mythic Vibe CLI user commands"
        echo "$PATH_LINE"
    } > "$HOME/.zprofile"
fi

PATH="$INSTALL_BIN:$PATH"
export PATH

echo "Verifying PATH command..."
mythic --version

echo
echo "================================================"
echo "  Setup Complete"
echo "================================================"
echo
echo "Commands installed:"
echo "  mythic"
echo "  mythic-vibe"
echo
echo "Open a new Terminal window, then run:"
echo "  mythic --help"
echo
