@echo off
REM All Dukascopy steps in a row (run overnight, sleep set to Never). Resumable; skipped days are retried on the next run.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.data_plans dukascopy --priority 1
python -m qpl.lab.data_plans dukascopy-spread
python -m qpl.lab.data_plans dukascopy --priority 2
python -m qpl.lab.data_plans dukascopy --priority 3
echo.
echo All done. Share it with Claude:
echo   git add research_data
echo   git commit -m "Dukascopy data"
echo   git push
pause
