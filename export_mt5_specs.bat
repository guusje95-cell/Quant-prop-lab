@echo off
REM Exports every symbol's specification from the MT5 app that is open and logged in (read-only; no orders, no login data saved).
REM Run it once per firm: log in to that firm's account in MT5 first, then double-click this file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python -c "import MetaTrader5" 2>nul || pip install -q MetaTrader5
python scripts\mt5_export_specs.py
echo.
echo Share it with Claude:
echo   git pull --no-rebase --no-edit
echo   git add research_data/firm_specs
echo   git commit -m "firm specs"
echo   git push
pause
