"""Gen403 (config/gen403_protocol.json, flagged). Writes results/gen403.json and results/gen403_sleeve_hourly.parquet."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, sleeve, B, pnl, days = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "sleeve", "B", "pnl", "days"))
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"); rc6 = sleeve(C6)
V4 = V.assign(**{"relative crowding 6": rc6}); v94 = unit(CS.portfolio_v5(V4)[0]); REF = (shp(v94), per(v94))
pk = B.coins(); PA = pd.DataFrame({c: B.k5(c).close.resample("1D").last() for c in pk}).reindex(days)
def relmom(P, k, cm=1.0):
    vol = P.pct_change().rolling(30, min_periods=20).std(); sc = (P / P.shift(k) - 1) / (vol * np.sqrt(k))
    zx = sc.sub(sc.mean(axis=1), axis=0).div(sc.std(axis=1), axis=0)
    w = (0.15 * zx.clip(-2, 2) / 2).where(sc.notna().sum(axis=1) >= 4, 0.0).fillna(0.0)
    return pnl(w, cm=cm).reindex(V.index).fillna(0.0)
P6 = PA[list(C6)]
single = {k: relmom(P6, k) for k in (3, 5, 7, 10, 14)}
ens = (single[5] + single[7] + single[10]) / 3
qv = pd.DataFrame({c: B.k5(c).quote_volume.resample("1D").sum() for c in pk}).reindex(days)
mem = (qv.rolling(30, min_periods=20).sum().shift(1).rank(axis=1, ascending=False) <= 6); mem = mem[~mem.index.to_period("M").duplicated()].reindex(days).ffill().fillna(False)
pit = sum(relmom(PA.where(mem), k) for k in (5, 7, 10)) / 3
cost2 = sum(relmom(P6, k, cm=2.0) for k in (5, 7, 10)) / 3
b = unit(CS.portfolio_v5(V4.assign(**{"relative momentum": ens}))[0]); r = [shp(b), per(b)]
rob = {**{f"k = {k}": per(s) for k, s in single.items()}, "costs x2": per(cost2), "point-in-time top-6": per(pit)}
robust = bool(all(sum(v > 0 for v in x) >= 2 for x in rob.values()))
d = dd(b).loc["2022":END]
out = {"reference v9.4": [REF[0], REF[1]], "ensemble sleeve": per(ens), "corr v9.4": round(float(pd.concat([dd(ens), dd(v94)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3),
       "book": r, "by year": {str(y): round(float(x.mean() / x.std() * np.sqrt(365)), 2) for y, x in d.groupby(d.index.year)}, "robustness": rob, "robust": robust,
       "pass": bool(robust and r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
ens.to_frame("relative momentum").to_parquet(ROOT / "results/gen403_sleeve_hourly.parquet"); b.to_frame("book").to_parquet(ROOT / "results/gen403_book_hourly.parquet")
(ROOT / "results/gen403.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
