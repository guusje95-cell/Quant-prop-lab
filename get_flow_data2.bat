@echo off
REM Gen247 data (free, public, no account, no key): Upbit KRW hourly for the altcoins + Binance SPOT hourly with taker-buy volume.
REM About 30-45 minutes; resumable (just run it again if it stops). Then push research_data.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.flow_data2
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/more research_data/binance_spot
echo   git commit -m "flow data 2"
echo   git push
pause
