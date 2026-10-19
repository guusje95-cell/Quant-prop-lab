@echo off
REM Free public data part 2 (no account, no key): CFTC COT positioning (futures) and Deribit option trades (crypto skew/flows).
REM COT takes ~2 minutes; Deribit several hours (resumable: run again to continue). Then push research_data/more2.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.free_data2 %1
echo.
echo Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/more2
echo   git commit -m "free data 2"
echo   git push
pause
