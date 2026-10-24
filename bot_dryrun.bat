@echo off
REM v8.6 bot in DRY-RUN (no keys, no orders sent). Run it next to paper_v86_start.bat: it reads paper_trading\v86\book_next_hour.json
REM every 5 minutes and logs the orders it WOULD place to bot_state\orders_log.csv. Stop: close the window, or create bot_state\STOP.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.bot.runner --phase challenge --loop
pause
