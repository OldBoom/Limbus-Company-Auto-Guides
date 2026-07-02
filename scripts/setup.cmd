@echo off
REM One-time environment setup (Windows CMD — no PowerShell execution policy needed)
REM Run from repo root: scripts\setup.cmd

setlocal
cd /d "%~dp0.."

where python >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://www.python.org/downloads/
    exit /b 1
)

python --version

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 exit /b 1
)

set VENV_PY=.venv\Scripts\python.exe

"%VENV_PY%" -m pip install -q --upgrade pip
"%VENV_PY%" -m pip install -q -r requirements.txt
"%VENV_PY%" -m pip install -q -e .
"%VENV_PY%" -m pip install -q pytest
"%VENV_PY%" -m spacy download en_core_web_sm

echo.
echo Setup complete. Use the venv Python directly (no Activate.ps1 required):
echo   .venv\Scripts\python.exe scripts\run_pipeline.py
echo   .venv\Scripts\python.exe -m limbus_guides.pipeline.run
echo   .venv\Scripts\python.exe -m streamlit run src\limbus_guides\dashboard\app.py

endlocal
