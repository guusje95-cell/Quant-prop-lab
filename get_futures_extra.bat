@echo off
REM Extra CME roots, in priority order: UB (ultra bond), NKD (Nikkei USD), PL (platinum, gold/platinum ratio), TN (ultra 10y), EMD (MidCap 400). Hourly 2010-26.
REM Step 1 is a free cost check; step 2 downloads roots in that order while the running total stays at or below the amount you type.
REM Your key is typed here once per window and never saved: do not paste it into chat or into any file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
pip install -q databento
set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_futures --roots UB NKD PL TN EMD
echo.
set /p MAXC=Download if the TOTAL is at most how many dollars? (0 = do not download): 
python -m qpl.live.databento_futures --roots UB NKD PL TN EMD --priority --download --max-cost %MAXC%
echo.
echo Then share it with Claude:
echo   git pull --no-rebase --no-edit
echo   git add research_data/databento
echo   git commit -m "databento extra roots"
echo   git push
pause
