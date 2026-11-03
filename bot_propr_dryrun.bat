@echo off
REM v9.9 crypto book on PROPR (Hyperliquid), DRY-RUN: only reads your Propr account (GET), never sends an order.
REM Paste your Propr API key (app.propr.xyz -> Settings) when asked; it stays in this window only (never in a file or in chat).
REM Leave it empty to run without an account (public data only). Needs paper_v98_start.bat + the hub running (for the v9.9 book).
REM Log: bot_state_propr\orders_log.csv. Stop: close the window or create bot_state_propr\STOP.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
set /p PROPR_API_KEY=Propr API key (Enter = none): 
python -m qpl.bot.venue_propr --loop
set PROPR_API_KEY=
pause
