"""Shrinks research_data/databento_extra/fut_stats.parquet (raw Databento statistics, >100 MB, not pushable) to a daily summary:
one row per trade date x outright contract x statistic (settlement price 3, cleared volume 6, open interest 9; last value of the day).
Usage (on your PC): python scripts/compact_fut_stats.py   -> research_data/databento_extra/fut_stats_daily.parquet"""
from pathlib import Path
import pandas as pd
D = Path(__file__).resolve().parents[1] / "research_data/databento_extra"
s = pd.read_parquet(D / "fut_stats.parquet")
print("raw rows", len(s), "columns", list(s.columns))
s = s[s["stat_type"].astype(int).isin([3, 6, 9])]
s = s[~s["symbol"].astype(str).str.contains("-")]                 # outrights only (no calendar spreads)
t = pd.to_datetime(s["ts_ref"] if "ts_ref" in s else s["ts_event"], utc=True, errors="coerce")
s = s.assign(date=t.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize())
val = s["price"].where(s["stat_type"].astype(int) == 3, s["quantity"])
out = (s.assign(value=val.astype("float64")).sort_values("ts_event")
        .groupby(["date", "symbol", "stat_type"], observed=True)["value"].last().reset_index())
out["symbol"] = out["symbol"].astype(str); out["stat_type"] = out["stat_type"].astype("int8")
f = D / "fut_stats_daily.parquet"; out.to_parquet(f, index=False, compression="zstd")
print("saved", f, len(out), "rows", round(f.stat().st_size / 1e6, 1), "MB")
