@echo off
REM Paper trading of crypto portfolio v9.8 candidate (v9.7 + Gen468 event short) - keeps running, one update per hour (at :06 UTC).
REM Simulation only: public Binance, Coinbase, Upbit, Yahoo and Deribit data, no API keys, no orders. Leave this window open and the PC awake.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v98
REM Re-use the market data v96 already downloaded (same feeds; v9.8 only adds listing ratios and delisting announcements)
if not exist paper_trading\v98\data if exist paper_trading\v96\data xcopy /E /I /Q /Y paper_trading\v96\data paper_trading\v98\data >nul
python -c "import sklearn" 2>nul || pip install -q scikit-learn
python -c "import openpyxl" 2>nul || pip install -q openpyxl
python scripts\paper_v5.py loop
pause
