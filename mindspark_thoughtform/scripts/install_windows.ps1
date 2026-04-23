# MindSpark: ThoughtForge — Windows Installer (PowerShell)
# Requires: Windows 10/11, Python 3.10+, Git
#
# Usage (PowerShell, run as your user — not Administrator required):
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#   .\scripts\install_windows.ps1 [-Profile desktop_cpu] [-Model C:\models\phi.gguf]
#
# Parameters:
#   -Profile      Hardware profile (default: auto)
#   -Model        Path to GGUF model file (optional)
#   -DataDir      Data directory (default: %APPDATA%\thoughtforge)
#   -SkipLlama    Skip llama-cpp-python install (knowledge-only mode)
#   -Vulkan       Enable Vulkan GPU acceleration

param(
    [string]$Profile  = "auto",
    [string]$Model    = "",
    [string]$DataDir  = "$env:APPDATA\thoughtforge",
    [switch]$SkipLlama,
    [switch]$Vulkan,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# ── Script location ────────────────────────────────────────────────────────────
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir

# ── Help ──────────────────────────────────────────────────────────────────────
if ($Help) {
    Get-Content $MyInvocation.MyCommand.Path | Where-Object { $_ -match "^#" } | ForEach-Object {
        $_ -replace "^# ?", ""
    }
    exit 0
}

# ── Colour helpers ─────────────────────────────────────────────────────────────
function Write-Info    { param($Msg) Write-Host "[ThoughtForge] $Msg" -ForegroundColor Cyan }
function Write-Success { param($Msg) Write-Host "[ThoughtForge] $Msg" -ForegroundColor Green }
function Write-Warn    { param($Msg) Write-Host "[ThoughtForge] $Msg" -ForegroundColor Yellow }
function Write-Err     { param($Msg) Write-Host "[ThoughtForge] ERROR: $Msg" -ForegroundColor Red; exit 1 }

# ── Python detection ──────────────────────────────────────────────────────────
function Find-Python {
    $candidates = @("python3.12", "python3.11", "python3.10", "python3", "python")
    foreach ($cmd in $candidates) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python (3\.(10|11|12|13))") {
                return $cmd
            }
        } catch { }
    }
    return $null
}

# ── Main ──────────────────────────────────────────────────────────────────────
Write-Info "MindSpark: ThoughtForge — Windows Installer"
Write-Info "Profile: $Profile | DataDir: $DataDir"

# Check Python
$PythonCmd = Find-Python
if (-not $PythonCmd) {
    Write-Err "Python 3.10+ is required. Download from https://python.org"
}
$PythonVer = & $PythonCmd --version 2>&1
Write-Info "Using $PythonVer"

# Check Git
try {
    $GitVer = & git --version 2>&1
    Write-Info "Git: $GitVer"
} catch {
    Write-Err "Git is required. Download from https://git-scm.com"
}

# Create virtualenv
$VenvDir = Join-Path $RepoRoot ".venv"
if (-not (Test-Path $VenvDir)) {
    Write-Info "Creating virtualenv at $VenvDir"
    & $PythonCmd -m venv $VenvDir
}

# Activate venv
$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
    Write-Err "Virtualenv creation failed — $ActivateScript not found"
}
. $ActivateScript

# Upgrade pip
Write-Info "Upgrading pip..."
pip install --upgrade pip --quiet

# Install core dependencies
Write-Info "Installing ThoughtForge Python packages..."
pip install --quiet `
    sqlalchemy `
    "sentence-transformers>=2.7" `
    ijson numpy tqdm pyyaml click rich platformdirs

# llama-cpp-python
if (-not $SkipLlama) {
    if ($Vulkan) {
        Write-Info "Installing llama-cpp-python with Vulkan acceleration..."
        $env:CMAKE_ARGS = "-DLLAMA_VULKAN=ON"
    } else {
        Write-Info "Installing llama-cpp-python (CPU build)..."
    }
    try {
        pip install --quiet llama-cpp-python
    } catch {
        Write-Warn "llama-cpp-python install failed — running in knowledge-only mode"
    }
    Remove-Item Env:\CMAKE_ARGS -ErrorAction SilentlyContinue
}

# Install ThoughtForge package
Write-Info "Installing ThoughtForge..."
pip install --quiet -e $RepoRoot --no-deps

# Data directory
Write-Info "Setting up data directory: $DataDir"
New-Item -ItemType Directory -Force -Path "$DataDir\memory" | Out-Null
New-Item -ItemType Directory -Force -Path "$DataDir\knowledge" | Out-Null

# Config file
$ConfigDir = "$env:APPDATA\thoughtforge"
New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
@"
data_dir: "$DataDir"
profile: "$Profile"
"@ | Set-Content "$ConfigDir\local.yaml" -Encoding UTF8

# Done
Write-Success "ThoughtForge installed successfully!"
Write-Host ""
Write-Host "  Profile   : $Profile" -ForegroundColor White
Write-Host "  Data dir  : $DataDir" -ForegroundColor White
Write-Host "  Vulkan    : $Vulkan"  -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. $VenvDir\Scripts\Activate.ps1"
Write-Host "  2. python forge_memory.py all"
if ($Model) {
    Write-Host "  3. python run_thoughtforge.py --model `"$Model`" --profile `"$Profile`""
} else {
    Write-Host "  3. python run_thoughtforge.py --profile `"$Profile`""
}
