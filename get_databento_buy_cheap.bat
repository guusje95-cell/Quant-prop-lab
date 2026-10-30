@echo off
REM Buys the two cheap items: QQQ closing-auction imbalance 2018-26 (~$1.67) and ES/NQ futures statistics 2010-26 (~$1.07).
REM It shows the exact price first and only downloads if you type yes.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_buy qqq_imbalance fut_stats
echo.
echo Then share it with Claude:
echo   git pull --no-rebase --no-edit
echo   git add research_data/databento_extra
echo   git commit -m "qqq imbalance + futures stats"
echo   git push
pause
