@echo off
REM Paper trading of the BrightFunded CFD book bf2.2 (bf2 + spot-flow / VRP / calendar ridge, measured spreads, $200k) - keeps running, one update per hour (at :06 UTC).
REM Simulation only: public Binance, Coinbase, Upbit, Yahoo, Deribit and Dukascopy data, no API keys, no orders. Leave this window open and the PC awake.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=bf22
python -c "import sklearn" 2>nul || pip install -q scikit-learn
python -c "import openpyxl" 2>nul || pip install -q openpyxl
python scripts\paper_v5.py loop
pause
