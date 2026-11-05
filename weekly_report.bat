@echo off
REM Weekly monitoring report: paper accounts vs backtest (z-score), shadows, dry-run bots (heartbeat, orders, rejects). Read-only.
REM The hub also runs it once a week (job weekly_report). Output: paper_trading\reports\weekly_<date>.md
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.hub.weekly
echo.
echo Share with Claude: git add paper_trading  then commit and push  (reports\shadows_daily.csv = every shadow day by day)
pause
