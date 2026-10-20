@echo off
REM FOMC statement dates 2009-now from federalreserve.gov (public). About 1 minute. Check that most years show 8. Then push research_data/more2.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.fomc_dates
echo.
echo Then: git add research_data/more2  /  git commit -m "fomc dates"  /  git push
pause
