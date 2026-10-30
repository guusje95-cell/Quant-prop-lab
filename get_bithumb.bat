@echo off
REM Gen277 data (free, public, no account): Bithumb KRW hourly candles (second Korean exchange) for BTC, ETH and our altcoins.
REM About 20-40 minutes; resumable (run it again if it stops). Then push research_data/more.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.bithumb
echo.
echo Done. Share it with Claude:
echo   git pull --no-rebase --no-edit
echo   git add research_data/more
echo   git commit -m "bithumb"
echo   git push
pause
