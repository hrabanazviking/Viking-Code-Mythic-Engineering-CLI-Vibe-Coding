#!/usr/bin/env bash
# MindSpark: ThoughtForge — Linux Installer
# Supports: Debian/Ubuntu, Arch Linux, Fedora/RHEL
#
# Usage:
#   chmod +x scripts/install_linux.sh
#   ./scripts/install_linux.sh [--profile desktop_cpu] [--model /path/to/model.gguf]
#
# Options:
#   --profile PROFILE   Hardware profile (default: auto-detected)
#   --model PATH        Path to GGUF model file (optional)
#   --data-dir PATH     Data directory for knowledge DB (default: ~/.local/share/thoughtforge)
#   --skip-llama        Skip llama-cpp-python install (knowledge-only mode)
#   --help              Show this message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
PROFILE="auto"
MODEL_PATH=""
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/thoughtforge"
SKIP_LLAMA=false
PYTHON_MIN="3.10"

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[ThoughtForge]${NC} $*"; }
success() { echo -e "${GREEN}[ThoughtForge]${NC} $*"; }
warn()    { echo -e "${YELLOW}[ThoughtForge]${NC} $*"; }
error()   { echo -e "${RED}[ThoughtForge]${NC} $*" >&2; exit 1; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)    PROFILE="$2"; shift 2 ;;
        --model)      MODEL_PATH="$2"; shift 2 ;;
        --data-dir)   DATA_DIR="$2"; shift 2 ;;
        --skip-llama) SKIP_LLAMA=true; shift ;;
        --help|-h)
            grep '^#' "$0" | head -20 | sed 's/^# \?//'
            exit 0 ;;
        *) error "Unknown option: $1" ;;
    esac
done

# ── OS detection ──────────────────────────────────────────────────────────────
detect_os() {
    if [ -f /etc/os-release ]; then
        # shellcheck source=/dev/null
        . /etc/os-release
        echo "$ID"
    elif command -v uname &>/dev/null; then
        uname -s | tr '[:upper:]' '[:lower:]'
    else
        echo "unknown"
    fi
}

OS_ID="$(detect_os)"
info "Detected OS: $OS_ID"

# ── System dependency installation ───────────────────────────────────────────
install_system_deps() {
    info "Installing system dependencies..."

    case "$OS_ID" in
        ubuntu|debian|linuxmint|pop)
            sudo apt-get update -qq
            sudo apt-get install -y --no-install-recommends \
                python3 python3-pip python3-venv \
                build-essential cmake git curl \
                libsqlite3-dev sqlite3
            ;;
        arch|manjaro|endeavouros)
            sudo pacman -Sy --noconfirm \
                python python-pip \
                base-devel cmake git curl \
                sqlite
            ;;
        fedora|rhel|centos|rocky|almalinux)
            sudo dnf install -y \
                python3 python3-pip \
                gcc gcc-c++ cmake git curl \
                sqlite sqlite-devel
            ;;
        *)
            warn "Unrecognized distro '$OS_ID' — assuming apt-compatible"
            sudo apt-get install -y --no-install-recommends \
                python3 python3-pip python3-venv build-essential cmake git curl libsqlite3-dev
            ;;
    esac
}

# ── Python version check ──────────────────────────────────────────────────────
check_python() {
    local python_cmd=""
    for cmd in python3.12 python3.11 python3.10 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver="$($cmd --version 2>&1 | grep -oP '(?<=Python )\d+\.\d+')"
            if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then
                python_cmd="$cmd"
                break
            fi
        fi
    done

    if [ -z "$python_cmd" ]; then
        error "Python $PYTHON_MIN+ is required. Install it and retry."
    fi

    echo "$python_cmd"
}

# ── Virtualenv setup ──────────────────────────────────────────────────────────
setup_venv() {
    local python_cmd="$1"
    local venv_dir="$REPO_ROOT/.venv"

    if [ ! -d "$venv_dir" ]; then
        info "Creating virtualenv at $venv_dir"
        "$python_cmd" -m venv "$venv_dir"
    fi

    # shellcheck source=/dev/null
    source "$venv_dir/bin/activate"
    pip install --upgrade pip --quiet
}

# ── Package installation ──────────────────────────────────────────────────────
install_packages() {
    info "Installing ThoughtForge Python packages..."
    pip install --quiet \
        sqlalchemy \
        "sentence-transformers>=2.7" \
        ijson numpy tqdm pyyaml click rich platformdirs

    if [ "$SKIP_LLAMA" = false ]; then
        info "Installing llama-cpp-python (CPU build)..."
        pip install --quiet llama-cpp-python || \
            warn "llama-cpp-python install failed — running in knowledge-only mode"
    fi

    # Install ThoughtForge itself
    pip install --quiet -e "$REPO_ROOT" --no-deps
}

# ── Data directory setup ──────────────────────────────────────────────────────
setup_data_dir() {
    info "Setting up data directory: $DATA_DIR"
    mkdir -p "$DATA_DIR"/{memory,knowledge}

    # Write a local config override pointing to the data dir
    local config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/thoughtforge"
    mkdir -p "$config_dir"
    cat > "$config_dir/local.yaml" <<EOF
data_dir: "$DATA_DIR"
profile: "$PROFILE"
EOF
}

# ── Install completion ────────────────────────────────────────────────────────
print_next_steps() {
    success "ThoughtForge installed successfully!"
    echo ""
    echo "  Profile   : $PROFILE"
    echo "  Data dir  : $DATA_DIR"
    [ -n "$MODEL_PATH" ] && echo "  Model     : $MODEL_PATH"
    echo ""
    echo "Next steps:"
    echo "  1. Activate venv:  source $REPO_ROOT/.venv/bin/activate"
    echo "  2. Build knowledge DB:  python forge_memory.py all"
    if [ -n "$MODEL_PATH" ]; then
        echo "  3. Run:  python run_thoughtforge.py --model \"$MODEL_PATH\" --profile \"$PROFILE\""
    else
        echo "  3. Run (knowledge-only):  python run_thoughtforge.py --profile \"$PROFILE\""
    fi
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    info "MindSpark: ThoughtForge — Linux Installer"

    install_system_deps

    PYTHON_CMD="$(check_python)"
    info "Using Python: $PYTHON_CMD ($($PYTHON_CMD --version))"

    setup_venv "$PYTHON_CMD"
    install_packages
    setup_data_dir
    print_next_steps
}

main
