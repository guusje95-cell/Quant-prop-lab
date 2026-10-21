@echo off
REM Shares the paper results with Claude (ledger, daily results, status - not the market data). Run e.g. once a week.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=bf22
python scripts\paper_v5.py reconcile
git add paper_trading/bf22/ledger_hourly.csv paper_trading/bf22/daily.csv paper_trading/bf22/status.md paper_trading/bf22/book_next_hour.json paper_trading/bf22/events.jsonl paper_trading/bf22/reconcile.csv paper_trading/bf22/orders.csv
git commit -m "Paper bf22 results"
git pull --no-edit
git push
pause
