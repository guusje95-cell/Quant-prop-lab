@echo off
REM Futures book paper trading: tops up the CME hourly bars from YOUR Databento account, then appends the new trading days to
REM paper_trading\futures\ledger_hourly.csv (each day computed once, never revised). Run it once a day (any time after 00:30 UTC).
REM Step 1 is a FREE cost check; nothing is downloaded unless the quoted total is at most the amount you type.
REM Your key is typed here once per window and never saved: do not paste it into chat or into any file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -c "import databento" 2>nul || pip install -q databento
if "%DATABENTO_API_KEY%"=="" set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_update
echo.
set /p MAXC=Download if the TOTAL is at most how many dollars? (0 = do not download): 
python -m qpl.live.databento_update --max-cost %MAXC%
echo.
python scripts\futures_paper.py
echo.
echo Share the result with Claude / the hub:  git add paper_trading/futures research_data/databento_live  then commit and push
pause
