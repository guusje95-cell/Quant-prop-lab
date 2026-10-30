@echo off
REM v9.8 on UNSEEN data: recomputes the frozen book up to 30 Oct 2026 00:00 UTC with the paper trader's own live data folder
REM (the research data ends 30 Sep 2026, so October was never seen). Read-only for the paper trader; no orders. Takes 5-20 minutes.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=%~dp0src
set QPL_PAPER=v98
python scripts\paper_v5.py _dump --cutoff "2026-10-30 00:00" --live 1 --out results\v98_oct_oos.parquet
git pull --no-rebase --no-edit
git add results/v98_oct_oos.parquet results/v98_oct_oos.book.json
git commit -m "v98 October out-of-sample dump"
git push
pause
