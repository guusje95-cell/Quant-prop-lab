@echo off
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v82
python scripts\paper_v5.py status
type paper_trading\v82\book_next_hour.json 2>nul
pause
