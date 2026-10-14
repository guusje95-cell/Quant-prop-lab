@echo off
REM ASK prices 2023+ for US100, US500, US30, DE40, gold, EURUSD -> real bid/ask spreads per hour. Run after get_dukascopy_1.bat.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.lab.data_plans dukascopy-spread
echo.
echo Done. Share it with Claude:  git add research_data  then  git commit -m "Dukascopy spreads"  then  git push
pause
