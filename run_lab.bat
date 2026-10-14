@echo off
REM Backtest Lab launcher for Windows: double-click this file.
REM First run: creates a Python environment, installs packages and downloads public market data (a few minutes).
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Install Python 3.11+ from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^) and run this again.
  pause
  exit /b 1
)
if not exist .venv (
  echo Creating Python environment...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt -r requirements-lab.txt
) else (
  call .venv\Scripts\activate.bat
)
set PYTHONPATH=%~dp0src
if not exist data\lab\crypto_majors_1d.parquet (
  echo Downloading public market data ^(one time^)...
  python -m qpl.lab.setup_data
)
streamlit run app\lab.py
pause
