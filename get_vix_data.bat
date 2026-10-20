@echo off
REM Free CBOE volatility index histories (VIX, VIX3M, VIX9D, VXN, VVIX). No key, no cost.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.vix_data
echo.
echo Then share it with Claude:
echo   git pull --no-edit
echo   git add research_data/more2
echo   git commit -m "vix data"
echo   git push
pause
