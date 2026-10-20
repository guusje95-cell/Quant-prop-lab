"""Dukascopy history 2003-today for Gen208b / Gen218 / Gen219, via the hourly downloader that works on the user's PC
(qpl.lab.download.duka_hourly: one request per month, cools down and retries after timeouts/blocks), resampled to daily (UTC).
Usage: python scripts/duka_slow_fetch.py   (resumable: finished instruments are skipped). Writes research_data/dukascopy_daily/*_D1_raw.parquet."""
import sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from qpl.lab import download as DL
OUT = ROOT / "research_data/dukascopy_daily"; OUT.mkdir(parents=True, exist_ok=True)
# lab symbol -> file name expected by the research scripts
JOBS = {"XPTUSD": "XPTUSD", "XAUUSD": "XAUUSD", "US500": "USA500IDXUSD", "US100": "USATECHIDXUSD", "WTI": "LIGHTCMDUSD", "USTBOND": "USTBONDTRUSD"}
for sym, name in JOBS.items():
    f = OUT / f"{name}_D1_raw.parquet"
    if f.exists():
        print(name, "already done"); continue
    try:
        h = DL.duka_hourly(sym, "2003-01-01").set_index("time").sort_index()
    except Exception as e:
        print(name, "FAILED:", e, "(run the .bat again later; it resumes)", flush=True); continue
    d = h.resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna(subset=["close"])
    d.astype("float64").to_parquet(f)
    print(name, "DONE", len(d), d.index.min().date(), d.index.max().date(), flush=True)
