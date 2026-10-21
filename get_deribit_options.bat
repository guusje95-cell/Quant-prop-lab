@echo off
REM Free public data (no account): Deribit options trade history 2020-today for BTC and ETH, reduced to daily flow / put-call /
REM implied-vol-by-strike aggregates (options skew and options flow for the ridge). About 30-90 minutes; resumable (run it again
REM if it stops). Then push research_data/deribit_options.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.deribit_options
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/deribit_options
echo   git commit -m "deribit options"
echo   git push
pause
