"""Gen424 (config/gen424_protocol.json, FLAGGED): fade relative depth imbalance among the 6 majors. Writes results/gen424.json."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts")); sys.path.insert(0, str(ROOT / "src"))
src = open(ROOT / "scripts/gen401_rc_freq.py").read().split("\nout = {")[0]
g = {"__file__": str(ROOT / "scripts/gen401_rc_freq.py")}; exec(compile(src, "g401", "exec"), g)
shp, per, unit, CS, V0, C6, rc6, a, bsm, pnl, days = (g[k] for k in ("shp", "per", "unit", "CS", "V", "C6", "rc6", "a", "bsm", "pnl", "days"))
import basket_live as BL
V = V0.assign(**{"relative crowding 6": (rc6 + a + bsm) / 3}); v95 = unit(CS.portfolio_v5(V)[0]); REF = (shp(v95), per(v95))
z = lambda x, w: (x - x.rolling(w, min_periods=int(w * 0.7)).mean()) / x.rolling(w, min_periods=int(w * 0.7)).std()
D = {c: pd.read_parquet(ROOT / f"research_data/binance_depth/{c}USDT_depth_1h.parquet") for c in C6}
def W(col="I2", win=90, coins=C6):
    Z = pd.DataFrame({c: z(BL.daily(D[c][col], "mean"), win) for c in coins}).reindex(days); Zd = Z.sub(Z.mean(axis=1), axis=0)
    return (-0.15 * Zd.clip(-2, 2) / 2).where(Z.notna().all(axis=1), 0.0)
sl = lambda w, cm=1.0, lag=0: pnl(w, cm, lag).reindex(V.index).fillna(0.0)
s = sl(W()); b = unit(CS.portfolio_v5(V.assign(**{"fade relative depth 6": s}))[0]); r = [shp(b), per(b)]
out = {"reference v9.5": [REF[0], REF[1]], "sleeve": per(s), "corr rc6": round(float(s.corr(V["relative crowding 6"])), 2), "book": r,
       "pass": bool(r[0] >= REF[0] + 0.05 and all(r[1][i] >= REF[1][i] for i in range(3))),
       "by year": {str(y): shp(s, str(y), str(y)) for y in range(2023, 2027)},
       "robustness": {"costs x2": per(sl(W(), 2.0)), "one day later": per(sl(W(), 1.0, 1)), "I1": per(sl(W("I1"))), "I5": per(sl(W("I5"))),
                      "z 60": per(sl(W(win=60))), "z 180": per(sl(W(win=180))),
                      **{f"without {c}": per(sl(W(coins=tuple(x for x in C6 if x != c)))) for c in C6}}}
(ROOT / "results/gen424.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=0))
