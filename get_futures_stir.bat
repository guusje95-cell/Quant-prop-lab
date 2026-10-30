@echo off
REM Short-rate futures (Fed funds ZQ, SOFR SR3, Eurodollar GE) from YOUR Databento account for the futures programme (Gen478).
REM Step 1 is a FREE cost check; nothing is downloaded unless the quoted total is at most the amount you type.
REM Your key is typed here once per window and never saved: do not paste it into chat or into any file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -c "import databento" 2>nul || pip install -q databento
if "%DATABENTO_API_KEY%"=="" set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_stir
echo.
set /p MAXC=Download if the TOTAL is at most how many dollars? (0 = do not download): 
python -m qpl.live.databento_stir --max-cost %MAXC%
echo.
git pull --no-edit
git add research_data/databento_stir
git commit -m "databento STIR futures"
git push
pause
