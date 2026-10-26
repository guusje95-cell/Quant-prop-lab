@echo off
REM Gen410 cascade survivorship check (free, public Binance archive): hourly high/low (from the files your pit download already has)
REM and open interest for the ~160 coins that were ever in the point-in-time top-20 (delisted coins included). Resumable; a few hours.
REM Keep the PC awake. Then push research_data/binance_pit.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.binance_vision cascadepit
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/binance_pit
echo   git commit -m "cascade pit data"
echo   git push
pause
