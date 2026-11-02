@echo off
REM Exports the MT5 terminal's own bid/ask tick history (read-only, no orders) for the CFD book's symbols, last 30 days.
REM Open MT5 and log in to your BrightFunded account first. Takes a few minutes. Then push it (commands below).
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -c "import MetaTrader5" 2>nul || pip install -q MetaTrader5
python scripts\mt5_export_ticks.py --days 30
echo.
echo Share it with Claude:
echo   git pull --no-rebase --no-edit
echo   git add research_data/firm_ticks
echo   git commit -m "MT5 ticks"
echo   git push
pause
