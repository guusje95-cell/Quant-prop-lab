@echo off
REM Gen459: daily Wikipedia page views for crypto articles (free Wikimedia API, no key, no account). About 1 minute.
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
python -m qpl.live.wiki_attention
git add research_data/attention/wiki_pageviews.parquet
git commit -m "Wikipedia page views (Gen459)"
git pull --no-edit
git push
pause
