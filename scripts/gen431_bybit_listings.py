"""Gen431 (config/gen431_protocol.json): Bybit-only / Bybit-first listings added to the v9.6 listing short. Writes results/gen431.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import crypto_sleeves as CS
import listing_live as LL
END = "2026-09-30"
D = ROOT / "research_data/bybit_listings"
V = pd.read_parquet(ROOT / "results/v95_sleeves.parquet"); idx = V.index
dd = lambda h: h.groupby(h.index.floor("D")).sum()
unit = lambda h: h * 0.15 / (dd(h.loc["2022":"2024"]).std() * np.sqrt(365))
def shp(h, a="2022", z=END):
    d = dd(h.loc[a:z]); return round(float(d.mean() / d.std() * np.sqrt(365)), 3)
per = lambda h: [shp(h, "2022", "2022"), shp(h, "2023", "2024"), shp(h, "2025", END)]
TF = set(json.loads((ROOT / "config/tradfi_perps.json").read_text())["symbols"])
EVB = LL.events(); binance_t0 = {s[:-4]: t0 for s, t0, c, f in EVB}
ins = json.loads((D / "instruments.json").read_text()); EVY = []; r30 = []
for x in ins:
    sym = x["symbol"]; base = sym[:-4]; t0 = pd.to_datetime(x["launchTime"], unit="ms")
    if t0 < LL.FIRST or base in TF or not (D / f"{sym}_1h.parquet").exists():
        continue
    k = pd.read_parquet(D / f"{sym}_1h.parquet"); k.index = pd.DatetimeIndex(k.index)
    if len(k) < 30 or k.loc[:k.index.min() + pd.Timedelta(hours=23), "quote_volume"].sum() < 1e7:
        continue
    start = (k.index.min() + pd.Timedelta(hours=24)).ceil("D"); cc = k["close"].loc[start:start + pd.Timedelta(days=30)]
    if len(cc) > 24 * 25:
        r30.append((start.year, float(cc.iloc[-1] / cc.iloc[0] - 1)))
    if base in binance_t0 and abs((binance_t0[base] - k.index.min()).days) <= 7:
        continue                                                   # already a Binance listing event
    fp = D / f"{sym}_funding.parquet"
    f = pd.read_parquet(fp) if fp.exists() else pd.DataFrame({"time": [], "last_funding_rate": []})
    fs = pd.Series(f["last_funding_rate"].astype(float).to_numpy(), index=pd.to_datetime(f["time"]).dt.floor("h")).groupby(level=0).last()
    EVY.append(("BYBIT_" + sym, k.index.min(), k["close"], fs))
LL.CAP = 1e9
P = pd.concat([LL.positions(idx, EVB), LL.positions(idx, EVY)], axis=1)
P = P.T.groupby(level=0).min().T.reindex(idx).fillna(0.0)                 # one position per column name
g = P.abs().sum(axis=1); P = P.mul((0.5 / g).clip(upper=1.0).fillna(1.0), axis=0)
CF = {s[:-4]: (c, f) for s, t0, c, f in EVB + EVY}
s_ = pd.Series(0.0, index=idx)
for n in P.columns:
    c, f = CF[n]; p = P[n]; r = (c / c.shift(1) - 1).reindex(idx).fillna(0.0)
    fu = f.copy(); fu.index = fu.index - pd.Timedelta(hours=1); fu = fu.groupby(level=0).sum().reindex(idx).fillna(0.0)
    s_ = s_ + p * r - p * fu - p.diff().abs().fillna(p.abs()) * 10 / 1e4
ls, _, _ = LL.pnl(idx); v96 = unit(CS.portfolio_v5(V.assign(**{"listing short": ls}))[0]); REF = (shp(v96), per(v96))
b = unit(CS.portfolio_v5(V.assign(**{"listing short": s_}))[0]); r = [shp(b), per(b)]
R30 = pd.DataFrame(r30, columns=["year", "r30"])
out = {"reference v9.6 A..Z": [REF[0], REF[1]], "Bybit instruments": len(ins), "Bybit-only / Bybit-first events added": len(EVY),
       "Bybit listings median 30-day return by year": {str(y): [round(float(x.median()), 3), int(len(x))] for y, x in R30.groupby("year")["r30"]},
       "sleeve": per(s_), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen431.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
