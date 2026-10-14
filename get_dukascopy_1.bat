@echo off
REM Dukascopy 1-minute data, free, no account. Priority 1. Resumable: stop and start again any time.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.data_plans dukascopy --priority 1
echo.
echo Done. Share it with Claude:  git add research_data  then  git commit -m "Dukascopy data 1"  then  git push
pause
