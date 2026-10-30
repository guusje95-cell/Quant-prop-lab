@echo off
REM Quant Trading Hub background worker: scheduler + research / risk / health / backup jobs. Paper and research only, never live orders.
REM Leave this window open (or use hub_task_scheduler.bat to run it every 15 minutes without a window).
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.hub init > hub_data_init.log 2>&1
python -m qpl.hub worker
pause
