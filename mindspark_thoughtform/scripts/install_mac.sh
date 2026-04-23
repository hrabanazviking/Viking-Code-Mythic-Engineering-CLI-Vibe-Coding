#!/usr/bin/env bash
# MindSpark: ThoughtForge — macOS Installer
# Requires: macOS 12+ (Monterey), Homebrew
#
# Usage:
#   chmod +x scripts/install_mac.sh
#   ./scripts/install_mac.sh [--profile desktop_cpu] [--model /path/to/model.gguf]
#
# Options:
#   --profile PROFILE   Hardware profile (default: auto-detected)
#   --model PATH        Path to GGUF model file (optional)
#   --data-dir PATH     Data directory (default: ~/Library/Application Support/thoughtforge)
#   --skip-llama        Skip llama-cpp-python (knowledge-only mode)
#   --metal             Enable Metal GPU acceleration (Apple Silicon)
#   --help              Show this message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
PROFILE="auto"
MODEL_PATH=""
DATA_DIR="$HOME/Library/Application Support/thoughtforge"
SKIP_LLAMA=false
USE_METAL=false

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
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
        --metal)      USE_METAL=true; shift ;;
        --help|-h)
            grep '^#' "$0" | head -20 | sed 's/^# \?//'
            exit 0 ;;
        *) error "Unknown option: $1" ;;
    esac
done

# ── Apple Silicon detection ───────────────────────────────────────────────────
detect_arch() {
    local arch
    arch="$(uname -m)"
    echo "$arch"
}

ARCH="$(detect_arch)"
info "Architecture: $ARCH"

if [ "$ARCH" = "arm64" ] && [ "$USE_METAL" = false ]; then
    info "Apple Silicon detected — consider --metal for Metal GPU acceleration"
fi

# ── Homebrew check ────────────────────────────────────────────────────────────
check_homebrew() {
    if ! command -v brew &>/dev/null; then
        info "Homebrew not found — installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    info "Homebrew: $(brew --version | head -1)"
}

# ── System dependencies ───────────────────────────────────────────────────────
install_system_deps() {
    info "Installing system dependencies via Homebrew..."
    brew install --quiet python@3.11 cmake git sqlite || true
}

# ── Virtualenv setup ──────────────────────────────────────────────────────────
setup_venv() {
    local python_cmd
    python_cmd="$(brew --prefix python@3.11)/bin/python3.11"
    [ ! -f "$python_cmd" ] && python_cmd="python3"

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
        sqlalchemy "sentence-transformers>=2.7" \
        ijson numpy tqdm pyyaml click rich platformdirs

    if [ "$SKIP_LLAMA" = false ]; then
        if [ "$USE_METAL" = true ] && [ "$ARCH" = "arm64" ]; then
            info "Installing llama-cpp-python with Metal acceleration..."
            CMAKE_ARGS="-DLLAMA_METAL=ON" pip install --quiet llama-cpp-python || \
                warn "Metal build failed — falling back to CPU"
        else
            info "Installing llama-cpp-python (CPU build)..."
            pip install --quiet llama-cpp-python || \
                warn "llama-cpp-python install failed — knowledge-only mode"
        fi
    fi

    pip install --quiet -e "$REPO_ROOT" --no-deps
}

# ── Data directory setup ──────────────────────────────────────────────────────
setup_data_dir() {
    info "Setting up data directory: $DATA_DIR"
    mkdir -p "$DATA_DIR"/{memory,knowledge}

    local config_dir="$HOME/.config/thoughtforge"
    mkdir -p "$config_dir"
    cat > "$config_dir/local.yaml" <<EOF
data_dir: "$DATA_DIR"
profile: "$PROFILE"
EOF
}

# ── Print next steps ──────────────────────────────────────────────────────────
print_next_steps() {
    success "ThoughtForge installed successfully!"
    echo ""
    echo "  Architecture : $ARCH"
    echo "  Profile      : $PROFILE"
    echo "  Data dir     : $DATA_DIR"
    echo "  Metal        : $USE_METAL"
    echo ""
    echo "Next steps:"
    echo "  1. source $REPO_ROOT/.venv/bin/activate"
    echo "  2. python forge_memory.py all"
    if [ -n "$MODEL_PATH" ]; then
        echo "  3. python run_thoughtforge.py --model \"$MODEL_PATH\" --profile \"$PROFILE\""
    else
        echo "  3. python run_thoughtforge.py --profile \"$PROFILE\""
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    info "MindSpark: ThoughtForge — macOS Installer"

    if [[ "$(uname -s)" != "Darwin" ]]; then
        error "This script is for macOS only. Use install_linux.sh on Linux."
    fi

    check_homebrew
    install_system_deps
    setup_venv
    install_packages
    setup_data_dir
    print_next_steps
}

main
