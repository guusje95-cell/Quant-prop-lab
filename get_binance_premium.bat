@echo off
REM Extra (small, a few minutes): hourly perp premium index = the basis between perp and spot, for the 20 coins.
REM Run after get_binance_data.bat has finished, then push research_data again.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.binance_vision premium
echo.
echo Done. Share it with Claude:
echo   git add research_data
echo   git commit -m "Binance premium index"
echo   git push
pause
