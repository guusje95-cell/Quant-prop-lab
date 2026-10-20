"""Gen202 (config/gen202_protocol.json): VM / BCX / R1X on BTC/ETH as v7 sleeves. Writes results/gen202.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen171_crypto_calendar.py").read()
g = {"__file__": str(ROOT / "scripts/gen171_crypto_calendar.py")}; exec(src.split("\ndays = pd.date_range")[0], g)
CS, HV7, sh, per, B0, k0 = (g[k] for k in ("CS", "HV7", "sh", "per", "B0", "k0"))
COINS = ["BTC", "ETH"]; days = pd.date_range("2020-01-01", "2026-09-30")
DB = {}
for c in COINS:
    x = CS.B.k5(c); d = pd.DataFrame({"o": x.open.resample("1D").first(), "h": x.high.resample("1D").max(), "l": x.low.resample("1D").min(), "c": x.close.resample("1D").last()})
    DB[c] = d.reindex(days)


def rsi2(c):
    dd = c.diff(); up = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd).clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def weights(kind):
    W = {}
    for c in COINS:
        d = DB[c]; r = d.c.pct_change()
        if kind == "VM":
            W[c] = 0.5 * (0.60 / (r.rolling(20).std() * np.sqrt(365))).clip(upper=2)
        elif kind == "BCX":
            z = r / r.rolling(60, min_periods=40).std().shift(1); s = pd.Series(np.where(z.abs() > 2, np.sign(r), 0.0), index=r.index)
            W[c] = 0.5 * s.shift(1).rolling(3, min_periods=1).mean()
        else:
            ibs = (d.c - d.l) / (d.h - d.l)
            ind = [rsi2(d.c) < 10, d.c <= d.c.rolling(5).min(), d.c.diff().lt(0).rolling(3).sum() == 3, ibs < 0.3]
            W[c] = 0.5 * sum(z.astype(float) for z in ind) / 4
    return pd.DataFrame(W).fillna(0.0)                      # row d = decided at the close of d, held during d+1


out = {"v7": [round(B0, 3), np.round(k0, 3).tolist()]}
for kind in ("VM", "BCX", "R1X"):
    sl = CS._from_daily_weights(weights(kind), COINS, 7.5).loc[:"2026-09-30 23:00"]; p = per(sl, "2020-01-01")
    vb = CS.portfolio_v5(pd.concat([HV7, sl.rename(kind)], axis=1).fillna(0.0))[0]; B1, k1 = sh(vb, "2022-01-01", "2026-09-30"), per(vb, "2022-01-01")
    out[kind] = {"sleeve D/T/H": np.round(p, 3).tolist(), "book": [round(B1, 3), np.round(k1, 3).tolist()],
                 "pass": bool(p[0] > 0 and p[1] >= 0.8 and p[2] >= 0.5 and B1 > B0 and k1[1] >= k0[1] and k1[2] >= k0[2])}
    print(kind, out[kind], flush=True)
    if out[kind]["pass"]:
        vb.to_frame("book").to_parquet(ROOT / f"results/gen202_{kind}_book.parquet")
json.dump(out, open(ROOT / "results/gen202.json", "w"), indent=1)
