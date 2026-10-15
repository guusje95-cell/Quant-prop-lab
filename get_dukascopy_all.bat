@echo off
REM Dukascopy in three passes (sleep set to Never). Resumable; failed days/months are retried on the next run.
REM 1) hourly 2013-today for all 35 instruments (fast, ~5-10 min per instrument)
REM 2) 1-minute 2018-today for US100, US500, US30, DE40, gold, EURUSD (slow: Dukascopy throttles; overnight)
REM 3) ask prices 2025+ for the same 6 (real spreads)
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.data_plans dukascopy-hourly
echo.
echo Hourly data done. You can push now (git add research_data, commit, push) while the rest continues.
python -m qpl.lab.data_plans dukascopy --priority 1
python -m qpl.lab.data_plans dukascopy-spread
echo.
echo All done. Share it with Claude:
echo   git add research_data
echo   git commit -m "Dukascopy data"
echo   git push
pause
