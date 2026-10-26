"""Gen419 (config/gen419_protocol.json): relative funding / leverage build-up / premium among the 6 majors. Writes results/gen419.json."""
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
def dly(s):                                                    # value of day d at row d + 1 (same convention as the crowding sleeve's daily())
    s = s.copy(); s.index = pd.DatetimeIndex(s.index).floor("D"); return s.groupby(level=0).mean().reindex(days).ffill().shift(1)
def rel(raw):
    Z = raw.apply(lambda s: z(s, 90)); Zd = Z.sub(Z.mean(axis=1), axis=0)
    return (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
def fund(c):
    f = B.funding(c); f = f.groupby(f.index.floor("D")).mean(); return dly(f).rolling(7, min_periods=5).mean()
def lev(c):
    oi = B.metrics(c)["sum_open_interest_value"].where(lambda s: s > 0); return np.log(dly(oi)).diff(7)
def prem(c):
    return dly(B.premium(c)["close"])
S = {k: pnl(rel(pd.DataFrame({c: fn(c) for c in C6}))).reindex(V.index).fillna(0.0)
     for k, fn in (("A relative funding", fund), ("B relative leverage build-up", lev), ("C relative premium", prem))}
out = {"reference v9.5": [REF[0], REF[1]], "trials": {}}
for k, s in S.items():
    b = unit(CS.portfolio_v5(V5.assign(**{k: s}))[0]); r = [shp(b), per(b)]
    out["trials"][k] = {"sleeve": per(s), "corr rc6": round(float(s.corr(V5["relative crowding 6"])), 2), "book": r,
                        "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3)))}
(ROOT / "results/gen419.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
