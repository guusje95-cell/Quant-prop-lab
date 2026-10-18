@echo off
REM Gen88: Coinbase BTC-USD / ETH-USD hourly candles (free public data, no account) for the Coinbase-premium test.
REM About 10-20 minutes; resumable. Then push research_data.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.coinbase_public
echo.
echo Done. Share it with Claude:
echo   git add research_data
echo   git commit -m "Coinbase hourly"
echo   git push
pause
