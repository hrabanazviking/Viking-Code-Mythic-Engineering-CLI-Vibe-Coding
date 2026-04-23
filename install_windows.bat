@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Norse Saga Engine v7.0.0 - Windows Installer
REM ============================================================
REM Supports Python 3.10–3.14 via:
REM   py launcher (py -3.x), python, python3 commands.
REM Creates .venv\ (matches launcher.py expectation).
REM Does not close automatically - press a key to exit.
REM ============================================================

echo.
echo ============================================================
echo   Norse Saga Engine v7.0.0 - Windows Setup
echo ============================================================
echo.

REM ============================================================
REM 1. SYSTEM REQUIREMENTS
REM ============================================================

echo [STEP 1] Checking system requirements...
echo.

ver | findstr /i "10 11" >nul
if !errorlevel! equ 0 (
    echo [OK] Windows 10/11 detected
) else (
    echo [WARN] Unrecognised Windows version - proceeding anyway
)

if "%PROCESSOR_ARCHITECTURE%"=="AMD64" (
    echo [OK] 64-bit system
) else (
    echo [WARN] 32-bit system detected (64-bit recommended^)
)
echo.

REM ============================================================
REM 2. FIND A SUITABLE PYTHON (3.10+)
REM ============================================================

echo [STEP 2] Searching for Python 3.10 or later...
echo.

set "PYTHON_CMD="
set "PYTHON_VERSION="

REM --- Helper: test one candidate, accept if 3.10+ ----------
REM   Usage: call :try_python <cmd>
REM   Sets PYTHON_CMD and PYTHON_VERSION on success
REM -----------------------------------------------------------

REM Priority 1: Windows Python Launcher (most reliable on Windows)
REM Try specific minor versions 3.14 down to 3.10 so we get the newest first.
for %%v in (3.14 3.13 3.12 3.11 3.10) do (
    if not defined PYTHON_CMD (
        call :try_python "py -%%v"
    )
)

REM Priority 2: bare "py -3" (picks the latest installed 3.x)
if not defined PYTHON_CMD (
    call :try_python "py -3"
)

REM Priority 3: "python" on PATH
if not defined PYTHON_CMD (
    call :try_python "python"
)

REM Priority 4: "python3" on PATH
if not defined PYTHON_CMD (
    call :try_python "python3"
)

if not defined PYTHON_CMD (
    echo [ERROR] No suitable Python (3.10+^) found.
    echo.
    echo Please install Python 3.10 or later from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT during installation:
    echo   - Check "Add Python to PATH"
    echo   - Check "Install for all users" (recommended^)
    echo.
    echo After installing, run this script again.
    echo.
    pause
    exit /b 1
)

echo [OK] Using Python !PYTHON_VERSION! via: !PYTHON_CMD!
echo.

REM ============================================================
REM 3. HANDLE EXISTING VIRTUAL ENVIRONMENT
REM ============================================================

echo [STEP 3] Checking for existing virtual environment...
echo.

set "VENV_DIR=.venv"
set "VENV_ACTIVATE=.venv\Scripts\activate.bat"
set "KEEP_EXISTING="

REM Check for existing .venv first, then legacy venv/
if exist ".venv\Scripts\python.exe" (
    echo [WARN] Existing .venv\ detected.
    set "FOUND_VENV=.venv"
    goto :ask_venv
)
if exist "venv\Scripts\python.exe" (
    echo [WARN] Existing venv\ detected (legacy name^).
    echo [INFO] The engine now expects .venv\  - this will be migrated.
    set "FOUND_VENV=venv"
    goto :ask_venv
)
echo [OK] No existing virtual environment found
goto :create_venv

:ask_venv
echo.
echo Options:
echo   1. Delete existing environment and create fresh .venv\
echo   2. Keep existing environment and update packages
echo   3. Cancel
echo.
choice /c 123 /m "Choose option (1, 2, or 3): "

if !errorlevel! equ 3 (
    echo [INFO] Installation cancelled.
    echo.
    pause
    exit /b 0
)
if !errorlevel! equ 2 (
    echo [INFO] Keeping existing environment.
    if "!FOUND_VENV!"=="venv" (
        set "VENV_DIR=venv"
        set "VENV_ACTIVATE=venv\Scripts\activate.bat"
    )
    set "KEEP_EXISTING=1"
    goto :activate_venv
)
REM Option 1 — delete and recreate
echo [INFO] Removing old environment...
if "!FOUND_VENV!"=="venv" (
    rmdir /s /q venv >nul 2>&1
) else (
    rmdir /s /q .venv >nul 2>&1
)
if exist "!FOUND_VENV!" (
    echo [ERROR] Could not delete !FOUND_VENV!\ - please remove it manually.
    pause
    exit /b 1
)
echo [OK] Old environment removed.

:create_venv
REM ============================================================
REM 4. CREATE .venv
REM ============================================================

echo.
echo [STEP 4] Creating virtual environment in .venv\ ...
echo.

!PYTHON_CMD! -m venv .venv

if !errorlevel! neq 0 (
    echo [ERROR] Failed to create virtual environment.
    echo.
    echo Possible fixes:
    echo   - Run as Administrator
    echo   - Try: !PYTHON_CMD! -m venv --clear .venv
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv was created but python.exe not found inside it.
    pause
    exit /b 1
)

echo [OK] Virtual environment created: .venv\
goto :activate_venv

:activate_venv
REM ============================================================
REM 5. ACTIVATE AND UPGRADE PIP
REM ============================================================

echo.
echo [STEP 5] Activating virtual environment...
echo.

call "!VENV_ACTIVATE!"

