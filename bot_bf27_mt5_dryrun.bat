@echo off
REM bf2.7 CFD candidate on MT5, DRY-RUN (no order is ever sent). Open MT5 and log in to your BrightFunded (trial / challenge) account first.
REM Every 5 minutes: builds paper_trading\bf27cand\book_next_hour.json, converts it to lots for this account and VALIDATES each order with
REM MT5's order_check (margin, volume, symbol). Log: bot_state_mt5\orders_log.csv. Stop: close the window or create bot_state_mt5\STOP.
REM Optional: config\news_blackouts.json = list of UTC times of red-folder news (no orders within 6 minutes).
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -c "import MetaTrader5" 2>nul || pip install -q MetaTrader5
python -m qpl.bot.venue_mt5 --phase challenge --loop
pause
