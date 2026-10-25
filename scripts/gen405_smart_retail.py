"""Gen405 (config/gen405_protocol.json). Writes results/gen405.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, sleeve, B, pnl, days, z, daily = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "sleeve", "B", "pnl", "days", "z", "daily"))
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"); V4 = V.assign(**{"relative crowding 6": sleeve(C6)}); v94 = unit(CS.portfolio_v5(V4)[0]); REF = (shp(v94), per(v94))
dv = lambda c: z(daily(B.metrics(c)["sum_toptrader_long_short_ratio"], "mean"), 90) - z(daily(B.metrics(c)["count_long_short_ratio"], "mean"), 90)
D = pd.DataFrame({c: dv(c) for c in C6})
W = {"D1 directional BTC/ETH": (0.125 * D[["BTC", "ETH"]].clip(-2, 2) / 2).fillna(0.0)}
Dd = D.sub(D.mean(axis=1), axis=0); W["D2 relative 6 coins"] = (0.15 * Dd.clip(-2, 2) / 2).where(D.notna().all(axis=1), 0.0).fillna(0.0)
out = {"reference v9.4": [REF[0], REF[1]], "trials": {}}
for nm, w in W.items():
    s = pnl(w).reindex(V.index).fillna(0.0); b = unit(CS.portfolio_v5(V4.assign(**{nm: s}))[0]); r = [shp(b), per(b)]
    out["trials"][nm] = {"sleeve": per(s), "corr v9.4": round(float(pd.concat([dd(s), dd(v94)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3), "book": r,
                         "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(nm, out["trials"][nm], flush=True)
(ROOT / "results/gen405.json").write_text(json.dumps(out, indent=1))
