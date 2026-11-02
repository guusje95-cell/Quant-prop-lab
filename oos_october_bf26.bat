@echo off
REM bf2.6 on UNSEEN data: recomputes the CFD book up to its paper start (21 Oct 2026 15:00 UTC) with the paper trader's own live data folder
REM (the research data ends 30 Sep 2026, so October was never seen). Read-only for the paper trader; no orders. Takes 5-20 minutes.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=bf26
python scripts\paper_v5.py _dump --cutoff "2026-10-21 15:00" --live 1 --out results\bf26_oct_oos.parquet
git pull --no-rebase --no-edit
git add results/bf26_oct_oos.parquet results/bf26_oct_oos.book.json
git commit -m "bf26 October out-of-sample dump (closes the prefix gap of the bf2.7 shadow)"
git push
pause
