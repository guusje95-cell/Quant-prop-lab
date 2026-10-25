"""Gen396 (config/gen396_protocol.json, flagged). Writes results/gen396.json and results/gen396_sleeve_hourly.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen390_breadth_regime.py").read().split("\nref_book = pd.read_parquet(ROOT")[0]
g = {"__file__": str(ROOT / "scripts/gen390_breadth_regime.py")}; exec(compile(src, "g390", "exec"), g)
dd, shp, per, unit, END, CS, daily, z, days, idx, K1 = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "daily", "z", "days", "idx", "K1"))
B = g["B"]
V = pd.read_parquet(ROOT / "results/v93_sleeves.parquet"); v93 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v93), per(v93))
R, FU = {}, {}
def prep(c):
    if c not in R:
        R[c] = B.k5(c).close.resample("1h").last().pct_change().fillna(0.0)
        f = B.funding(c).copy(); f.index = f.index - pd.Timedelta(hours=1); FU[c] = f.groupby(level=0).sum()
def pnl(W, cm=1.0, lag=0):
    W = W.reindex(days).fillna(0.0).shift(1 + lag); out = 0.0
    for c in W:
        prep(c); p = W[c].reindex(idx.floor("D")).set_axis(idx).fillna(0.0); r = R[c].reindex(idx).fillna(0.0); f = FU[c].reindex(idx).fillna(0.0)
        out = out + p * r - p * f - p.diff().abs().fillna(0.0) * 5 * cm / 1e4
    return out
def rel(coins, col, win=90):
    Z = pd.DataFrame({c: z(daily(B.metrics(c)[col], "mean"), win) for c in coins}); Zd = Z.sub(Z.mean(axis=1), axis=0)
    return (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
def sleeve(coins, cm=1.0, lag=0, win=90):
    return ((pnl(rel(coins, "count_toptrader_long_short_ratio", win), cm, lag) + pnl(rel(coins, "count_long_short_ratio", win), cm, lag)) / 2).reindex(V.index).fillna(0.0)
C3 = ("BTC", "ETH", "SOL"); rc = sleeve(C3)
b = unit(CS.portfolio_v5(V.assign(**{"relative crowding": rc}))[0]); r = [shp(b), per(b)]
d = dd(rc).loc["2022":END]
out = {"reference v9.3": [REF[0], REF[1]], "sleeve 2022 / 2023-24 / 2025-26": per(rc), "sleeve by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)},
       "corr with v9.3": round(float(pd.concat([dd(rc), dd(v93)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3), "v9.3 + relative crowding": r,
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
rob = {"BTC/ETH only": per(sleeve(("BTC", "ETH"))), "6 coins": per(sleeve(("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"))), "cost x2": per(sleeve(C3, cm=2.0)),
       "one day later": per(sleeve(C3, lag=1)), "z 60": per(sleeve(C3, win=60)), "z 180": per(sleeve(C3, win=180))}
out["robustness"] = rob; out["robust (each >= 2 of 3 periods positive)"] = bool(all(sum(v > 0 for v in x) >= 2 for x in rob.values()))
rc.to_frame("relative crowding").to_parquet(ROOT / "results/gen396_sleeve_hourly.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen396_book_hourly.parquet")
(ROOT / "results/gen396.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
