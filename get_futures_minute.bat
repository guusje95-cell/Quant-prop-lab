@echo off
REM 1-minute CME bars (front contract) for intraday futures research: ES NQ GC CL from 2018. Step 1 is a FREE cost check.
REM Your key stays in this window only: never paste it in chat or a file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_futures --minute
echo.
set /p MAXC=Download if the TOTAL is at most how many dollars? (0 = do not download): 
python -m qpl.live.databento_futures --minute --download --max-cost %MAXC%
echo.
echo Then: git add research_data/databento  /  git commit -m "databento 1m"  /  git push
pause
