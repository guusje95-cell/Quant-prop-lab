@echo off
REM One paper-trading update (used by the hourly scheduled task). Catches up any hours missed while the PC was off.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python scripts\paper_v5.py run >> paper_trading\v5\run_log.txt 2>&1
