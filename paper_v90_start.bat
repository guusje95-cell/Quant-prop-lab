@echo off
REM Paper trading of crypto portfolio v9.0 (Gen373 K1: honest book, no carry, point-in-time C*) - keeps running, one update per hour (at :06 UTC).
REM Simulation only: public Binance, Coinbase, Upbit, Yahoo and Deribit data, no API keys, no orders. Leave this window open and the PC awake.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v90
python -c "import sklearn" 2>nul || pip install -q scikit-learn
python -c "import openpyxl" 2>nul || pip install -q openpyxl
python scripts\paper_v5.py loop
pause
