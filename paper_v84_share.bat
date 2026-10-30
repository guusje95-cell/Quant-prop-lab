@echo off
REM Shares the paper results with Claude (ledger, daily results, status - not the market data). Run e.g. once a week.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v84
python scripts\paper_v5.py reconcile
git add paper_trading/v84/ledger_hourly.csv paper_trading/v84/daily.csv paper_trading/v84/status.md paper_trading/v84/book_next_hour.json paper_trading/v84/events.jsonl paper_trading/v84/reconcile.csv paper_trading/v84/orders.csv
git commit -m "Paper v8.4 results"
git pull --no-rebase --no-edit
git push
pause
