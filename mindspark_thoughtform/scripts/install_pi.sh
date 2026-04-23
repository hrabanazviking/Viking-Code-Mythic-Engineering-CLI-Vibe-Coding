#!/usr/bin/env bash
# MindSpark: ThoughtForge — Raspberry Pi Installer
# Supports: Pi Zero 2W, Pi 4, Pi 5 (Raspberry Pi OS / Ubuntu for Pi)
#
# Usage:
#   chmod +x scripts/install_pi.sh
#   ./scripts/install_pi.sh [--profile pi_5] [--model /models/tinyllama.gguf]
#
# Options:
#   --profile PROFILE   Hardware profile: pi_zero | pi_5 (default: auto-detected)
#   --model PATH        Path to GGUF model file (optional)
#   --data-dir PATH     Data directory (default: ~/thoughtforge-data)
#   --skip-llama        Skip llama-cpp-python (knowledge-only mode)
#   --vulkan            Enable Vulkan GPU acceleration (Pi 5 VideoCore VII)
#   --subset            Build edge knowledge subset after install
#   --help              Show this message
#
# Recommended models:
#   Pi Zero 2W (pi_zero profile): TinyLlama-1.1B-Q2_K.gguf  (~500MB)
#   Pi 4/5    (pi_5 profile):     Phi-3-mini-Q4_K_M.gguf     (~2.2GB)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
PROFILE="auto"
MODEL_PATH=""
DATA_DIR="$HOME/thoughtforge-data"
SKIP_LLAMA=false
USE_VULKAN=false
BUILD_SUBSET=false

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[ThoughtForge-Pi]${NC} $*"; }
success() { echo -e "${GREEN}[ThoughtForge-Pi]${NC} $*"; }
warn()    { echo -e "${YELLOW}[ThoughtForge-Pi]${NC} $*"; }
error()   { echo -e "${RED}[ThoughtForge-Pi]${NC} $*" >&2; exit 1; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)    PROFILE="$2"; shift 2 ;;
        --model)      MODEL_PATH="$2"; shift 2 ;;
        --data-dir)   DATA_DIR="$2"; shift 2 ;;
        --skip-llama) SKIP_LLAMA=true; shift ;;
        --vulkan)     USE_VULKAN=true; shift ;;
        --subset)     BUILD_SUBSET=true; shift ;;
        --help|-h)
            grep '^#' "$0" | head -25 | sed 's/^# \?//'
            exit 0 ;;
        *) error "Unknown option: $1" ;;
    esac
done

# ── Pi model detection ────────────────────────────────────────────────────────
detect_pi_profile() {
    local ram_kb
    ram_kb="$(grep MemTotal /proc/meminfo | awk '{print $2}')"
    local ram_mb=$(( ram_kb / 1024 ))

    if [ "$ram_mb" -le 700 ]; then
        echo "pi_zero"
    else
        echo "pi_5"
    fi
}

if [ "$PROFILE" = "auto" ]; then
    PROFILE="$(detect_pi_profile)"
    info "Auto-detected profile: $PROFILE"
fi

# ── Architecture check ────────────────────────────────────────────────────────
ARCH="$(uname -m)"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" && "$ARCH" != "armv8l" ]]; then
    warn "Architecture '$ARCH' may not be a Raspberry Pi. Proceeding anyway."
fi

info "MindSpark: ThoughtForge — Raspberry Pi Installer"
info "Profile: $PROFILE | Arch: $ARCH | RAM: $(grep MemTotal /proc/meminfo | awk '{print $2, $3}')"

# ── System dependencies ───────────────────────────────────────────────────────
info "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    build-essential cmake git ninja-build \
    libsqlite3-dev sqlite3 \
    libopenblas-dev \
    libatlas-base-dev

if [ "$USE_VULKAN" = true ]; then
    info "Installing Vulkan development libraries..."
    sudo apt-get install -y --no-install-recommends \
        libvulkan-dev vulkan-tools mesa-vulkan-drivers || \
        warn "Vulkan libs not available — falling back to CPU"
fi

