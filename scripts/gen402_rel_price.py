"""Gen402 (config/gen402_protocol.json). Writes results/gen402.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, sleeve, B, pnl, days = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "sleeve", "B", "pnl", "days"))
from qpl.lab import strategies as ST
from qpl.lab.data import Bars
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"); rc6 = sleeve(C6)
V4 = V.assign(**{"relative crowding 6": rc6}); v94 = unit(CS.portfolio_v5(V4)[0]); REF = (shp(v94), per(v94))
P = pd.DataFrame({c: B.k5(c).close.resample("1D").last() for c in C6}).reindex(days)
vol = P.pct_change().rolling(30, min_periods=20).std()
cs = ST.CStarTrend(); cst = cs.signal(Bars("6", "1d", P, P, P, P, P * 0), {**cs.defaults(), "long_only": False, "btc_leads": False, "stablecoin_filter": False})
S = {"A relative C*": cst, "B relative momentum 28d": (P / P.shift(28) - 1) / (vol * np.sqrt(28)), "C relative reversal 7d": -(P / P.shift(7) - 1) / (vol * np.sqrt(7))}
out = {"reference v9.4": [REF[0], REF[1]], "trials": {}}
for nm, sc in S.items():
    sc = sc.reindex(days); zx = sc.sub(sc.mean(axis=1), axis=0).div(sc.std(axis=1), axis=0)
    w = (0.15 * zx.clip(-2, 2) / 2).where(sc.notna().all(axis=1), 0.0).fillna(0.0)
    s = pnl(w).reindex(V.index).fillna(0.0)
    b = unit(CS.portfolio_v5(V4.assign(**{nm: s}))[0]); r = [shp(b), per(b)]
    out["trials"][nm] = {"sleeve": per(s), "corr v9.4": round(float(pd.concat([dd(s), dd(v94)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3), "book": r,
                         "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(nm, out["trials"][nm], flush=True)
(ROOT / "results/gen402.json").write_text(json.dumps(out, indent=1))
