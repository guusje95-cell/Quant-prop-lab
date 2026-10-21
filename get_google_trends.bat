@echo off
REM Gen265 data (free): daily Google search interest for crypto terms 2020-today (retail attention, Koch & Dimpfl 2022).
REM Google rate-limits: this pauses by itself and resumes if you run it again. Expect 30-90 minutes.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -c "import pytrends" 2>nul || pip install -q pytrends
python -m qpl.live.google_trends
echo.
echo Done. Share it with Claude:
echo   git pull --no-edit
echo   git add research_data/attention
echo   git commit -m "google trends"
echo   git push
pause
