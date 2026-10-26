"""Gen420 (config/gen420_protocol.json, FLAGGED): relative OI momentum among the 6 majors. Writes results/gen420.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
shp, per, unit, CS, V, B, C6, rc6, a, bsm, pnl, days = (g[k] for k in ("shp", "per", "unit", "CS", "V", "B", "C6", "rc6", "a", "bsm", "pnl", "days"))
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
V5 = V.assign(**{"relative crowding 6": (rc6 + a + bsm) / 3}); v95 = unit(CS.portfolio_v5(V5)[0]); REF = (shp(v95), per(v95))
def dly(s):
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); return s.groupby(level=0).mean().reindex(days).ffill().shift(1)
OI = pd.DataFrame({c: np.log(dly(B.metrics(c)["sum_open_interest_value"].where(lambda s: s > 0))) for c in C6})
def W(k=7, win=90):
    Z = OI.diff(k).apply(lambda s: z(s, win)); Zd = Z.sub(Z.mean(axis=1), axis=0); return (0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
sl = lambda w, cm=1.0, lag=0: pnl(w, cm, lag).reindex(V.index).fillna(0.0)
s = sl(W()); b = unit(CS.portfolio_v5(V5.assign(**{"relative OI momentum": s}))[0]); r = [shp(b), per(b)]
dd = lambda h: h.groupby(h.index.floor("D")).sum()
out = {"reference v9.5": [REF[0], REF[1]], "sleeve": per(s), "corr rc6": round(float(s.corr(V5["relative crowding 6"])), 2), "book": r,
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3))),
       "by year": {str(y): shp(s, str(y), str(y)) for y in range(2022, 2027)},
       "robustness": {"costs x2": per(sl(W(), 2.0)), "one day later": per(sl(W(), 1.0, 1)), "z 60": per(sl(W(win=60))), "z 180": per(sl(W(win=180))),
                      "change 3d": per(sl(W(k=3))), "change 14d": per(sl(W(k=14)))}}
(ROOT / "results/gen420.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
