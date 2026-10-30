@echo off
REM Bybit reality check for v8.6 (free, public market data, no account / no key): which of our 60 coins trade on Bybit,
REM their order sizes, funding history since 2020, and live spreads. About 15-30 minutes; resumable. Then push research_data/bybit.
REM Bybit may be restricted in some countries; if every request fails, paste the error to Claude.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.bybit_check
echo.
echo Done. Share it with Claude:
echo   git pull --no-rebase --no-edit
echo   git add research_data/bybit
echo   git commit -m "bybit check"
echo   git push
pause
