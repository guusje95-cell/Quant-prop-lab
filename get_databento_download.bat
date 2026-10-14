@echo off
REM STEP 2: downloads the items listed by get_databento_check_cost.bat, in priority order, staying under $100 of the free $125 credit.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.data_plans databento --go --budget 100
echo.
echo Done. Share it with Claude:  git add research_data  then  git commit -m "Databento data"  then  git push
pause
