@echo off
REM Buys the SPY closing-auction imbalance 2018-26 (~$25.87) for the Gen243 confirmation test.
REM It shows the exact price first and only downloads if you type yes.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_buy spy_imbalance
echo.
echo Then share it with Claude:
echo   git pull --no-edit
echo   git add research_data/databento_extra
echo   git commit -m "spy imbalance"
echo   git push
pause
