@echo off
REM DRY-RUN of the daily-flat index book (US500 / US100 / US2000 / US30 CFDs) on a logged-in MT5 terminal (FTMO / FundedNext / The5ers type).
REM Flat 15:55-18:00 ET and at weekends. Orders are only checked (order_check), never sent. Targets are rebuilt at 14:05 and 16:30 ET
REM from the futures data: a Databento top-up costs a few cents (you set the maximum; 0 = no download, then the targets use the last data).
REM Your Databento key is typed here once per window and never saved: do not paste it into chat or into any file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -c "import MetaTrader5" 2>/dev/null || pip install -q MetaTrader5
if "%DATABENTO_API_KEY%"=="" set /p DATABENTO_API_KEY=Paste your Databento API key (Enter = skip, then no top-ups): 
set /p MAXC=Maximum dollars per Databento top-up (e.g. 0.5; 0 = none): 
set /p ACC=Account size in USD (e.g. 100000): 
set /p RISK=Book risk (1.0 = 10%% vol; 1.4 = 14%%): 
set /p CFDM=CFD firm (hold until 16:55 ET, swap at 17:00)? y/n: 
set EXTRA=
if /i "%CFDM%"=="y" (set QPL_FLAT_FROM=17& set EXTRA=--cfd-1655)
python scripts\v99\dailyflat_targets.py
python -m qpl.bot.runner_dailyflat --loop --account %ACC% --risk %RISK% --max-cost %MAXC% %EXTRA%
pause
