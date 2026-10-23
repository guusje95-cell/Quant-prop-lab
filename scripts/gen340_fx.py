"""Gen340 (config/gen340_protocol.json): FX month-end fix rebalancing and local-hours depreciation on Dukascopy hourly data.
Writes results/gen340.json and results/gen340_series.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
import futures_db as F
DK = ROOT / "research_data/dukascopy"; COST = 1.0 / 1e4
px = lambda s: pd.read_parquet(DK / f"{s}_1h.parquet")["close"].pipe(lambda x: x[~x.index.duplicated()].sort_index())
FX = {"EUR": px("EURUSD"), "GBP": px("GBPUSD"), "JPY": 1 / px("USDJPY")}             # all as USD price of the foreign currency
IDX = {"EUR": px("EU50"), "GBP": px("UK100"), "JPY": px("JP225")}
H = pd.DataFrame(FX).loc["2013-01-02":"2026-09-30 23:00"]; R = H.pct_change(fill_method=None).fillna(0.0)


def pnl(pos):                                                            # pos: hourly position in the foreign currency (USD notional)
    pos = pos.reindex(R.index).fillna(0.0)
    return (pos * R).sum(axis=1) - pos.diff().abs().fillna(pos.abs()).sum(axis=1) * COST


def stats(h):
    d = h.groupby(h.index.floor("D")).sum(); d = d[d.index.weekday < 5]
    f = lambda a, z: round(float(d.loc[a:z].mean() / d.loc[a:z].std() * np.sqrt(252)), 3)
    return [f("2013", "2019"), f("2020", "2022"), f("2023", "2026-09-30")]


# ---- A: month-end fix ----------------------------------------------------------------------------------------------------
es = F.daily("ES")["r"] if "r" in F.daily("ES") else F.daily("ES").iloc[:, 0]
es.index = pd.DatetimeIndex(es.index)
days = pd.DatetimeIndex(sorted(set(H.index.normalize()[H.index.weekday < 5])))
last = pd.Series(days, index=days).groupby(days.to_period("M")).max()
posA = pd.DataFrame(0.0, index=H.index, columns=H.columns)
for m, ld in last.items():
    prior = days[(days.to_period("M") == m) & (days < ld)]
    if len(prior) < 3:
        continue
    cut = prior[-2]                                                      # information through the close two trading days before month end
    start = pd.Timestamp(m.start_time)
    us = float((1 + es.loc[start:cut]).prod() - 1)
    fix = (pd.Timestamp(ld) + pd.Timedelta(hours=16)).tz_localize("Europe/London").tz_convert("UTC").tz_localize(None)
    hrs = H.index[(H.index >= ld) & (H.index < fix)]
    for c in H.columns:
        fi = IDX[c].loc[start:cut + pd.Timedelta(hours=23)]
        if len(fi) < 10:
            continue
        sig = us - float(fi.iloc[-1] / fi.iloc[0] - 1)
        posA.loc[hrs, c] = np.sign(sig) / 3                               # US outperformed -> sell USD = long the foreign currency
A = pnl(posA)
# ---- B: local-hours depreciation -------------------------------------------------------------------------------------------
hr = H.index.hour; wd = H.index.weekday < 5
posB = pd.DataFrame(0.0, index=H.index, columns=H.columns)
for c in ("EUR", "GBP"):
    posB.loc[wd & (hr >= 7) & (hr <= 11), c] = -1 / 3; posB.loc[wd & (hr >= 13) & (hr <= 19), c] = 1 / 3
posB.loc[wd & (hr >= 0) & (hr <= 5), "JPY"] = -1 / 3; posB.loc[wd & (hr >= 13) & (hr <= 19), "JPY"] = 1 / 3
Bp = pnl(posB)
v = pd.read_parquet(ROOT / "results/cache_v86_final.parquet")["portfolio"]; vd = v.groupby(v.index.floor("D")).sum()
out = {}
for nm, h in (("A month-end fix", A), ("B local-hours depreciation", Bp)):
    d = h.groupby(h.index.floor("D")).sum(); c = float(pd.concat([d, vd], axis=1, sort=True).loc["2022":"2026-09-30"].dropna().corr().iloc[0, 1])
    s = stats(h)
    out[nm] = {"net Sharpe DEV / TEST / HOLD": s, "corr v8.6": round(c, 3), "pass": bool(s[0] > 0 and s[1] >= 0.5 and s[2] >= 0.3 and abs(c) <= 0.3)}
    print(nm, out[nm], flush=True)
# gross (no cost) for information
COST0 = COST; COST = 0.0
out["A gross"] = stats(pnl(posA)); out["B gross"] = stats(pnl(posB)); COST = COST0
print("gross", out["A gross"], out["B gross"])
pd.DataFrame({"A": A, "B": Bp}).to_parquet(ROOT / "results/gen340_series.parquet")
json.dump(out, open(ROOT / "results/gen340.json", "w"), indent=1)
