@echo off
REM Paper trading of crypto portfolio v5 - keeps running, one update per hour (at :06 UTC).
REM Simulation only: public Binance market data, no API keys, no orders. Leave this window open and the PC awake.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -c "import openpyxl" 2>nul || pip install -q openpyxl
python scripts\paper_v5.py loop
pause
