@echo off
REM Read-only Bybit order-book logger for the v9.9 limit-order study (R1): public data only, no key, no orders.
REM Logs the top of the book of 20 coins every 2 s from 23:59 to 00:12 UTC each day into paper_trading\book_logs\.
REM Leave this window open next to the paper traders. Share weekly: git add paper_trading/book_logs, commit, push.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.live.book_logger once
python -m qpl.live.book_logger loop
pause
