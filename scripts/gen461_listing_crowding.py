"""Gen461 (config/gen461_protocol.json): listing short sized by retail crowding at entry. Writes results/gen461.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"; ARCH = ROOT / "data/lab/binance_vision"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
ls, _, EV = LL.pnl(idx); V7 = V.drop(columns="cascade limit strict").assign(**{"listing short": ls})
ref = unit(CS.portfolio_v5(V7)[0]); REF = (shp(ref), per(ref))
LL.CAP = 1e9; P = LL.positions(idx, EV); size, Ls = {}, []
for s, t0, c, f in EV:
    e = (t0 + pd.Timedelta(hours=24)).ceil("D"); m = ARCH / f"{s}_metrics.parquet"; k = 1.0
    if m.exists():
        x = pd.read_parquet(m, columns=["time", "count_long_short_ratio"]); x["time"] = pd.to_datetime(x["time"])
        v = x[(x["time"] >= e - pd.Timedelta(hours=24)) & (x["time"] < e)]["count_long_short_ratio"].astype(float).dropna()
        if len(v) > 50:
            L = float(v.mean()); Ls.append(L); k = float(np.clip(L / 1.5, 0.5, 2.0))
    size[s[:-4]] = k
for n in P.columns:
    P[n] = P[n] * size.get(n, 1.0)
g = P.abs().sum(axis=1); P = P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
CF = {s[:-4]: (c, f) for s, t0, c, f in EV}; s_ = pd.Series(0.0, index=idx)
for n in P.columns:
    c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
    fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
    s_ = s_ + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
b = unit(CS.portfolio_v5(V7.assign(**{"listing short": s_}))[0]); r = [shp(b), per(b)]
out = {"reference v9.7": [REF[0], REF[1]], "events with metrics": len(Ls), "account ratio at entry (median / p10 / p90)": [round(float(np.median(Ls)), 2), round(float(np.percentile(Ls, 10)), 2), round(float(np.percentile(Ls, 90)), 2)] if Ls else None,
       "sleeve": per(s_), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen461.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
