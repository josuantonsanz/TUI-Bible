@echo off
rem Launch the TUI Bible application from this checkout.
rem Used by the Desktop shortcut created by create_desktop_shortcut.ps1.
rem First run: installs dependencies and builds the local database.
setlocal EnableExtensions
cd /d "%~dp0.."

set "APP_NAME=TUI Bible"

where uv >nul 2>nul
if errorlevel 1 (
    echo [%APP_NAME%] "uv" was not found on PATH.
    echo [%APP_NAME%] Install it from https://docs.astral.sh/uv/ and try again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [%APP_NAME%] First run: installing dependencies with "uv sync"...
    call uv sync
    if errorlevel 1 (
        echo [%APP_NAME%] "uv sync" failed. See the messages above.
        pause
        exit /b 1
    )
)

set "DATA_DIR=%LOCALAPPDATA%\opengnt-interface"
if defined OPENGNT_DATA_DIR set "DATA_DIR=%OPENGNT_DATA_DIR%"

if not exist "%DATA_DIR%\opengnt.db" (
    echo [%APP_NAME%] Building the local database for the first time...
    call uv run opengnt setup --full-install
    if errorlevel 1 (
        echo [%APP_NAME%] Database setup failed. See the messages above.
        pause
        exit /b 1
    )
)

call uv run opengnt-tui
if errorlevel 1 (
    echo.
    echo [%APP_NAME%] The application exited with an error.
    pause
)

endlocal
