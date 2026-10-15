@echo off
REM Creates a Windows scheduled task that runs paper_v5_once.bat every hour at :06 (no window needed).
REM Remove it again with:  schtasks /Delete /TN QPL_paper_v5 /F
cd /d "%~dp0"
schtasks /Create /F /SC HOURLY /MO 1 /ST 00:06 /TN QPL_paper_v5 /TR "\"%~dp0paper_v5_once.bat\""
echo.
echo Scheduled. Tip: in Task Scheduler, open QPL_paper_v5 ^> Conditions and tick "Wake the computer to run this task",
echo or set Windows sleep to Never while paper trading. Missed hours are caught up on the next run (flagged late).
pause
