@echo off
REM Quick Dukascopy check: 5 days of EURUSD, one line per day (about 30 seconds). Copy the output to Claude.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
echo Testing Dukascopy, one line per day...
python -c "from qpl.lab import download as D; import pandas as pd; [print(d.date(), '->', (lambda x: x if isinstance(x, str) else ('no data (weekend/holiday)' if x is None else f'OK {len(x)} minutes'))(D._duka_day('EURUSD', d, tries=2)), flush=True) for d in pd.date_range('2026-09-14', '2026-09-18')]"
echo.
echo Done. Copy everything above to Claude.
pause