# ── Swap for pi_zero (needed for compilation) ─────────────────────────────────
if [ "$PROFILE" = "pi_zero" ]; then
    SWAP_SIZE="$(free -m | awk '/^Swap:/{print $2}')"
    if [ "$SWAP_SIZE" -lt 512 ]; then
        warn "Low swap ($SWAP_SIZE MB) — increasing to 1GB for compilation"
        sudo dphys-swapfile swapoff 2>/dev/null || true
        echo "CONF_SWAPSIZE=1024" | sudo tee /etc/dphys-swapfile > /dev/null
        sudo dphys-swapfile setup
        sudo dphys-swapfile swapon
    fi
fi

# ── Virtualenv ────────────────────────────────────────────────────────────────
VENV_DIR="$REPO_ROOT/.venv"
info "Creating virtualenv at $VENV_DIR"
[ -d "$VENV_DIR" ] || python3 -m venv "$VENV_DIR"
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet

# ── Python packages ───────────────────────────────────────────────────────────
info "Installing core packages..."
pip install --quiet \
    sqlalchemy \
    numpy \
    tqdm \
    pyyaml \
    click \
    rich \
    platformdirs \
    ijson

info "Installing sentence-transformers (ARM build — may take several minutes)..."
pip install --quiet "sentence-transformers>=2.7" || \
    warn "sentence-transformers failed — vector retrieval disabled"

if [ "$SKIP_LLAMA" = false ]; then
    info "Building llama-cpp-python (ARM — may take 10-30 min)..."
    if [ "$USE_VULKAN" = true ]; then
        CMAKE_ARGS="-DLLAMA_VULKAN=ON -DLLAMA_NATIVE=ON" \
            pip install --quiet llama-cpp-python || \
            warn "Vulkan build failed — retrying with CPU only"
        CMAKE_ARGS="-DLLAMA_NATIVE=ON" \
            pip install --quiet llama-cpp-python || \
            warn "llama-cpp-python failed — knowledge-only mode"
    else
        CMAKE_ARGS="-DLLAMA_NATIVE=ON" \
            pip install --quiet llama-cpp-python || \
            warn "llama-cpp-python failed — knowledge-only mode"
    fi
fi

pip install --quiet -e "$REPO_ROOT" --no-deps

# ── Data directory ────────────────────────────────────────────────────────────
info "Setting up data directory: $DATA_DIR"
mkdir -p "$DATA_DIR"/{memory,knowledge}
mkdir -p "$HOME/.config/thoughtforge"
cat > "$HOME/.config/thoughtforge/local.yaml" <<EOF
data_dir: "$DATA_DIR"
profile: "$PROFILE"
EOF

# ── Build knowledge subset ────────────────────────────────────────────────────
if [ "$BUILD_SUBSET" = true ]; then
    info "Building edge knowledge subset for $PROFILE..."
    python - <<PYEOF
from pathlib import Path
from thoughtforge.etl.subset import EdgeSubsetBuilder

source = Path("$DATA_DIR/knowledge/thoughtforge.db")
if source.exists():
    builder = EdgeSubsetBuilder()
    result = builder.build(source_db=source, profile_id="$PROFILE")
    print(f"Subset built: {result.entities_copied} entities → {result.output_path}")
else:
    print(f"Source DB not found at {source} — run 'python forge_memory.py all' first")
PYEOF
fi

# ── Done ──────────────────────────────────────────────────────────────────────
success "ThoughtForge installed on Raspberry Pi!"
echo ""
echo "  Profile : $PROFILE"
echo "  Arch    : $ARCH"
echo "  Vulkan  : $USE_VULKAN"
echo "  Data    : $DATA_DIR"
echo ""
echo "Next steps:"
echo "  1. source $VENV_DIR/bin/activate"
echo "  2. python forge_memory.py reference   # fast (minutes)"
echo "     (or: python forge_memory.py all   # full — many hours on Pi)"
if [ -n "$MODEL_PATH" ]; then
    echo "  3. python run_thoughtforge.py --model \"$MODEL_PATH\" --profile \"$PROFILE\""
else
    echo "  3. python run_thoughtforge.py --profile \"$PROFILE\""
fi
echo ""
echo "Recommended models:"
echo "  pi_zero: TinyLlama-1.1B-Chat-v1.0.Q2_K.gguf"
echo "  pi_5:    Phi-3-mini-128k-instruct.Q4_K_M.gguf"
