@echo off
REM Downloads Bybit public announcement titles (listings / delistings) for research. No key, no account.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.live.bybit_announcements
git add research_data/bybit_announcements
git commit -m "Bybit announcements"
git push
pause
