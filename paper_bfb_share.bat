@echo off
REM Shares the paper results with Claude (ledger, daily results, status - not the market data). Run e.g. once a week.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=bfb
python scripts\paper_v5.py reconcile
git add paper_trading/bfb/ledger_hourly.csv paper_trading/bfb/daily.csv paper_trading/bfb/status.md paper_trading/bfb/book_next_hour.json paper_trading/bfb/events.jsonl paper_trading/bfb/reconcile.csv paper_trading/bfb/orders.csv
git commit -m "Paper bfb shadow results"
git pull --no-edit
git push
pause
