@echo off
REM QUOTE ONLY: prints the price of order-flow and options datasets on Databento. Downloads nothing and costs nothing.
REM Your key is typed here once per window and never saved: do not paste it into chat or into any file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_quotes
pause
