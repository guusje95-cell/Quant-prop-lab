@echo off
REM v9.9 CANDIDATE bot in DRY-RUN (no keys, no orders, NOT a paper account). Separate from v9.8: reads the v9.8 paper book and the
REM event-sleeve ledgers, builds paper_trading\v99cand\book_next_hour.json and logs the orders it WOULD place to
REM bot_state_v99cand\orders_log.csv every 5 minutes. Needs paper_v98_start.bat (and the hub) running. Stop: close the window,
REM or create bot_state_v99cand\STOP.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.bot.runner_v99 --phase challenge --loop
pause
