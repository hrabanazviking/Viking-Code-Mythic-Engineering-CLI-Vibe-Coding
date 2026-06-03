@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM Mythic Vibe CLI - Windows installation script
REM
REM Usage:
REM   install_windows.bat
REM   install_windows.bat --dev
REM   install_windows.bat --extras tui,ai,ux
REM   install_windows.bat --venv C:\path\to\.venv
REM ============================================================

set "EXTRAS=tui"
set "VENV_DIR=.venv"
set "VENV_ABS="
set "REPO_ABS="
set "INSTALL_BIN=%LOCALAPPDATA%\Programs\MythicVibeCLI\bin"
set "PYTHON_CMD="
set "PYTHON_VERSION="
set "NEEDS_VENV_CREATE=0"

:parse_args
if "%~1"=="" goto :main
if /i "%~1"=="--help" goto :usage
if /i "%~1"=="-h" goto :usage
if /i "%~1"=="/?" goto :usage
if /i "%~1"=="--dev" (
    set "EXTRAS=dev"
    shift
    goto :parse_args
)
if /i "%~1"=="--extras" (
    if "%~2"=="" (
        echo [ERROR] --extras requires a comma-separated value, such as tui,ai
        exit /b 1
    )
    set "EXTRAS=%~2"
    shift
    shift
    goto :parse_args
)
if /i "%~1"=="--venv" (
    if "%~2"=="" (
        echo [ERROR] --venv requires a directory path.
        exit /b 1
    )
    set "VENV_DIR=%~2"
    shift
    shift
    goto :parse_args
)
echo [ERROR] Unknown option: %~1
goto :usage_error

:usage
echo Mythic Vibe CLI - Windows installation script
echo.
echo Usage:
echo   install_windows.bat              ^& rem install editable checkout with tui extra
echo   install_windows.bat --dev        ^& rem install editable checkout with dev extra
echo   install_windows.bat --extras tui,ai,ux
echo   install_windows.bat --venv C:\path\to\.venv
exit /b 0

:usage_error
echo.
echo Run install_windows.bat --help for usage.
exit /b 1

:main
echo.
echo ============================================================
echo   Mythic Vibe CLI - Windows Setup
echo ============================================================
echo.

if not exist "pyproject.toml" (
    echo [ERROR] pyproject.toml not found.
    echo Please run this script from the Mythic Vibe CLI repository root.
    exit /b 1
)

if not exist "mythic_vibe_cli\" (
    echo [ERROR] mythic_vibe_cli\ not found.
    echo Please run this script from the Mythic Vibe CLI repository root.
    exit /b 1
)

for %%I in ("!VENV_DIR!") do set "VENV_ABS=%%~fI"
for %%I in (".") do set "REPO_ABS=%%~fI"

echo [STEP 1] Searching for Python 3.10 or later...
echo.

for %%v in (3.14 3.13 3.12 3.11 3.10) do (
    if not defined PYTHON_CMD (
        call :try_python "py -%%v"
    )
)

if not defined PYTHON_CMD call :try_python "py -3"
if not defined PYTHON_CMD call :try_python "python"
if not defined PYTHON_CMD call :try_python "python3"

if not defined PYTHON_CMD (
    echo [ERROR] No suitable Python 3.10+ found.
    echo.
    echo Install Python from https://www.python.org/downloads/
    echo During installation, enable "Add Python to PATH".
    exit /b 1
)

echo [OK] Using Python !PYTHON_VERSION! via: !PYTHON_CMD!
echo.

for /f "tokens=1,2 delims=." %%a in ("!PYTHON_VERSION!") do (
    set "PY_MAJOR=%%a"
    set "PY_MINOR=%%b"
)
if "!PY_MAJOR!"=="3" (
    if !PY_MINOR! geq 14 (
        echo [WARN] Python 3.14+ is newer than the documented tested range.
        echo        If dependency installation fails, retry with Python 3.12 or 3.13.
        echo.
    )
)

echo [STEP 2] Creating virtual environment in !VENV_DIR!\ ...
echo.

set "NEEDS_VENV_CREATE=0"
if not exist "!VENV_DIR!\Scripts\python.exe" set "NEEDS_VENV_CREATE=1"
if not exist "!VENV_DIR!\Scripts\activate.bat" set "NEEDS_VENV_CREATE=1"

if "!NEEDS_VENV_CREATE!"=="1" (
    if exist "!VENV_DIR!\" (
        call :quarantine_venv
        if !errorlevel! neq 0 exit /b 1
    )
    !PYTHON_CMD! -m venv "!VENV_DIR!"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        echo Try removing !VENV_DIR!\ and running this script again.
        exit /b 1
    )
) else (
    echo [OK] Virtual environment already exists.
)

if not exist "!VENV_DIR!\Scripts\activate.bat" (
    echo [ERROR] Could not find !VENV_DIR!\Scripts\activate.bat
    echo Remove !VENV_DIR!\ and rerun this script.
    exit /b 1
)

echo [STEP 3] Activating virtual environment...
echo.

