"""EX-1c (protocol research/v99/ex1c_protocol.json): Weiss expiry trade edge vs entry delay at 1-minute resolution.
Data: Binance USDT-M perp 1-minute klines from the public archive data.binance.vision (the fapi endpoint is geo-restricted from the
cloud container; same data). Cached in research_data/binance_1m_weiss/. Writes results/v99/ex1c_weiss_1m.json."""
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "research_data/binance_1m_weiss"; CACHE.mkdir(parents=True, exist_ok=True)
DELAYS = (0, 1, 2, 3, 5, 10, 15)


def day_1m(sym: str, d: pd.Timestamp) -> pd.DataFrame:
    f = CACHE / f"{sym}_{d.date()}.parquet"
    if f.exists():
        return pd.read_parquet(f)
    u = f"https://data.binance.vision/data/futures/um/daily/klines/{sym}/1m/{sym}-1m-{d.date()}.zip"
    for k in range(4):
        try:
            raw = urllib.request.urlopen(u, timeout=60).read(); break
        except Exception:
            time.sleep(2 * (k + 1)); raw = None
    if raw is None:
        return pd.DataFrame()
    z = zipfile.ZipFile(io.BytesIO(raw)); x = pd.read_csv(z.open(z.namelist()[0]), header=None)
    if not str(x.iloc[0, 0]).isdigit():
        x = x.iloc[1:]
    x = x.iloc[:, :5].astype(float); x.columns = ["t", "open", "high", "low", "close"]
    x.index = pd.to_datetime(x.pop("t").astype("int64"), unit="ms")
    x = x.between_time("06:55", "10:10"); x.to_parquet(f); return x


days = pd.date_range("2022-01-07", "2026-09-30", freq="W-FRI"); days = days[(days + pd.Timedelta(days=7)).month != days.month]
rows = []
for d in days:
    for sym in ("BTCUSDT", "ETHUSDT"):
        x = day_1m(sym, d)
        if x.empty:
            continue
        o = x["open"]; t7, t8, t10 = d + pd.Timedelta(hours=7), d + pd.Timedelta(hours=8), d + pd.Timedelta(hours=10)
        if not all(t in o.index for t in (t7, t8, t10)):
            continue
        pre = o[t8] / o[t7] - 1
        if pre == 0:
            continue
        side = -np.sign(pre); r = {"day": str(d.date()), "coin": sym[:3], "pre_bp": round(pre * 1e4, 1)}
        for dl in DELAYS:
            te = t8 + pd.Timedelta(minutes=dl)
            r[f"d{dl}"] = (side * (o[t10] / o[te] - 1) - 10 / 1e4) * 1e4 if te in o.index else np.nan
        rows.append(r)
T = pd.DataFrame(rows)
out = {"trades": len(T), "days": int(T.day.nunique()),
       "per-trade net bp (mean, t)": {f"{d} min": [round(float(T[f'd{d}'].mean()), 1), round(float(T[f'd{d}'].mean() / T[f'd{d}'].std() * np.sqrt(T[f'd{d}'].count())), 2)] for d in DELAYS},
       "share of the d=0 mean kept": {f"{d} min": round(float(T[f'd{d}'].mean() / T['d0'].mean()), 2) for d in DELAYS},
       "by year, d=0 / d=1 / d=15 (bp)": {y: [round(float(g[c].mean()), 1) for c in ("d0", "d1", "d15")] for y, g in T.groupby(T.day.str[:4])}}
print(json.dumps(out, indent=1)); (ROOT / "results/v99/ex1c_weiss_1m.json").write_text(json.dumps(out, indent=1))
T.to_csv(ROOT / "results/v99/ex1c_weiss_trades.csv", index=False)
