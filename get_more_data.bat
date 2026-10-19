@echo off
REM Gen102: more free public data (no account, no key): Coinbase altcoins, Upbit KRW (kimchi premium), Bitstamp, Fear & Greed.
REM About 30-60 minutes; resumable. Then push research_data.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.more_data
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/coinbase research_data/more
echo   git commit -m "more data"
echo   git push
pause
