@echo off
REM FREE cost quote for CME options data (Databento) - downloads nothing and costs nothing. For the futures programme (track 3).
REM Your key is typed here once per window and never saved: do not paste it into chat or into any file.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -c "import databento" 2>nul || pip install -q databento
if "%DATABENTO_API_KEY%"=="" set /p DATABENTO_API_KEY=Paste your Databento API key (stays in this window only): 
python -m qpl.live.databento_options_quote
git pull --no-rebase --no-edit
git add research_data/databento_options_quote.csv
git commit -m "options cost quote"
git push
pause
