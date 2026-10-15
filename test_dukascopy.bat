@echo off
REM Quick Dukascopy check (under a minute): 3 days of 1-minute EURUSD and 3 months of hourly EURUSD. Copy the output to Claude.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
set PYTHONPATH=src
echo Testing Dukascopy...
python -c "from qpl.lab import download as D; import pandas as pd; f=lambda x: x if isinstance(x, str) else ('no data' if x is None else f'OK {len(x)} bars'); [print('minute', d.date(), '->', f(D._duka_day('EURUSD', d, tries=1)), flush=True) for d in pd.date_range('2026-09-15', '2026-09-17')]; [print('hourly', m.strftime('%%Y-%%m'), '->', f(D._duka_fetch(f'https://datafeed.dukascopy.com/datafeed/EURUSD/{m.year}/{m.month-1:02d}/BID_candles_hour_1.bi5', m, tries=1)), flush=True) for m in pd.date_range('2026-06-01', '2026-08-01', freq='MS')]"
echo.
echo Done. Copy everything above to Claude.
pause
