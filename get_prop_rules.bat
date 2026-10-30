@echo off
REM Saves the official prop-firm rule pages (config/prop_sources.json) as evidence for the Quant Trading Hub. Read-only, no login.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.hub.prop_snapshots
git add research_data/prop_pages
git commit -m "prop rule pages"
git push
pause