call "!VENV_DIR!\Scripts\activate.bat"
if !errorlevel! neq 0 (
    echo [ERROR] Could not activate virtual environment.
    exit /b 1
)

echo [STEP 4] Upgrading pip...
echo.

python -m pip install --upgrade pip
if !errorlevel! neq 0 (
    echo [ERROR] pip upgrade failed.
    exit /b 1
)

echo.
if defined EXTRAS (
    set "PACKAGE_SPEC=.[!EXTRAS!]"
) else (
    set "PACKAGE_SPEC=."
)

echo [STEP 5] Installing Mythic Vibe CLI from local checkout: !PACKAGE_SPEC!
echo.

python -m pip install -e "!PACKAGE_SPEC!"
if !errorlevel! neq 0 (
    echo [ERROR] Package installation failed.
    echo To retry manually:
    echo   !VENV_DIR!\Scripts\activate.bat
    echo   python -m pip install -e "!PACKAGE_SPEC!"
    exit /b 1
)

echo.
echo [STEP 6] Installing user commands...
echo.

if not exist "!INSTALL_BIN!" mkdir "!INSTALL_BIN!"
if !errorlevel! neq 0 (
    echo [ERROR] Could not create !INSTALL_BIN!
    exit /b 1
)

if not exist "!VENV_ABS!\Scripts\mythic.exe" (
    echo [ERROR] !VENV_ABS!\Scripts\mythic.exe not found after installation.
    exit /b 1
)

if not exist "!VENV_ABS!\Scripts\mythic-vibe.exe" (
    echo [ERROR] !VENV_ABS!\Scripts\mythic-vibe.exe not found after installation.
    exit /b 1
)

call :write_launcher "mythic" "!VENV_ABS!\Scripts\mythic.exe"
if !errorlevel! neq 0 exit /b 1
call :write_launcher "mythic-vibe" "!VENV_ABS!\Scripts\mythic-vibe.exe"
if !errorlevel! neq 0 exit /b 1

echo [OK] User commands written to !INSTALL_BIN!
echo.
echo [STEP 7] Updating user PATH...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$bin = $env:LOCALAPPDATA + '\Programs\MythicVibeCLI\bin'; $path = [Environment]::GetEnvironmentVariable('Path','User'); if ([string]::IsNullOrWhiteSpace($path)) { [Environment]::SetEnvironmentVariable('Path', $bin, 'User') } elseif (($path -split ';') -notcontains $bin) { [Environment]::SetEnvironmentVariable('Path', $path.TrimEnd(';') + ';' + $bin, 'User') }"
if !errorlevel! neq 0 (
    echo [WARN] Could not persist !INSTALL_BIN! to the user PATH automatically.
    echo        Add it manually if mythic is not found in new terminals.
) else (
    echo [OK] User PATH includes !INSTALL_BIN!
)

set "PATH=!INSTALL_BIN!;!PATH!"

echo.
echo [STEP 8] Verifying install...
echo.

mythic-vibe --version
if !errorlevel! neq 0 (
    echo [ERROR] mythic-vibe command failed after installation.
    exit /b 1
)

mythic-vibe --help >nul
if !errorlevel! neq 0 (
    echo [ERROR] mythic-vibe --help failed after installation.
    exit /b 1
)

mythic --version
if !errorlevel! neq 0 (
    echo [ERROR] mythic command failed after PATH setup.
    exit /b 1
)

echo.
echo ============================================================
echo   Setup Complete
echo ============================================================
echo.
echo Commands installed:
echo   mythic
echo   mythic-vibe
echo.
echo Open a new terminal, then run:
echo   mythic --help
echo.
exit /b 0

