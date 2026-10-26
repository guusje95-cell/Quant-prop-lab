"""Gen417 (config/gen417_protocol.json): vol forecast for the book's vol targeting. Writes results/gen417.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
END = "2026-09-30"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet")
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
D = dd(V); W = CS.v5_weights(D, list(V.columns)); Wh = W.reindex(V.index.floor("D")).set_axis(V.index)
raw = (V * Wh).sum(axis=1); rawd = dd(raw)
lvl = (0.15 / (rawd.rolling(365, min_periods=60).std() * np.sqrt(365))).shift(1); x1 = rawd * lvl
xh = raw * lvl.reindex(raw.index.floor("D")).set_axis(raw.index)
def book(sd_daily):
    tgt = (0.15 / (sd_daily * np.sqrt(365))).clip(upper=1.5).shift(1); mu = (lvl * tgt).loc["2022-01-01":]
    return unit((raw * mu.reindex(raw.index.floor("D")).set_axis(raw.index)).loc["2022-01-01":].dropna())
ref = book(x1.rolling(30).std()); v95 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v95), per(v95))
hv = (xh ** 2).groupby(xh.index.floor("D")).mean() * 24
T = {"A EWMA": x1.ewm(halflife=10, min_periods=30).std(),
     "B HAR mix": np.sqrt((x1.rolling(7).var() + x1.rolling(30).var() + x1.rolling(90).var()) / 3),
     "C hourly realised vol": np.sqrt(hv.rolling(10).mean())}
out = {"reference v9.5": [REF[0], REF[1]], "check replica": [shp(ref), per(ref)], "trials": {}}
for k, s in T.items():
    b = book(s); r = [shp(b), per(b)]
    out["trials"][k] = {"book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen417.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
