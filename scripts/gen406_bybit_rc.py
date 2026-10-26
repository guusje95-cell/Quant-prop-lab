"""Gen406 (config/gen406_protocol.json, registered before the data). Writes results/gen406.json.
Y4 (Hyperliquid) not run: the download paged only BTC fully (descriptive trial anyway)."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, pnl, days, z, daily = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "pnl", "days", "z", "daily"))
ND = ROOT / "research_data/newdata"
rc95 = pd.read_parquet(ROOT / "results/gen404_sleeve_hourly.parquet").iloc[:, 0].reindex(V.index).fillna(0.0)
V5 = V.assign(**{"relative crowding 6": rc95}); v95 = unit(CS.portfolio_v5(V5)[0]); REF = (shp(v95), per(v95))
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE")
C15 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA", "AVAX", "LINK", "LTC", "TRX", "DOT", "BCH", "NEAR", "SUI")
def br(c):
    x = pd.read_parquet(ND / f"bybit_{c}_account_ratio_1d.parquet")["buyRatio"]; x.index = pd.DatetimeIndex(x.index); return x
def rel_bybit(coins, min_hist=0):
    Zs = pd.DataFrame({c: z(daily(br(c)), 90) for c in coins})
    if min_hist:
        first = {c: br(c).index.min() for c in coins}
        for c in coins:
            Zs.loc[Zs.index < first[c] + pd.Timedelta(days=min_hist), c] = np.nan
    Zd = Zs.sub(Zs.mean(axis=1), axis=0)
    ok = Zs.notna().all(axis=1) if not min_hist else Zs.notna().sum(axis=1) >= 4
    return (-0.15 * Zd.clip(-2, 2) / 2).where(ok, 0.0).fillna(0.0)
y1 = pnl(rel_bybit(C6)).reindex(V.index).fillna(0.0)
from qpl.lab import binance_pack as B, extra_pack as X
idx = V.index
def pnl_any(W):
    W = W.reindex(days).fillna(0.0).shift(1); out = 0.0
    for c in W:
        if c in B.coins():
            r = B.k5(c).close.resample("1h").last().pct_change(); f = B.funding(c).copy()
        else:
            r = X.close_1h(c).pct_change(); f = X.funding(c).copy()
        r = r.reindex(idx).fillna(0.0); f.index = f.index - pd.Timedelta(hours=1); f = f.groupby(level=0).sum().reindex(idx).fillna(0.0)
        p = W[c].reindex(idx.floor("D")).set_axis(idx).fillna(0.0); out = out + p * r - p * f - p.diff().abs().fillna(0.0) * 5 / 1e4
    return out
y3 = pnl_any(rel_bybit(C15, min_hist=365)).reindex(V.index).fillna(0.0)
T = {"Y1 Bybit relative crowding (added)": V5.assign(**{"bybit relative crowding": y1}),
     "Y2 two-venue relative crowding (replaces)": V.assign(**{"relative crowding 6": (rc95 + y1) / 2}),
     "Y3 Bybit relative crowding 15 coins (added)": V5.assign(**{"bybit relative crowding 15": y3})}
out = {"reference v9.5": [REF[0], REF[1]], "Y1 sleeve": per(y1), "Y3 sleeve": per(y3),
       "corr Y1 vs Binance sleeve": round(float(pd.concat([dd(y1), dd(rc95)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3), "trials": {}}
for k, H in T.items():
    b = unit(CS.portfolio_v5(H)[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
y1.to_frame("y1").assign(y3=y3).to_parquet(ROOT / "results/gen406_sleeves_hourly.parquet")
(ROOT / "results/gen406.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
