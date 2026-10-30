@echo off
REM Shares the paper results with Claude (ledger, daily results, status - not the market data). Run e.g. once a week.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v8
python scripts\paper_v5.py reconcile
git add paper_trading/v8/ledger_hourly.csv paper_trading/v8/daily.csv paper_trading/v8/status.md paper_trading/v8/book_next_hour.json paper_trading/v8/events.jsonl paper_trading/v8/reconcile.csv paper_trading/v8/orders.csv
git commit -m "Paper v8 results"
git pull --no-rebase --no-edit
git push
pause
