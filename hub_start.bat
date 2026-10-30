@echo off
REM Quant Trading Hub background worker: scheduler + research / risk / health / backup jobs. Paper and research only, never live orders.
REM Leave this window open (or use hub_task_scheduler.bat to run it every 15 minutes without a window).
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
echo [1/2] Preparing the hub database and reading all results (first time 2-15 min; details in hub_data_init.log) ...
python -m qpl.hub init > hub_data_init.log 2>&1
if errorlevel 1 (
  echo Init FAILED - the last lines of hub_data_init.log:
  powershell -command "Get-Content hub_data_init.log -Tail 15"
  pause
  exit /b 1
)
echo [1/2] done.
echo [2/2] Worker: every job is listed below as it starts and finishes. Ctrl+C stops it safely.
python -m qpl.hub worker
pause
