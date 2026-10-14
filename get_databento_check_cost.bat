@echo off
REM STEP 1 (free, downloads nothing): prints the exact cost of every Databento item and what fits in a $100 budget.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.data_plans databento --budget 100
pause
