@echo off
REM New free research data (Gen376 + Gen406): DefiLlama, Blockchain.com, Bybit BTC/ETH OI + long/short, Bybit long/short + OI for 15 coins, Hyperliquid funding.
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
