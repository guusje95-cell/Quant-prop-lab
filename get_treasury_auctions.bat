@echo off
REM US Treasury auction calendar from TreasuryDirect (public, no account). About 1 minute. Then push research_data/more2.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.treasury_auctions
echo.
echo Then: git add research_data/more2  /  git commit -m "treasury auctions"  /  git push
pause
