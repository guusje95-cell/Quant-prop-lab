@echo off
REM Gen80: about 40 more Binance USD-M coins, hourly (prices, open interest, funding, premium) - more independent bets for
REM premium carry and the liquidation cascade. Several hours (open interest is one file per coin per day); resumable.
REM Keep the PC awake (the script keeps it awake itself; the screen may turn off). Then push research_data.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.binance_vision extra
echo.
echo Done. Share it with Claude:
echo   git add research_data
echo   git commit -m "Binance extra coins"
echo   git push
pause
