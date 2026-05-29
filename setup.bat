@echo off
echo ===================================================
echo        Local Pilot Automated Setup
echo ===================================================
echo.

echo [1/4] Checking for Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH!
    echo Please install Python 3.10+ from python.org and try again.
    pause
    exit /b 1
)

echo [2/4] Creating virtual environment (.venv)...
if not exist .venv (
    python -m venv .venv
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

echo [3/4] Installing dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt

echo [4/4] Registering Context Menu (Right Click)...
echo Running PowerShell script to embed Local Pilot into Windows Explorer...
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\register-context-menu.ps1"

echo.
echo ===================================================
echo Setup Complete! 
echo ===================================================
echo IMPORTANT: Don't forget to rename .env.example to .env
echo and add your Groq API key if you want to use the Cloud Agent!
echo.
echo You can now right-click any file and select "Ask Local Pilot",
echo or run 'run.bat' to start the app directly.
pause
