@echo off
REM Gen248 data (free, public Binance archive, no account, no key): BTC/ETH perp taker flow by trade size, 2020 to last month.
REM BIG download (tens of GB in total, one month at a time, deleted after processing; ~5 GB free disk needed). Several hours.
REM Resumable: just run it again if it stops. Leave the PC awake. Then push research_data/trade_size (small files).
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.trade_size_flow
echo.
echo Done. Share it with Claude:
echo   git pull --no-rebase --no-edit
echo   git add research_data/trade_size
echo   git commit -m "trade size flow"
echo   git push
pause
