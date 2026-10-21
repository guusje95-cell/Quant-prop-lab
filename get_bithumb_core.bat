@echo off
REM Gen277 core set only (BTC, ETH + the 16 altcoins of the kimchi sleeve): about 1 hour instead of 4. Resumable.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -m qpl.live.bithumb BTC ETH AAVE ADA ATOM AVAX BCH DOGE DOT ETC FIL LINK NEAR SOL TRX UNI XLM XRP
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/more
echo   git commit -m "bithumb"
echo   git push
pause
