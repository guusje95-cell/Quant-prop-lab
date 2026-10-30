@echo off
REM Futures book paper trading WITHOUT downloading: appends any completed trading days already in research_data\databento_live.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python scripts\futures_paper.py
pause
