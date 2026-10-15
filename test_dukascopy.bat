@echo off
REM Quick Dukascopy check (about 1 minute): one month of EURUSD. Shows the reason if days fail.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
python -c "from qpl.lab import download as D; import pandas as pd; df=D.dukascopy('EURUSD','2026-09-01','2026-09-30'); print('OK', len(df), 'minutes', df.time.min(), '..', df.time.max())"
pause
