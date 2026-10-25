"""Gen401 (config/gen401_protocol.json). Writes results/gen401.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen396_relcrowd.py").read().split("\nC3 = (")[0]
g = {"__file__": str(ROOT / "scripts/gen396_relcrowd.py")}; exec(compile(src, "g396", "exec"), g)
dd, shp, per, unit, END, CS, V, sleeve, B, pnl, days, rel, idx, R, FU, prep = (g[k] for k in ("dd", "shp", "per", "unit", "END", "CS", "V", "sleeve", "B", "pnl", "days", "rel", "idx", "R", "FU", "prep"))
C6 = ("BTC", "ETH", "SOL", "XRP", "BNB", "DOGE"); rc6 = sleeve(C6)
v94 = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": rc6}))[0]); REF = (shp(v94), per(v94))
# A: 8-hourly
def rel8(col):
    Z = {}
    for c in C6:
        m = B.metrics(c)[col]; m.index = pd.DatetimeIndex(m.index)
        x = m.resample("8h").mean(); Z[c] = (x - x.rolling(270, min_periods=190).mean()) / x.rolling(270, min_periods=190).std()
    Z = pd.DataFrame(Z); Zd = Z.sub(Z.mean(axis=1), axis=0); return (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
def pnl8(W):
    out = 0.0
    for c in W:
        prep(c); p = W[c].copy(); p.index = p.index + pd.Timedelta(hours=8)                 # bar [t, t+8h) decided at its close, held from t+8h
        p = p.reindex(idx, method="ffill").fillna(0.0); r = R[c].reindex(idx).fillna(0.0); f = FU[c].reindex(idx).fillna(0.0)
        out = out + p * r - p * f - p.diff().abs().fillna(0.0) * 5 / 1e4
    return out
a = ((pnl8(rel8("count_toptrader_long_short_ratio")) + pnl8(rel8("count_long_short_ratio"))) / 2).reindex(V.index).fillna(0.0)
bsm = ((pnl(rel(C6, "count_toptrader_long_short_ratio").rolling(3, min_periods=1).mean()) + pnl(rel(C6, "count_long_short_ratio").rolling(3, min_periods=1).mean())) / 2).reindex(V.index).fillna(0.0)
out = {"reference v9.4": [REF[0], REF[1]], "trials": {}}
for nm, s in (("A 8-hourly", a), ("B 3-day smoothing", bsm)):
    b = unit(CS.portfolio_v5(V.assign(**{"relative crowding 6": s}))[0]); r = [shp(b), per(b)]
    out["trials"][nm] = {"sleeve": per(s), "book": r, "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
    print(nm, out["trials"][nm], flush=True)
(ROOT / "results/gen401.json").write_text(json.dumps(out, indent=1))
