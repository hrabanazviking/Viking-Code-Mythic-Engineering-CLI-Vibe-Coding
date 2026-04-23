#!/data/data/com.termux/files/usr/bin/bash
# MindSpark: ThoughtForge — Termux (Android) Installer
# Requires: Termux app (F-Droid build recommended), Android 8+
#
# Usage (inside Termux):
#   chmod +x install_termux.sh
#   ./install_termux.sh [--profile phone_low] [--model /sdcard/models/tinyllama.gguf]
#
# Options:
#   --profile PROFILE   Hardware profile (default: phone_low)
#   --model PATH        Path to GGUF model file (optional)
#   --data-dir PATH     Data directory (default: ~/thoughtforge-data)
#   --skip-llama        Skip llama-cpp-python (knowledge-only mode)
#   --onnx              Install onnxruntime for ONNX embedding inference
#   --help              Show this message
#
# Notes:
#   - Termux uses its own package manager (pkg), not apt/brew
#   - llama-cpp-python is compiled from source — takes 10-20 min on phone
#   - For very low RAM (< 3GB), use --skip-llama for knowledge-only mode
#   - Model files: use TinyLlama-1.1B-Q2_K.gguf (best for phone_low profile)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
PROFILE="phone_low"
MODEL_PATH=""
DATA_DIR="$HOME/thoughtforge-data"
SKIP_LLAMA=false
INSTALL_ONNX=false

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}[Forge]${NC} $*"; }
success() { echo -e "${GREEN}[Forge]${NC} $*"; }
warn()    { echo -e "${YELLOW}[Forge]${NC} $*"; }
error()   { echo -e "${RED}[Forge]${NC} $*" >&2; exit 1; }

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --profile)    PROFILE="$2"; shift 2 ;;
        --model)      MODEL_PATH="$2"; shift 2 ;;
        --data-dir)   DATA_DIR="$2"; shift 2 ;;
        --skip-llama) SKIP_LLAMA=true; shift ;;
        --onnx)       INSTALL_ONNX=true; shift ;;
        --help|-h)
            grep '^#' "$0" | head -30 | sed 's/^# \?//'
            exit 0 ;;
        *) error "Unknown option: $1" ;;
    esac
done

# ── Termux environment check ──────────────────────────────────────────────────
if ! command -v pkg &>/dev/null; then
    error "pkg not found — this script requires Termux. Download from F-Droid."
fi

info "MindSpark: ThoughtForge — Termux Installer"
info "Profile: $PROFILE | Data dir: $DATA_DIR"

# ── System dependencies ───────────────────────────────────────────────────────
info "Updating Termux packages..."
pkg update -y -q

info "Installing system dependencies..."
pkg install -y -q \
    python \
    cmake \
    ninja \
    clang \
    git \
    sqlite \
    libandroid-spawn \
    binutils

# ── Virtualenv ────────────────────────────────────────────────────────────────
info "Creating virtualenv..."
VENV_DIR="$REPO_ROOT/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet

# ── Python packages ───────────────────────────────────────────────────────────
info "Installing core Python packages..."
pip install --quiet \
    sqlalchemy \
    numpy \
    tqdm \
    pyyaml \
    click \
    rich \
    platformdirs

# sentence-transformers (heavy — try lightweight alternative first)
info "Installing sentence-transformers (this may take a while)..."
pip install --quiet "sentence-transformers>=2.7" || \
    warn "sentence-transformers failed — vector retrieval disabled"

# ijson
pip install --quiet ijson || warn "ijson not available — Wikidata ETL disabled"

if [ "$INSTALL_ONNX" = true ]; then
    info "Installing onnxruntime (for ONNX embedding inference)..."
    pip install --quiet onnxruntime || warn "onnxruntime not available on this architecture"
fi

if [ "$SKIP_LLAMA" = false ]; then
    info "Building llama-cpp-python from source (ARM64 — may take 15-20 min)..."
    warn "This is CPU-only. For best performance on phone, use a Q2_K model."
    CMAKE_ARGS="-DLLAMA_NATIVE=ON" pip install --quiet llama-cpp-python || {
        warn "llama-cpp-python build failed — running in knowledge-only mode"
        warn "Try: --skip-llama for faster install"
    }
fi

# Install ThoughtForge package
pip install --quiet -e "$REPO_ROOT" --no-deps

# ── Data directory ────────────────────────────────────────────────────────────
info "Setting up data directory: $DATA_DIR"
mkdir -p "$DATA_DIR"/{memory,knowledge}

mkdir -p "$HOME/.config/thoughtforge"
cat > "$HOME/.config/thoughtforge/local.yaml" <<EOF
data_dir: "$DATA_DIR"
profile: "$PROFILE"
EOF

# ── Done ──────────────────────────────────────────────────────────────────────
success "ThoughtForge installed in Termux!"
echo ""
echo "  Profile : $PROFILE"
echo "  Data    : $DATA_DIR"
echo "  ONNX    : $INSTALL_ONNX"
[ -n "$MODEL_PATH" ] && echo "  Model   : $MODEL_PATH"
echo ""
echo "Next steps:"
echo "  1. source $VENV_DIR/bin/activate"
echo "  2. python forge_memory.py reference   # build reference knowledge only (fast)"
echo "     (or: python forge_memory.py all    # full knowledge base — hours on phone)"
if [ -n "$MODEL_PATH" ]; then
    echo "  3. python run_thoughtforge.py --model \"$MODEL_PATH\" --profile \"$PROFILE\""
else
    echo "  3. python run_thoughtforge.py --profile \"$PROFILE\""
fi
echo ""
echo "Recommended model for phone_low profile:"
echo "  TinyLlama-1.1B-Chat-v1.0.Q2_K.gguf  (~500MB)"
