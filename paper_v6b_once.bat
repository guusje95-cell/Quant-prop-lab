@echo off
REM One paper-trading update (used by the hourly scheduled task). Catches up any hours missed while the PC was off.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v6b
if not exist paper_trading\v6b mkdir paper_trading\v6b
python scripts\paper_v5.py run >> paper_trading\v6b\run_log.txt 2>&1
