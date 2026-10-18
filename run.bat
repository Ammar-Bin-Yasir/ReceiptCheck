@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 launcher.py %*
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Install Python 3.11 or newer from https://www.python.org/downloads/
        echo Select "Add python.exe to PATH", then run this file again.
        pause
        exit /b 1
    )
    python launcher.py %*
)
if errorlevel 1 (
    echo.
    echo Startup failed. See the message above and README.md.
    pause
    exit /b 1
)
