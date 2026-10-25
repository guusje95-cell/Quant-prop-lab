"""Gen408 (config/gen408_protocol.json). Writes results/gen408.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
dd, shp, per, unit, END, CS, V, B, pnl, days, C6, z, daily, rc6, a, bsm = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "B", "pnl", "days", "C6", "z", "daily", "rc6", "a", "bsm"))
rc95 = (rc6 + a + bsm) / 3; V5 = V.assign(**{"relative crowding 6": rc95}); v95 = unit(CS.portfolio_v5(V5)[0]); REF = (shp(v95), per(v95))
def chg(col):
    Z = pd.DataFrame({c: z(daily(B.metrics(c)[col], "mean").diff(7), 90) for c in C6}); Zd = Z.sub(Z.mean(axis=1), axis=0)
    return (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0).fillna(0.0)
c1 = ((pnl(chg("count_toptrader_long_short_ratio")) + pnl(chg("count_long_short_ratio"))) / 2).reindex(V.index).fillna(0.0)
T = {"C1 crowding change as an added sleeve": V5.assign(**{"crowding change": c1}), "C2 level + change": V.assign(**{"relative crowding 6": (rc95 + c1) / 2})}
out = {"reference v9.5": [REF[0], REF[1]], "C1 sleeve": per(c1), "corr C1 vs v9.5 sleeve": round(float(pd.concat([dd(c1), dd(rc95)], axis=1).loc["2022":END].corr().iloc[0, 1]), 3), "trials": {}}
for nm, H in T.items():
    b = unit(CS.portfolio_v5(H)[0]); r = [shp(b), per(b)]
    out["trials"][nm] = {"book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen408.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
