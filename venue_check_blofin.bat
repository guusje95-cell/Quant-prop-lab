@echo off
REM Checks which positions of the running v9.8 paper book are tradable on BloFin (demo = HyroTrader's BloFin challenges, and live).
REM Public market data only: no key, no account, no orders.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.bot.venue_blofin --book paper_trading\v98\book_next_hour.json --env demo --account 200000
python -m qpl.bot.venue_blofin --book paper_trading\v98\book_next_hour.json --env live --account 200000
pause
