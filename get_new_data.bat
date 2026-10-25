@echo off
REM New free research data (Gen376): DefiLlama (stablecoins, DEX / perp-DEX volume, TVL), Blockchain.com (mempool, fees, miners),
REM Bybit public BTC/ETH open interest and long/short ratio. Public endpoints only: no account, no key, no payment. About 2-5 minutes.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.new_data
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/newdata
echo   git commit -m "new data"
echo   git push
pause
