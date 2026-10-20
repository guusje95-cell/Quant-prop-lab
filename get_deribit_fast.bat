@echo off
REM Deribit option flow only (BTC and ETH), 4 parallel requests. Resumes: finished months are skipped. Then push research_data/more2.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.free_data2 deribit
echo.
echo Then: git add research_data/more2  /  git commit -m "deribit"  /  git push
pause
