@echo off
REM Everything free in one go (run overnight; set Windows sleep to "Never" first). Each step resumes where it stopped.
REM 1) Binance futures: 1-minute candles, open interest / long-short, funding, premium index (20 coins)
REM 2) Dukascopy 1-minute: priority 1, ask-price spreads, priority 2, priority 3
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.binance_vision all
python -m qpl.lab.data_plans dukascopy --priority 1
python -m qpl.lab.data_plans dukascopy-spread
python -m qpl.lab.data_plans dukascopy --priority 2
python -m qpl.lab.data_plans dukascopy --priority 3
echo.
echo All done. Share it with Claude:
echo   git add research_data
echo   git commit -m "Binance + Dukascopy data"
echo   git push
pause
