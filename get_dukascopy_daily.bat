@echo off
REM Free Dukascopy daily candles 2003-2026 (no account, no cost) for Gen208b (gold/platinum) and the 2003-2010 backcasts (Gen218/219).
REM It is slow on purpose (20 s between requests, waits when Dukascopy says "too many requests"); it resumes if you run it again.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python scripts\duka_slow_fetch.py XPTUSD XAUUSD USA500IDXUSD USATECHIDXUSD LIGHTCMDUSD USTBONDTRUSD
echo.
echo Then share it with Claude:
echo   git pull --no-edit
echo   git add research_data/dukascopy_daily
echo   git commit -m "dukascopy daily"
echo   git push
pause
