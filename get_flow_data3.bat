@echo off
REM Gen262 data (free, public, no account, no key): Upbit KRW for the 40 extra coins, Binance TRY/BRL/EUR pairs, Yahoo FX.
REM About 30-60 minutes; resumable (just run it again if it stops). Then push research_data.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.flow_data3
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/more research_data/binance_fiat
echo   git commit -m "flow data 3"
echo   git push
pause
