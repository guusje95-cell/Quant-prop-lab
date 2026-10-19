@echo off
REM CME futures history from YOUR Databento account. Step 1 is a free cost check; step 2 only runs if the quote fits your free credit.
REM Your key is typed here once per window and never saved: do not paste it into chat or into any file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
pip install -q databento
set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_futures
echo.
set /p MAXC=Download if the TOTAL is at most how many dollars? (0 = do not download): 
python -m qpl.live.databento_futures --download --max-cost %MAXC%
echo.
echo Then share it with Claude:
echo   git pull --no-edit
echo   git add research_data/databento
echo   git commit -m "databento futures"
echo   git push
pause
