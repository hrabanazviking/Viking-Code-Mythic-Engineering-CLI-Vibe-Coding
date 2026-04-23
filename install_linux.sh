#!/bin/bash
# Norse Saga Engine v7.0.0 - Linux Installation Script
# ===================================================

echo "================================================"
echo "  Norse Saga Engine v7.0.0 - Linux Setup"
echo "================================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found!"
    echo "Please install Python 3.10+ using your package manager:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
    echo "  Fedora: sudo dnf install python3 python3-pip"
    echo "  Arch: sudo pacman -S python python-pip"
    exit 1
fi

echo "Found Python:"
python3 --version
echo

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "ERROR: main.py not found!"
    echo "Please run this script from the NorseSagaEngine folder"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate and install dependencies
echo
echo "Installing dependencies..."
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

# ensure requests (for local providers) exists
pip install requests

# optional math libraries
pip install numpy sympy >/dev/null 2>&1 || echo "Optional math libraries skipped (not required)"

# Create config if needed
echo
if [ ! -f "config.yaml" ]; then
    echo "Creating config.yaml from template..."
    cp config.template.yaml config.yaml
    echo
    echo "IMPORTANT: Edit config.yaml to add your API keys!"
    echo "  1. OpenRouter API key (required): https://openrouter.ai/keys"
    echo "  2. Replicate API key (optional): https://replicate.com/account/api-tokens"
else
    echo "config.yaml already exists."
fi

echo
# quick sanity check openrouter key (read with utf-8 encoding to avoid errors)
ORKEY=$(python - <<'PY'
import yaml,sys
try:
    cfg=yaml.safe_load(open('config.yaml', encoding='utf-8'))
except Exception as e:
    cfg={}
print(cfg.get('openrouter',{}).get('api_key',''))
PY
)
if [ -z "$ORKEY" ]; then
    echo "WARNING: OpenRouter API key appears empty or could not be read from config.yaml"
    echo "Please edit config.yaml, ensure it is UTF-8 encoded, and add a valid key before playing."
else
    echo "OpenRouter API key looks configured."
fi

# Create required directories
echo
echo "Creating required directories..."
mkdir -p data/auto_generated/characters
mkdir -p data/auto_generated/quests
mkdir -p data/auto_generated/locations
mkdir -p data/auto_generated/portraits
mkdir -p data/memory
mkdir -p data/sessions
mkdir -p logs
echo "Directories created."

# Make start script executable
chmod +x start_game.sh 2>/dev/null

echo
echo "================================================"
echo "  Setup Complete!"
echo "================================================"
echo
echo "To play the game:"
echo "  1. Edit config.yaml with your API keys"
echo "  2. Run: ./start_game.sh"
echo
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo
