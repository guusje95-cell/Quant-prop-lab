@echo off
REM Shares the paper results with Claude (ledger, daily results, status - not the market data). Run e.g. once a week.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v6b
python scripts\paper_v5.py reconcile
git add paper_trading/v6b/ledger_hourly.csv paper_trading/v6b/daily.csv paper_trading/v6b/status.md paper_trading/v6b/book_next_hour.json paper_trading/v6b/events.jsonl paper_trading/v6b/reconcile.csv paper_trading/v6b/orders.csv
git commit -m "Paper v6b shadow results"
git pull --no-rebase --no-edit
git push
pause
