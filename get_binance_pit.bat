@echo off
REM Gen321 survivorship check (free, public): EVERY Binance USD-M USDT perp ever listed since 2020, delisted coins included
REM (about 350 symbols): hourly close + volume, funding, premium index. A few hours; resumable (run again if it stops).
REM Keep the PC awake. Then push research_data/binance_pit (~100-200 MB).
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.binance_vision pit
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/binance_pit
echo   git commit -m "binance point-in-time universe"
echo   git push
pause
