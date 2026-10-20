@echo off
REM Free SqueezeMetrics DIX / GEX daily history (dealer gamma exposure + dark-pool index), for the intraday GEX-regime tests (Gen240/241).
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.flow_data
echo.
echo If it says "failed": open https://squeezemetrics.com/monitor/static/DIX.csv in your browser and save it as research_data\more2\squeeze_dix.csv
echo Then share it with Claude:
echo   git pull --no-edit
echo   git add research_data/more2/squeeze_dix.csv
echo   git commit -m "squeeze dix"
echo   git push
pause