:write_launcher
set "LAUNCHER_NAME=%~1"
set "LAUNCHER_EXE=%~2"
set "LAUNCHER_PATH=!INSTALL_BIN!\!LAUNCHER_NAME!.cmd"
> "!LAUNCHER_PATH!" echo @echo off
>> "!LAUNCHER_PATH!" echo setlocal
>> "!LAUNCHER_PATH!" echo set "VENV_COMMAND=!LAUNCHER_EXE!"
>> "!LAUNCHER_PATH!" echo set "VENV_PYTHON=!VENV_ABS!\Scripts\python.exe"
>> "!LAUNCHER_PATH!" echo set "REPO_PATH=!REPO_ABS!"
>> "!LAUNCHER_PATH!" echo set "PACKAGE_SPEC=!PACKAGE_SPEC!"
>> "!LAUNCHER_PATH!" echo set "LOG_DIR=%%LOCALAPPDATA%%\MythicVibeCLI\logs"
>> "!LAUNCHER_PATH!" echo set "LOG_FILE=%%LOG_DIR%%\startup-wrapper.log"
>> "!LAUNCHER_PATH!" echo if not exist "%%LOG_DIR%%" mkdir "%%LOG_DIR%%" ^>nul 2^>nul
>> "!LAUNCHER_PATH!" echo if not exist "%%VENV_COMMAND%%" call :repair "missing executable"
>> "!LAUNCHER_PATH!" echo if not exist "%%VENV_COMMAND%%" ^(
>> "!LAUNCHER_PATH!" echo   echo ERROR: Mythic Vibe command is missing: %%VENV_COMMAND%% 1^>^&2
>> "!LAUNCHER_PATH!" echo   echo Rerun install_windows.bat from %%REPO_PATH%% 1^>^&2
>> "!LAUNCHER_PATH!" echo   exit /b 127
>> "!LAUNCHER_PATH!" echo ^)
>> "!LAUNCHER_PATH!" echo "%%VENV_COMMAND%%" %%*
>> "!LAUNCHER_PATH!" echo set "STATUS=%%ERRORLEVEL%%"
>> "!LAUNCHER_PATH!" echo if "%%STATUS%%"=="126" call :retry
>> "!LAUNCHER_PATH!" echo if "%%STATUS%%"=="127" call :retry
>> "!LAUNCHER_PATH!" echo if "%%STATUS%%"=="9009" call :retry
>> "!LAUNCHER_PATH!" echo if not "%%STATUS%%"=="0" if "%%MYTHIC_WRAPPER_REPAIR_ON_FAILURE%%"=="1" call :retry
>> "!LAUNCHER_PATH!" echo exit /b %%STATUS%%
>> "!LAUNCHER_PATH!" echo.
>> "!LAUNCHER_PATH!" echo :retry
>> "!LAUNCHER_PATH!" echo call :repair "command exited with status %%STATUS%%"
>> "!LAUNCHER_PATH!" echo "%%VENV_COMMAND%%" %%*
>> "!LAUNCHER_PATH!" echo set "STATUS=%%ERRORLEVEL%%"
>> "!LAUNCHER_PATH!" echo exit /b %%STATUS%%
>> "!LAUNCHER_PATH!" echo.
>> "!LAUNCHER_PATH!" echo :repair
>> "!LAUNCHER_PATH!" echo echo %%DATE%% %%TIME%% repair requested for !LAUNCHER_NAME!: %%~1 ^>^> "%%LOG_FILE%%" 2^>nul
>> "!LAUNCHER_PATH!" echo if not exist "%%REPO_PATH%%\pyproject.toml" ^(
>> "!LAUNCHER_PATH!" echo   echo %%DATE%% %%TIME%% repair skipped: repository path unavailable: %%REPO_PATH%% ^>^> "%%LOG_FILE%%" 2^>nul
>> "!LAUNCHER_PATH!" echo   exit /b 1
>> "!LAUNCHER_PATH!" echo ^)
>> "!LAUNCHER_PATH!" echo if not exist "%%VENV_PYTHON%%" ^(
>> "!LAUNCHER_PATH!" echo   echo %%DATE%% %%TIME%% repair skipped: venv python unavailable: %%VENV_PYTHON%% ^>^> "%%LOG_FILE%%" 2^>nul
>> "!LAUNCHER_PATH!" echo   exit /b 1
>> "!LAUNCHER_PATH!" echo ^)
>> "!LAUNCHER_PATH!" echo pushd "%%REPO_PATH%%" ^>nul 2^>nul
>> "!LAUNCHER_PATH!" echo if errorlevel 1 exit /b 1
>> "!LAUNCHER_PATH!" echo "%%VENV_PYTHON%%" -m pip install -e "%%PACKAGE_SPEC%%" ^>^> "%%LOG_FILE%%" 2^>^&1
>> "!LAUNCHER_PATH!" echo set "REPAIR_STATUS=%%ERRORLEVEL%%"
>> "!LAUNCHER_PATH!" echo popd ^>nul 2^>nul
>> "!LAUNCHER_PATH!" echo exit /b %%REPAIR_STATUS%%
exit /b 0

REM ============================================================
REM SUBROUTINE: try_python ^<cmd^>
REM Tests whether ^<cmd^> runs Python 3.10+.
REM ============================================================
:try_python
set "_TRY_CMD=%~1"

%_TRY_CMD% --version >nul 2>&1
if !errorlevel! neq 0 goto :eof

%_TRY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if !errorlevel! neq 0 goto :eof

for /f "tokens=2" %%v in ('%_TRY_CMD% --version 2^>^&1') do set "_VER=%%v"
set "PYTHON_CMD=%_TRY_CMD%"
set "PYTHON_VERSION=!_VER!"
goto :eof

REM ============================================================
REM SUBROUTINE: quarantine_venv
REM Moves an incomplete existing venv aside before rebuilding.
REM ============================================================
:quarantine_venv
set "BROKEN_VENV=!VENV_ABS!.broken.%RANDOM%"
if exist "!BROKEN_VENV!" set "BROKEN_VENV=!VENV_ABS!.broken.%RANDOM%.%RANDOM%"
echo [WARN] Existing virtual environment is incomplete.
echo        Moving it to !BROKEN_VENV! and creating a fresh one.
move "!VENV_DIR!" "!BROKEN_VENV!" >nul
if !errorlevel! neq 0 (
    echo [ERROR] Could not move broken virtual environment out of the way.
    exit /b 1
)
exit /b 0
