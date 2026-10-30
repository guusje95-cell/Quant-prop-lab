@echo off
REM Gen431: Bybit USDT perps - launch dates + first 40 days of hourly prices and funding (public Bybit API, no key, no account).
REM Takes about 10-20 minutes. Then it pushes the data so Claude can test the listing short on Bybit (the exchange HyroTrader uses).
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.live.bybit_listings
git add research_data/bybit_listings
git commit -m "Bybit listings data (Gen431)"
git pull --no-rebase --no-edit
git push
pause
