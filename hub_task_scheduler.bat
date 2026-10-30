@echo off
REM Registers a Windows scheduled task that runs one hub worker pass every 15 minutes (no window needed). Run once.
cd /d "%~dp0"
schtasks /Create /F /SC MINUTE /MO 15 /TN "QuantTradingHub" /TR "cmd /c cd /d \"%~dp0\" && set PYTHONPATH=%~dp0src && python -m qpl.hub worker --once >> hub_worker.log 2>&1"
echo Task "QuantTradingHub" created. Remove it with: schtasks /Delete /TN QuantTradingHub /F
pause