if !errorlevel! neq 0 (
    echo [ERROR] Could not activate virtual environment.
    pause
    exit /b 1
)

echo [OK] Virtual environment active.
echo.
echo [INFO] Upgrading pip...

REM Use python -m pip (safer than calling pip.exe directly during upgrades)
python -m pip install --upgrade pip --quiet

if !errorlevel! neq 0 (
    echo [WARN] pip upgrade failed - continuing with existing pip version.
) else (
    echo [OK] pip up to date.
)

echo.

REM ============================================================
REM 6. INSTALL DEPENDENCIES
REM ============================================================

echo [STEP 6] Installing dependencies...
echo.

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found.
    echo Please ensure requirements.txt exists in the project root.
    pause
    exit /b 1
)

REM Count packages so we can report something useful without dumping the file
for /f %%c in ('find /c /v "" ^< requirements.txt') do set "REQ_LINES=%%c"
echo [INFO] Installing from requirements.txt (!REQ_LINES! entries^)...

python -m pip install -r requirements.txt

if !errorlevel! neq 0 (
    echo [WARN] Some packages failed to install.
    echo.
    echo To retry manually:
    echo   .venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    echo.
    set "DEPS_OK=0"
) else (
    echo [OK] All packages installed.
    set "DEPS_OK=1"
)

echo.

REM ============================================================
REM 7. VERIFY KEY IMPORTS
REM ============================================================

echo [STEP 7] Verifying key packages...
echo.

python -c "import yaml, rich, httpx, requests; print('[OK] Core packages verified')" 2>&1

if !errorlevel! neq 0 (
    echo [WARN] One or more core packages could not be imported.
    echo        Run: pip install PyYAML rich httpx requests
) else (
    REM Check AI packages separately (optional but common)
    python -c "import openai; print('[OK] openai available')" 2>nul
    python -c "import anthropic; print('[OK] anthropic available')" 2>nul
)

echo.

REM ============================================================
REM 8. CONFIGURATION FILE
REM ============================================================

echo [STEP 8] Checking configuration...
echo.

if exist "config.yaml" (
    echo [OK] config.yaml exists.
    echo [INFO] Review it and add your OpenRouter API key if not done already.
) else if exist "config.template.yaml" (
    echo [INFO] Creating config.yaml from template...
    copy /y "config.template.yaml" "config.yaml" >nul
    if !errorlevel! equ 0 (
        echo [OK] config.yaml created.
        echo [INFO] Edit config.yaml and add your OpenRouter API key.
    ) else (
        echo [ERROR] Could not create config.yaml - copy it manually from config.template.yaml.
    )
) else (
    echo [ERROR] Neither config.yaml nor config.template.yaml found.
    echo        Ensure project files are intact.
)

echo.

REM ============================================================
REM 9. CREATE REQUIRED DIRECTORIES
REM ============================================================

echo [STEP 9] Creating required directories...
echo.

for %%d in (logs data session) do (
    if not exist "%%d" (
        mkdir "%%d" >nul 2>&1
        if exist "%%d" (
            echo [OK] Created %%d\
        ) else (
            echo [WARN] Could not create %%d\
        )
    ) else (
        echo [OK] %%d\ exists
    )
)

echo.

REM ============================================================
REM 10. SUMMARY
REM ============================================================

echo ============================================================
echo   INSTALLATION COMPLETE
echo ============================================================
echo.

if defined KEEP_EXISTING (
    echo  Python:      !PYTHON_VERSION! (existing environment kept^)
) else (
    echo  Python:      !PYTHON_VERSION! (new environment in .venv\^)
)

if "!DEPS_OK!"=="1" (
    echo  Packages:    Installed successfully
) else (
    echo  Packages:    Some failures - see warnings above
)

echo.
echo  Next steps:
echo  -----------
echo  1. Edit config.yaml - add your OpenRouter API key
echo     Get one at: https://openrouter.ai/keys
echo.
echo  2. Start the game:
echo       start_game.bat
echo     Or manually:
echo       .venv\Scripts\activate.bat  ^&  python main.py
echo.
echo  3. Troubleshoot:
echo       run_diagnostics.bat
echo       logs\saga.log
echo.
echo ============================================================
echo   Completed: %date% %time%
echo ============================================================
echo.

REM Deactivate cleanly (uses the activate path we set earlier)
call "!VENV_ACTIVATE!" >nul 2>&1
call deactivate >nul 2>&1

echo Press any key to exit...
pause >nul
exit /b 0


REM ============================================================
REM SUBROUTINE: try_python <cmd>
REM Tests if <cmd> gives Python 3.10+ and sets PYTHON_CMD / PYTHON_VERSION
REM ============================================================
:try_python
set "_TRY_CMD=%~1"

REM Run candidate silently - skip if it fails entirely
%_TRY_CMD% --version >nul 2>&1
if !errorlevel! neq 0 goto :eof

REM Detect Windows Store stub: real Python prints version, stub opens Store
REM The stub exits with code 9009 on real execution attempts; test with -c
%_TRY_CMD% -c "import sys; sys.exit(0)" >nul 2>&1
if !errorlevel! neq 0 goto :eof

REM Grab version string
for /f "tokens=2" %%v in ('%_TRY_CMD% --version 2^>^&1') do set "_VER=%%v"

REM Parse major.minor
for /f "tokens=1,2 delims=." %%a in ("!_VER!") do (
    set "_MAJ=%%a"
    set "_MIN=%%b"
)

REM Accept if major=3 and minor>=10
if "!_MAJ!"=="3" (
    if !_MIN! geq 10 (
        set "PYTHON_CMD=%_TRY_CMD%"
        set "PYTHON_VERSION=!_VER!"
    )
)
goto :eof
