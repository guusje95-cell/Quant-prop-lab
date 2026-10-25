@echo off
REM Shares the paper results with Claude (ledger, daily results, status - not the market data). Run e.g. once a week.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v90
python scripts\paper_v5.py reconcile
git add paper_trading/v90/ledger_hourly.csv paper_trading/v90/daily.csv paper_trading/v90/status.md paper_trading/v90/book_next_hour.json paper_trading/v90/events.jsonl paper_trading/v90/reconcile.csv paper_trading/v90/orders.csv
git commit -m "Paper v9.0 results"
git pull --no-edit
git push
pause
