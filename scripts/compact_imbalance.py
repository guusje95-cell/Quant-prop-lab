"""Keeps only the closing-auction window (15:45-16:05 ET) of a raw Databento imbalance file so it fits on GitHub.
Usage (on your PC): python scripts/compact_imbalance.py spy_imbalance   -> research_data/databento_extra/spy_imbalance_close.parquet"""
import sys
from pathlib import Path
import pandas as pd
D = Path(__file__).resolve().parents[1] / "research_data/databento_extra"
name = sys.argv[1] if len(sys.argv) > 1 else "spy_imbalance"
m = pd.read_parquet(D / f"{name}.parquet"); print("raw rows", len(m))
t = pd.to_datetime(m["ts_recv"], utc=True).dt.tz_convert("America/New_York")
hm = t.dt.strftime("%H:%M")
m = m[(hm >= "15:45") & (hm <= "16:05")]
f = D / f"{name}_close.parquet"; m.to_parquet(f, index=False, compression="zstd")
print("saved", f, len(m), "rows", round(f.stat().st_size / 1e6, 1), "MB")
