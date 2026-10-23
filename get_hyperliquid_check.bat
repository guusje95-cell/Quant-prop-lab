@echo off
REM Hyperliquid check for v8.6 at Propr (free, public market data, no wallet / account / key): which of our 60 coins trade on
REM Hyperliquid, their max leverage, funding history since 2023, and live spreads. About 15-30 minutes; resumable.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.hyperliquid_check
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/hyperliquid
echo   git commit -m "hyperliquid check"
echo   git push
pause
