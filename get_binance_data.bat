@echo off
REM Downloads free Binance futures data (1-minute candles, open interest / long-short ratios, funding, premium index) for 20 coins.
REM Takes 1-3 hours the first time; you can stop and start again, finished months are kept.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.binance_vision all
echo.
echo Done. Now share the compact pack with Claude:
echo   git add research_data
echo   git commit -m "Binance research data"
echo   git push
pause
